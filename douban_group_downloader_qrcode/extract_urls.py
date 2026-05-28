import csv
import json
import time
from pathlib import Path
from urllib.parse import urljoin, urldefrag

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def init_driver():
    print("正在初始化浏览器...")
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
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
    return url


def extract_group_urls(driver, groupid, groupname):
    """Extract all visible topic URLs from a Douban group discussion list."""
    print("\n" + "=" * 60)
    print(f"开始提取 {groupname}_{groupid} 小组的帖子 URL")
    print("=" * 60)

    seen_urls = set()
    all_urls = []
    group_url = f"https://www.douban.com/group/{groupid}/discussion?start=0&type=new"
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

            soup = BeautifulSoup(driver.page_source, "html.parser")
            results = soup.find_all("td", class_="title")

            if not results:
                print("没有找到帖子列表，可能需要重新登录或检查小组权限。")
                break

            page_count = 0
            for result in results:
                link_node = result.find("a")
                if not link_node:
                    continue

                link = clean_topic_url(link_node.get("href", ""))
                title = link_node.get("title") or link_node.get_text(strip=True)

                if not link or not title or link in seen_urls:
                    continue

                seen_urls.add(link)
                all_urls.append({"url": link, "title": title.strip()})
                page_count += 1

            print(f"本页提取 {page_count} 个 URL，累计 {len(all_urls)} 个")

            next_page = soup.find("span", class_="next")
            next_link = next_page.find("a") if next_page else None
            next_url = next_link.get("href") if next_link else ""

            if not next_url:
                print("已经到最后一页")
                break

            driver.get(urljoin("https://www.douban.com", next_url))
            time.sleep(3)
            page_num += 1

        except Exception as exc:
            print(f"提取出错：{exc}")
            break

    print(f"\n共提取 {len(all_urls)} 个帖子 URL")
    return all_urls


def safe_name(value):
    unsafe_chars = '<>:"/\\|?*'
    result = "".join("_" if char in unsafe_chars else char for char in value).strip()
    return result or "douban_group"


def save_urls(urls, groupname, groupid):
    """Save URLs and generate a config file for douban_private_single.py."""
    base_name = f"{safe_name(groupname)}_{groupid}_urls"

    txt_file = Path(f"{base_name}.txt")
    with txt_file.open("w", encoding="utf-8") as file:
        for item in urls:
            file.write(item["url"] + "\n")
    print(f"已保存 URL 文本：{txt_file}")

    json_file = Path(f"{base_name}.json")
    with json_file.open("w", encoding="utf-8") as file:
        json.dump(urls, file, ensure_ascii=False, indent=2)
    print(f"已保存 URL 明细：{json_file}")

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

        for group in groups:
            groupid = str(group.get("groupid", "")).strip()
            groupname = str(group.get("groupname", "")).strip()

            if not groupid or not groupname:
                print("跳过一条不完整的小组配置。")
                continue

            urls = extract_group_urls(driver, groupid, groupname)

            if not urls:
                continue

            files = save_urls(urls, groupname, groupid)
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
        driver.quit()


if __name__ == "__main__":
    main()
