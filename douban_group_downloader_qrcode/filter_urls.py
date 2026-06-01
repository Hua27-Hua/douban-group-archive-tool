import argparse
import csv
import json
import re
import sys
from pathlib import Path


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


def split_keywords(value):
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,，\s]+", value) if item.strip()]


def safe_name(value):
    unsafe_chars = '<>:"/\\|?*'
    result = "".join("_" if char in unsafe_chars else char for char in value).strip()
    return result or "selected_urls"


def read_json(path):
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict) and "single_posts" in data:
        data = data["single_posts"]

    items = []
    for item in data:
        url = str(item.get("url") or item.get("link") or "").strip()
        title = str(item.get("title") or url).strip()
        if url:
            items.append({"url": url, "title": title})
    return items


def read_csv(path):
    items = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            url = str(row.get("url") or row.get("link") or "").strip()
            title = str(row.get("title") or url).strip()
            if url:
                items.append({"url": url, "title": title})
    return items


def read_txt(path):
    items = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            url = line.strip()
            if url:
                items.append({"url": url, "title": url})
    return items


def read_items(path):
    suffix = path.suffix.lower()
    if suffix == ".json":
        return read_json(path)
    if suffix == ".csv":
        return read_csv(path)
    if suffix == ".txt":
        return read_txt(path)
    raise ValueError("只支持 .json、.csv、.txt URL 清单")


def item_text(item):
    return f"{item.get('title', '')} {item.get('url', '')}".lower()


def matches_keywords(item, include_keywords, exclude_keywords, mode):
    text = item_text(item)

    if include_keywords:
        include_hits = [keyword.lower() in text for keyword in include_keywords]
        if mode == "all" and not all(include_hits):
            return False
        if mode == "any" and not any(include_hits):
            return False

    if exclude_keywords:
        if any(keyword.lower() in text for keyword in exclude_keywords):
            return False

    return True


def unique_items(items):
    seen = set()
    result = []
    for item in items:
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        result.append(item)
    return result


def save_outputs(items, output_base, save_extra_formats=False):
    json_file = output_base.with_suffix(".json")

    with json_file.open("w", encoding="utf-8") as file:
        json.dump({"single_posts": items}, file, ensure_ascii=False, indent=2)

    csv_file = None
    txt_file = None
    if save_extra_formats:
        csv_file = output_base.with_suffix(".csv")
        txt_file = output_base.with_suffix(".txt")

        with csv_file.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["title", "url"])
            writer.writeheader()
            writer.writerows(items)

        with txt_file.open("w", encoding="utf-8") as file:
            for item in items:
                file.write(item["url"] + "\n")

    return json_file, csv_file, txt_file


def find_url_files():
    patterns = ["*_urls.json", "*_urls.csv", "*_urls.txt"]
    files = []
    for pattern in patterns:
        files.extend(Path(".").glob(pattern))
    files = [
        path for path in files
        if "single_posts_config" not in path.name and "selected" not in path.name
    ]
    return sorted(set(files), key=lambda path: path.name.lower())


def choose_input_file():
    files = find_url_files()
    if not files:
        raise FileNotFoundError("没有找到 URL 清单。请先运行 extract_urls.py 生成 *_urls.json。")

    print("\n找到这些 URL 清单：")
    for index, path in enumerate(files, 1):
        print(f"{index}. {path}")

    choice = input("请选择要筛选的文件编号，直接回车默认 1：").strip()
    if not choice:
        return files[0]

    try:
        selected = files[int(choice) - 1]
    except (ValueError, IndexError) as exc:
        raise ValueError("输入的编号无效。") from exc

    return selected


def interactive_args(args):
    input_path = Path(args.input) if args.input else choose_input_file()
    non_interactive = any([
        args.input,
        args.include is not None,
        args.exclude is not None,
        args.mode,
        args.output,
        args.limit,
    ])

    include = args.include
    if include is None and not non_interactive:
        include = input("\n想包含哪些关键词？多个词用空格隔开，直接回车表示全部保留：").strip()
    elif include is None:
        include = ""

    exclude = args.exclude
    if exclude is None and not non_interactive:
        exclude = input("想排除哪些关键词？多个词用空格隔开，直接回车表示不排除：").strip()
    elif exclude is None:
        exclude = ""

    mode = args.mode
    if include and not args.mode and not non_interactive:
        mode_choice = input("关键词匹配方式：1=命中任意一个即可，2=必须全部命中，直接回车默认 1：").strip()
        mode = "all" if mode_choice == "2" else "any"

    output = args.output
    if not output and not non_interactive:
        output = input("输出文件名前缀，直接回车自动生成：").strip()

    return input_path, include, exclude, mode or "any", output


def main():
    parser = argparse.ArgumentParser(description="从 extract_urls.py 生成的 URL 清单里快速筛选帖子")
    parser.add_argument("--input", "-i", default="", help="URL 清单文件，支持 .json/.csv/.txt")
    parser.add_argument("--include", default=None, help="要包含的关键词，多个词用空格或逗号分隔")
    parser.add_argument("--exclude", default=None, help="要排除的关键词，多个词用空格或逗号分隔")
    parser.add_argument(
        "--mode",
        choices=["any", "all"],
        default="",
        help="include 关键词匹配方式：any=任意命中，all=全部命中",
    )
    parser.add_argument("--output", "-o", default="", help="输出文件名前缀")
    parser.add_argument("--limit", type=int, default=0, help="最多输出多少条，0 表示不限制")
    parser.add_argument(
        "--save-extra-formats",
        action="store_true",
        help="额外生成 .csv 和 .txt。默认只生成 JSON。",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("豆瓣小组 URL 快速筛选器")
    print("=" * 60)

    try:
        input_path, include_text, exclude_text, mode, output = interactive_args(args)
        include_keywords = split_keywords(include_text)
        exclude_keywords = split_keywords(exclude_text)

        items = unique_items(read_items(input_path))
        selected = [
            item for item in items
            if matches_keywords(item, include_keywords, exclude_keywords, mode)
        ]
        if args.limit > 0:
            selected = selected[:args.limit]

        if output:
            output_base = Path(safe_name(output))
        else:
            output_base = input_path.with_name(f"{input_path.stem}_selected_single_posts_config")

        json_file, csv_file, txt_file = save_outputs(
            selected,
            output_base,
            save_extra_formats=args.save_extra_formats,
        )

        print("\n筛选完成")
        print(f"原始 URL 数量：{len(items)}")
        print(f"筛选后数量：{len(selected)}")
        print(f"指定帖子配置：{json_file}")
        if args.save_extra_formats:
            print(f"表格预览文件：{csv_file}")
            print(f"纯 URL 文本：{txt_file}")

        if selected:
            print("\n前 20 条预览：")
            for index, item in enumerate(selected[:20], 1):
                print(f"{index}. {item['title']}")
            if len(selected) > 20:
                print(f"... 还有 {len(selected) - 20} 条")

        print("\n下一步：把生成的 JSON 内容复制到 douban_group_downloader_captcha/config.json，")
        print("然后运行 douban_group_downloader_captcha/download_posts.py。")

    except Exception as exc:
        print(f"处理失败：{exc}")


if __name__ == "__main__":
    main()
