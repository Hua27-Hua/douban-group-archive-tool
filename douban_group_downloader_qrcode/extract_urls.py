import argparse
import csv
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urldefrag

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


LIST_TYPES = {
    "new": {
        "label": "最新讨论",
        "url_type": "new",
    },
    "elite": {
        "label": "精华帖",
        "url_type": "elite",
    },
    "hot": {
        "label": "热门讨论",
        "url_type": "hot",
    },
}

TOPIC_URL_RE = re.compile(r"https?://www\.douban\.com/group/topic/(\d+)/?")


def find_local_chromedriver():
    """优先使用用户放在本地的 ChromeDriver，避免网络不好时自动下载失败。"""
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    search_dirs = [
        Path.cwd(),
        script_dir,
        project_dir,
        Path.cwd() / "drivers",
        script_dir / "drivers",
        project_dir / "drivers",
    ]
    names = ["chromedriver.exe", "chromedriver"]

    for folder in search_dirs:
        for name in names:
            path = folder / name
            if path.is_file():
                return str(path)
    return ""


def build_chrome_service():
    local_driver = find_local_chromedriver()
    if local_driver:
        print(f"使用本地 ChromeDriver: {local_driver}")
        return Service(local_driver, log_output=os.devnull)

    print("未找到本地 chromedriver.exe，尝试自动下载匹配版本...")
    return Service(ChromeDriverManager().install(), log_output=os.devnull)


def init_driver():
    print("正在初始化浏览器...")
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(
        service=build_chrome_service(),
        options=options,
    )
    print("浏览器初始化完成")
    return driver


def login(driver):
    print("\n" + "=" * 60)
    print("请先在打开的浏览器里登录豆瓣")
    print("=" * 60)
    driver.get("https://www.douban.com")
    time.sleep(3)
    input("登录完成后按回车继续...")
    return True


def ensure_driver_alive(driver):
    try:
        _ = driver.current_url
        return True
    except (InvalidSessionIdException, WebDriverException):
        return False


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} 不是有效的 JSON：{exc}") from exc


def load_group_config():
    """Read group config from this folder or from the qrcode crawler folder."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "config.json",
        here.parent / "douban_group_downloader_qrcode" / "config.json",
    ]

    for path in candidates:
        config = read_json(path)
        if config and config.get("grouplist"):
            print(f"读取小组配置：{path}")
            return config["grouplist"]

    example = {
        "grouplist": [
            {
                "groupid": "123456",
                "groupname": "示例小组",
            }
        ]
    }
    raise FileNotFoundError(
        "没有找到可用的 grouplist 配置。请在 qrcode 目录的 config.json 里填写小组信息，例如：\n"
        + json.dumps(example, ensure_ascii=False, indent=2)
    )


def clean_topic_url(url):
    url, _fragment = urldefrag(url.strip())
    match = TOPIC_URL_RE.search(url)
    if match:
        return f"https://www.douban.com/group/topic/{match.group(1)}/"
    return url


def build_group_list_url(groupid, list_type):
    info = LIST_TYPES.get(list_type, LIST_TYPES["new"])
    return f"https://www.douban.com/group/{groupid}/discussion?start=0&type={info['url_type']}"


def find_tab_url(soup, tab_text):
    for link in soup.find_all("a", href=True):
        text = link.get_text(" ", strip=True)
        if tab_text in text:
            href = link.get("href", "").strip()
            if "/group/" in href and ("discussion" in href or "type=" in href):
                return urljoin("https://www.douban.com", href)
    return ""


def resolve_first_list_url(driver, groupid, list_type, custom_url=""):
    if custom_url:
        return custom_url

    if list_type != "elite":
        return build_group_list_url(groupid, list_type)

    # 豆瓣精华入口偶尔会变；先从页面上找“精华”标签链接，找不到再用常见参数兜底。
    discussion_url = f"https://www.douban.com/group/{groupid}/discussion?start=0&type=new"
    driver.get(discussion_url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    tab_url = find_tab_url(soup, "精华")
    return tab_url or build_group_list_url(groupid, list_type)


def extract_topic_links(soup):
    link_nodes = []
    selectors = [
        "#content table.olt td.title a[href*='/group/topic/']",
        "table.olt td.title a[href*='/group/topic/']",
        "#content .article td.title a[href*='/group/topic/']",
        "#content .article a[href*='/group/topic/']",
    ]
    for selector in selectors:
        link_nodes = soup.select(selector)
        if link_nodes:
            break

    if not link_nodes:
        # 兜底：页面结构变了才扫全页，避免平时把侧栏/推荐区的帖子链接混进列表。
        link_nodes = soup.find_all("a", href=True)

    topics = []
    seen_ids = set()

    for link_node in link_nodes:
        href = link_node.get("href", "")
        match = TOPIC_URL_RE.search(href)
        if not match:
            continue

        topic_id = match.group(1)
        if topic_id in seen_ids:
            continue

        title = (
            link_node.get("title")
            or link_node.get_text(" ", strip=True)
            or f"topic_{topic_id}"
        ).strip()
        if not title:
            continue

        seen_ids.add(topic_id)
        topics.append({
            "url": f"https://www.douban.com/group/topic/{topic_id}/",
            "title": title,
        })

    return topics


def find_next_url(soup):
    selectors = [
        "span.next a",
        ".paginator .next a",
        ".paginator a.next",
        "a[rel='next']",
    ]
    for selector in selectors:
        link = soup.select_one(selector)
        if link and link.get("href"):
            return urljoin("https://www.douban.com", link["href"])

    for link in soup.find_all("a", href=True):
        text = link.get_text(" ", strip=True)
        if text in ("后页>", "后页", "下一页", "下页"):
            return urljoin("https://www.douban.com", link["href"])

    return ""


def extract_group_urls(driver, groupid, groupname, list_type="new", custom_url="", max_pages=0):
    """Extract all visible topic URLs from a Douban group discussion list."""
    print("\n" + "=" * 60)
    list_label = LIST_TYPES.get(list_type, LIST_TYPES["new"])["label"]
    if custom_url:
        list_label = "自定义列表页"
    print(f"开始提取 {groupname}_{groupid} 小组的帖子 URL")
    print(f"提取范围：{list_label}")
    print("=" * 60)

    seen_urls = set()
    all_urls = []
    group_url = resolve_first_list_url(driver, groupid, list_type, custom_url=custom_url)
    driver.get(group_url)
    time.sleep(3)

    page_num = 1

    while True:
        print(f"\n正在提取第 {page_num} 页...")

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.olt, #content"))
            )
            time.sleep(2)

            current_url = driver.current_url
            soup = BeautifulSoup(driver.page_source, "html.parser")
            results = extract_topic_links(soup)

            if not results:
                print("没有找到帖子列表，可能需要重新登录或检查小组权限。")
                break

            page_count = 0
            duplicate_count = 0
            for result in results:
                link = clean_topic_url(result["url"])
                title = result["title"]

                if not link or not title:
                    continue

                if link in seen_urls:
                    duplicate_count += 1
                    continue

                seen_urls.add(link)
                all_urls.append({"url": link, "title": title.strip()})
                page_count += 1

            print(
                f"本页识别 {len(results)} 个列表 URL，"
                f"新增 {page_count} 个，重复 {duplicate_count} 个，累计 {len(all_urls)} 个"
            )

            if max_pages and page_num >= max_pages:
                print(f"已达到最大页数限制：{max_pages}")
                break

            next_url = find_next_url(soup)
            if not next_url:
                print("已经到最后一页")
                break

            if next_url == current_url:
                print("下一页地址没有变化，停止翻页，避免重复提取。")
                break

            driver.get(next_url)
            time.sleep(3)
            page_num += 1

        except Exception as exc:
            print(f"提取出错：{exc}")
            break

    print(f"\n共提取 {len(all_urls)} 个帖子 URL")
    return all_urls


def choose_list_type(args):
    if args.custom_url:
        return "new", args.custom_url

    if args.list_type:
        return args.list_type, ""

    print("\n请选择要提取的帖子范围：")
    print("1. 最新讨论 / 全部列表")
    print("2. 精华帖")
    print("3. 热门讨论")
    print("4. 自定义列表页 URL")
    choice = input("请输入 1-4，直接回车默认 1：").strip()

    if choice == "2":
        return "elite", ""
    if choice == "3":
        return "hot", ""
    if choice == "4":
        custom_url = input("请粘贴豆瓣小组列表页 URL：").strip()
        return "new", custom_url
    return "new", ""


def safe_name(value):
    unsafe_chars = '<>:"/\\|?*'
    result = "".join("_" if char in unsafe_chars else char for char in value).strip()
    return result or "douban_group"


def save_urls(urls, groupname, groupid, list_type="new", custom_url="", save_extra_formats=False):
    """Save URLs and generate a config file for douban_private_single.py."""
    suffix = "custom" if custom_url else list_type
    if suffix == "new":
        base_name = f"{safe_name(groupname)}_{groupid}_urls"
    else:
        base_name = f"{safe_name(groupname)}_{groupid}_{suffix}_urls"

    json_file = Path(f"{base_name}.json")
    with json_file.open("w", encoding="utf-8") as file:
        json.dump(urls, file, ensure_ascii=False, indent=2)
    print(f"已保存 URL 明细：{json_file}")

    txt_file = None
    csv_file = None
    if save_extra_formats:
        txt_file = Path(f"{base_name}.txt")
        with txt_file.open("w", encoding="utf-8") as file:
            for item in urls:
                file.write(item["url"] + "\n")
        print(f"已保存 URL 文本：{txt_file}")

        csv_file = Path(f"{base_name}.csv")
        with csv_file.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["title", "url"])
            writer.writeheader()
            writer.writerows(urls)
        print(f"已保存表格文件：{csv_file}")

    single_config_file = Path(f"{base_name}_single_posts_config.json")
    with single_config_file.open("w", encoding="utf-8") as file:
        json.dump({"single_posts": urls}, file, ensure_ascii=False, indent=2)
    print(f"已生成指定帖子下载配置：{single_config_file}")

    return {
        "txt": txt_file,
        "json": json_file,
        "csv": csv_file,
        "single_config": single_config_file,
    }


def main():
    parser = argparse.ArgumentParser(description="豆瓣小组 URL 提取器")
    parser.add_argument(
        "--list-type",
        choices=sorted(LIST_TYPES.keys()),
        default="",
        help="提取范围：new=最新讨论，elite=精华帖，hot=热门讨论。不填则启动时手动选择。",
    )
    parser.add_argument(
        "--custom-url",
        default="",
        help="直接指定一个豆瓣小组列表页 URL，例如精华页、搜索结果页或某个分类页。",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="最多提取多少页，0 表示一直翻到最后。",
    )
    parser.add_argument(
        "--save-extra-formats",
        action="store_true",
        help="额外生成 .csv 和 .txt。默认只生成 JSON。",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("豆瓣小组 URL 提取器 - 生成指定帖子下载配置")
    print("=" * 60)

    try:
        groups = load_group_config()
    except Exception as exc:
        print(exc)
        return

    driver = init_driver()

    try:
        login(driver)
        if not ensure_driver_alive(driver):
            print("\n浏览器已经关闭或断开连接。")
            print("请重新运行脚本；登录后不要关闭脚本打开的 Chrome 窗口，直接回到终端按回车即可。")
            return

        list_type, custom_url = choose_list_type(args)
        if not ensure_driver_alive(driver):
            print("\n浏览器已经关闭或断开连接。")
            print("请重新运行脚本；选择提取范围时也要保持 Chrome 窗口打开。")
            return

        for group in groups:
            groupid = str(group.get("groupid", "")).strip()
            groupname = str(group.get("groupname", "")).strip()

            if not groupid or not groupname:
                print("跳过一条不完整的小组配置。")
                continue

            urls = extract_group_urls(
                driver,
                groupid,
                groupname,
                list_type=list_type,
                custom_url=custom_url,
                max_pages=args.max_pages,
            )

            if not urls:
                continue

            files = save_urls(
                urls,
                groupname,
                groupid,
                list_type=list_type,
                custom_url=custom_url,
                save_extra_formats=args.save_extra_formats,
            )
            print("\n" + "=" * 60)
            print("提取完成")
            print(f"共 {len(urls)} 个帖子")
            print(f"指定帖子下载配置：{files['single_config']}")
            print("如果只想下载这些指定帖子，可以把上面的文件内容复制到 captcha 目录的 config.json。")
            print("=" * 60)

    except Exception as exc:
        print(f"\n程序出错：{exc}")

    finally:
        try:
            input("\n按回车关闭浏览器...")
        except EOFError:
            pass
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
