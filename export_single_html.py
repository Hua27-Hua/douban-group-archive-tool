import argparse
import base64
import hashlib
import mimetypes
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup


OUTPUT_DIR_NAME = "_single_html_exports"
IMAGE_ATTRS = (
    "data-archived-original-url",
    "data-original",
    "data-origin-src",
    "data-photo-url",
    "data-orig",
    "data-raw-src",
    "data-src",
    "src",
)
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif"}
IMAGE_MAGIC = {
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG\r\n\x1a\n": ".png",
    b"GIF87a": ".gif",
    b"GIF89a": ".gif",
    b"RIFF": ".webp",
    b"BM": ".bmp",
}
DOUBANIO_HOSTS = ("img1.doubanio.com", "img2.doubanio.com", "img3.doubanio.com", "img9.doubanio.com")
DECORATION_URL_MARKERS = (
    "/group-static/pics/uploader.png",
    "/pics/nav/",
    "/pics/icon/",
    "/favicon",
)
DECORATION_CLASSES = {
    "upload-icon",
    "remove-img",
}


try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


LOCAL_STYLE = """
html {
  background: #f4f3ee;
}
body {
  box-sizing: border-box;
  max-width: 1120px;
  min-height: 100vh;
  margin: 0 auto;
  padding: 0 42px 64px;
  color: #1f2a2a;
  background: #fff;
  font: 16px/1.72 -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
}
* {
  box-sizing: border-box;
}
a {
  color: #00715d;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}
img {
  max-width: min(100%, 720px);
  height: auto;
  cursor: zoom-in;
}
p {
  margin: 0 0 12px;
}
h1 {
  margin: 0;
  padding: 30px 0 18px;
  color: #111;
  font-size: 26px;
  line-height: 1.35;
  font-weight: 700;
  border-bottom: 1px solid #e5e1d9;
}
h2 {
  margin: 28px 0 14px;
  color: #333;
  font-size: 19px;
}
h3,
h4 {
  margin: 0 0 14px;
  color: #667071;
  font-size: 15px;
  line-height: 1.45;
  font-weight: 600;
}
h3 .from a,
h4 > a:first-child,
.from a {
  color: #00715d;
  font-size: 18px;
  font-weight: 700;
}
.manager-icon,
.owner-icon {
  display: inline-block;
  margin: 0 6px;
  padding: 0 4px;
  border-radius: 3px;
  color: #fff;
  background: #6f8f63;
  font-size: 13px;
  line-height: 1.45;
}
.pubtime,
.topic-meta,
.create-time,
.update-time,
.ip-location {
  color: #697577;
  font-size: 14px;
  font-weight: 600;
}
blockquote {
  margin: 10px 0 16px;
  padding: 10px 14px;
  color: #334343;
  border-left: 3px solid #d7ded4;
  background: #f4f5f1;
}
pre, code {
  white-space: pre-wrap;
  word-break: break-word;
}
table {
  max-width: 100%;
  border-collapse: collapse;
}

.article {
  max-width: 100%;
  margin: 0 auto;
}
#content,
.article,
.mod,
.mod-bd {
  width: 100% !important;
}
#topic-content.topic-content,
.comment-item {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  column-gap: 18px;
  max-width: 100%;
}
#topic-content.topic-content {
  padding: 26px 0 28px;
  border-bottom: 1px solid #e5e1d9;
}
.comment-item {
  margin: 0;
  padding: 28px 0 30px;
  border-bottom: 1px solid #e5e1d9;
  list-style: none;
}
.reply-doc,
.topic-doc,
.rich-content,
.topic-richtext,
.reply-content,
.markdown {
  min-width: 0;
  max-width: 100%;
}
.bg-img-green {
  background: transparent !important;
}
.reply-content,
.topic-richtext {
  color: #1f2a2a;
  font-size: 17px;
}
.reply-content {
  margin-top: 6px;
  clear: both;
}
.markdown {
  white-space: normal;
  word-break: break-word;
}
.markdown blockquote,
.reply-quote,
.ref-comment {
  margin: 8px 0 16px;
  padding: 10px 14px;
  color: #405050;
  border-left: 3px solid #d7ded4;
  background: #f4f5f1;
}
.user-face,
.avatar {
  flex-shrink: 0;
  width: 58px;
}
.user-face a,
.avatar a {
  display: block;
}
.user-face img,
.avatar img,
img.pil {
  display: block;
  width: 48px !important;
  height: 48px !important;
  max-width: 48px !important;
  max-height: 48px !important;
  object-fit: cover;
  border-radius: 6px;
  background: #e8e5dd;
}
.topic-richtext img,
.reply-content img,
.markdown img,
.content img:not(.pil) {
  display: block;
  max-width: min(100%, 720px) !important;
  height: auto !important;
  margin: 12px 0;
  border-radius: 2px;
}
.comment-photos {
  display: block !important;
  clear: both;
  width: 100% !important;
  margin: 10px 0 18px !important;
  padding: 0 !important;
}
.cmt-img-wrapper,
.cmt-img {
  display: block !important;
  width: auto !important;
  height: auto !important;
  max-width: 100% !important;
  overflow: visible !important;
}
.cmt-img img,
.comment-photos img {
  display: block !important;
  width: auto !important;
  height: auto !important;
  max-width: min(100%, 720px) !important;
  max-height: none !important;
  margin: 12px 0 18px !important;
  object-fit: contain !important;
}
.clear,
.clearfix::after {
  display: none;
}
.single-file-missing-image {
  display: none !important;
}
@media (max-width: 720px) {
  body {
    padding: 0 18px 42px;
  }
  #topic-content.topic-content,
  .comment-item {
    grid-template-columns: 42px minmax(0, 1fr);
    column-gap: 12px;
  }
  .user-face,
  .avatar {
    width: 42px;
  }
  .user-face img,
  .avatar img,
  img.pil {
    width: 36px !important;
    height: 36px !important;
    max-width: 36px !important;
    max-height: 36px !important;
  }
  h1 {
    font-size: 22px;
  }
  h3 .from a,
  h4 > a:first-child,
  .from a {
    font-size: 16px;
  }
}
.single-file-lightbox {
  position: fixed;
  inset: 0;
  z-index: 999999;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(0, 0, 0, 0.82);
}
.single-file-lightbox img {
  max-width: 96vw;
  max-height: 94vh;
  cursor: zoom-out;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);
}
.single-file-lightbox.is-open {
  display: flex;
}

/* Fallback cleanup if a Douban interaction block was not removed structurally. */
#db-global-nav,
#db-nav-group,
.global-nav,
.nav,
.nav-wrap,
.nav-primary,
.nav-items,
.nav-search,
.top-nav-info,
.nav-user-account,
.top-nav-reminder,
.top-nav-doubanapp,
#footer,
.footer,
.back-to-top,
.sns-bar,
.tabs,
.topic-opts-bar,
.action-react,
.operation-div,
.operation-more,
.comment-vote,
.lnk-reply,
.lnk-delete-comment,
.lnk-reaction,
.comment-report-wrapper,
.report,
.image-download-failed,
.single-file-missing-image,
.reply-form,
.comment-form,
#last,
#reply_form {
  display: none !important;
}
"""


LIGHTBOX_SCRIPT = """
(function () {
  if (window.__doubanSingleFileLightbox) return;
  window.__doubanSingleFileLightbox = true;

  var overlay = document.createElement('div');
  overlay.className = 'single-file-lightbox';
  var enlarged = document.createElement('img');
  overlay.appendChild(enlarged);
  document.body.appendChild(overlay);

  function close() {
    overlay.classList.remove('is-open');
    enlarged.removeAttribute('src');
  }

  document.addEventListener('click', function (event) {
    var target = event.target;
    if (target && target.tagName === 'IMG' && target.currentSrc) {
      event.preventDefault();
      enlarged.src = target.currentSrc;
      overlay.classList.add('is-open');
    }
  });

  overlay.addEventListener('click', close);
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') close();
  });
}());
"""


def is_remote_url(value):
    return value.startswith("http://") or value.startswith("https://") or value.startswith("//")


def is_data_url(value):
    return value.startswith("data:")


def guess_mime(path):
    mime, _encoding = mimetypes.guess_type(path.name)
    return mime or "application/octet-stream"


def file_to_data_uri(path):
    data = path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{guess_mime(path)};base64,{encoded}"


def normalize_remote_url(value):
    if value.startswith("//"):
        return "https:" + value
    return value


def image_filename(img_url):
    parsed = urlparse(img_url)
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext not in IMAGE_EXTS:
        ext = ".jpg"

    digest = hashlib.md5(img_url.encode("utf-8")).hexdigest()[:12]
    return f"img_{digest}{ext}"


def image_url_candidates(img_url):
    candidates = []

    def add_candidate(url):
        if url and url not in candidates:
            candidates.append(url)

    img_url = normalize_remote_url(img_url)
    add_candidate(img_url)

    replacements = [
        ("/view/richtext/s/", "/view/richtext/large/"),
        ("/view/richtext/s/", "/view/richtext/raw/"),
        ("/view/richtext/s/", "/view/richtext/l/"),
        ("/view/richtext/m/", "/view/richtext/large/"),
        ("/view/richtext/m/", "/view/richtext/raw/"),
        ("/view/richtext/l/", "/view/richtext/large/"),
        ("/view/richtext/l/", "/view/richtext/raw/"),
        ("/view/richtext/large/", "/view/richtext/raw/"),
        ("/view/richtext/large/", "/view/richtext/l/"),
        ("/view/richtext/large/", "/view/richtext/s/"),
        ("/view/richtext/large/public/", "/view/richtext/public/"),
        ("/view/richtext/raw/", "/view/richtext/large/"),
        ("/view/richtext/raw/", "/view/richtext/l/"),
        ("/view/richtext/raw/", "/view/richtext/s/"),
        ("/view/richtext/raw/public/", "/view/richtext/public/"),
        ("/view/photo/l/public/", "/view/photo/raw/public/"),
        ("/view/photo/m/public/", "/view/photo/l/public/"),
        ("/view/group_topic/l/public/", "/view/group_topic/raw/public/"),
    ]
    for old, new in replacements:
        if old in img_url:
            add_candidate(img_url.replace(old, new))

    for candidate in list(candidates):
        parsed = urlparse(candidate)
        if parsed.netloc in DOUBANIO_HOSTS:
            for host in DOUBANIO_HOSTS:
                if host != parsed.netloc:
                    add_candidate(parsed._replace(netloc=host).geturl())

    return candidates


def candidate_local_files(images_dir, img_url):
    for candidate_url in image_url_candidates(img_url):
        filename = image_filename(candidate_url)
        path = images_dir / filename
        yield path

        base = path.with_suffix("")
        for ext in IMAGE_EXTS:
            if ext != path.suffix.lower():
                yield base.with_suffix(ext)


def find_archived_remote_image(html_path, img_url):
    images_dir = html_path.parent / "images"
    if not images_dir.is_dir():
        return None

    seen = set()
    for path in candidate_local_files(images_dir, img_url):
        if path in seen:
            continue
        seen.add(path)
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def detect_image_ext(data):
    for magic, ext in IMAGE_MAGIC.items():
        if data.startswith(magic):
            if ext == ".webp" and b"WEBP" not in data[:16]:
                continue
            return ext
    return None


def save_downloaded_image(images_dir, img_url, data):
    filename = image_filename(img_url)
    detected_ext = detect_image_ext(data)
    if detected_ext:
        filename = Path(filename).with_suffix(detected_ext).name

    images_dir.mkdir(parents=True, exist_ok=True)
    path = images_dir / filename
    path.write_bytes(data)
    return path


def fetch_archived_remote_image(html_path, remote_urls, session):
    images_dir = html_path.parent / "images"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Referer": "https://www.douban.com/",
    }

    seen = set()
    for remote_url in remote_urls:
        for candidate_url in image_url_candidates(remote_url):
            if candidate_url in seen:
                continue
            seen.add(candidate_url)
            try:
                response = session.get(candidate_url, headers=headers, timeout=30, allow_redirects=True)
            except requests.RequestException:
                continue

            content_type = response.headers.get("Content-Type", "").lower()
            data = response.content
            if response.status_code != 200 or not data:
                continue
            if "image" not in content_type and not detect_image_ext(data):
                continue

            return save_downloaded_image(images_dir, candidate_url, data)

    return None


def resolve_local_path(html_path, raw_src):
    if not raw_src or is_remote_url(raw_src) or is_data_url(raw_src):
        return None

    parsed = urlparse(raw_src)
    local_part = unquote(parsed.path or raw_src)
    local_part = local_part.split("#", 1)[0].split("?", 1)[0]
    if not local_part:
        return None

    candidate = (html_path.parent / local_part).resolve()
    try:
        candidate.relative_to(html_path.parent.resolve())
    except ValueError:
        return None

    return candidate if candidate.is_file() else None


def remove_remote_dependencies(soup):
    for tag in soup.find_all("script"):
        src = tag.get("src", "").strip()
        if src and is_remote_url(src):
            tag.decompose()

    for tag in soup.find_all(["link", "source"]):
        href = tag.get("href", "").strip()
        srcset = tag.get("srcset", "").strip()
        if (href and is_remote_url(href)) or (srcset and "http" in srcset):
            tag.decompose()

    for tag in soup.find_all(True):
        for attr in ("srcset", "data-srcset"):
            if attr in tag.attrs:
                del tag.attrs[attr]


def remove_douban_chrome_and_actions(soup):
    selectors = [
        "#db-global-nav",
        "#db-nav-group",
        ".global-nav",
        ".nav-wrap",
        ".nav-primary",
        ".nav-items",
        ".nav-search",
        ".top-nav-info",
        ".nav-user-account",
        ".top-nav-reminder",
        ".top-nav-doubanapp",
        "#footer",
        ".footer",
        ".back-to-top",
        ".sns-bar",
        ".tabs",
        ".topic-opts-bar",
        ".action-react",
        ".operation-div",
        ".operation-more",
        ".comment-report-wrapper",
        ".report",
        ".image-download-failed",
        ".single-file-missing-image",
        ".reply-form",
        ".comment-form",
        "#last",
        "#reply_form",
    ]
    for selector in selectors:
        for tag in soup.select(selector):
            tag.decompose()

    interaction_classes = {
        "comment-vote",
        "lnk-reply",
        "lnk-delete-comment",
        "lnk-reaction",
        "react-btn",
        "react-cancel-like",
        "react-num",
        "react-text",
    }
    for tag in list(soup.find_all(True)):
        classes = set(tag.get("class") or [])
        if classes & interaction_classes:
            tag.decompose()

    remove_text_markers = {
        "赞",
        "已赞",
        "回复",
        "投诉",
        "删除",
        "你的回复",
    }
    for tag in list(soup.find_all(["a", "button", "span", "h2"])):
        text = tag.get_text(" ", strip=True)
        if text in remove_text_markers:
            tag.decompose()


def normalize_archive_layout(soup):
    for quote in soup.select(".reply-quote-content"):
        short_content = quote.select_one(".short.ref-content")
        full_content = quote.select_one(".all.ref-content")
        if full_content:
            if short_content:
                short_content.decompose()
            full_content.attrs.pop("style", None)
            classes = [cls for cls in full_content.get("class", []) if cls != "all"]
            full_content["class"] = classes or ["ref-content"]

        for toggle in quote.select(".toggle-reply"):
            toggle.decompose()

    for tag in soup.select(".comment-photos, .cmt-img-wrapper, .cmt-img"):
        if "style" in tag.attrs:
            del tag.attrs["style"]

    for img in soup.find_all("img"):
        classes = set(img.get("class") or [])
        if "pil" in classes:
            continue
        for attr in ("style", "width", "height"):
            if attr in img.attrs:
                del img.attrs[attr]


def remote_image_urls(img):
    urls = []
    for attr in IMAGE_ATTRS:
        value = (img.get(attr) or "").strip()
        if is_remote_url(value):
            normalized = normalize_remote_url(value)
            if normalized not in urls:
                urls.append(normalized)
    return urls


def is_decoration_image(img):
    classes = set(img.get("class") or [])
    if classes & DECORATION_CLASSES:
        return True

    src = normalize_remote_url((img.get("src") or "").strip()).lower()
    if any(marker in src for marker in DECORATION_URL_MARKERS):
        return True

    parent = img.parent
    while parent and parent.name != "[document]":
        parent_classes = set(parent.get("class") or [])
        parent_id = (parent.get("id") or "").lower()
        if "img-uploader-wrapper" in parent_classes or "uploader" in parent_id:
            return True
        parent = parent.parent

    return False


def remove_image_node(img):
    parent = img.parent
    if parent and parent.name == "a" and not parent.get_text(strip=True) and len(parent.find_all("img")) == 1:
        parent.decompose()
    else:
        img.decompose()


def clean_image_attrs(img):
    for attr in IMAGE_ATTRS:
        if attr in img.attrs and attr != "src":
            del img.attrs[attr]
    for attr in ("srcset", "loading", "data-original-url", "data-lazy-src"):
        if attr in img.attrs:
            del img.attrs[attr]


def embed_images(soup, html_path, fetch_missing=False):
    embedded = 0
    recovered_remote = 0
    fetched_remote = 0
    skipped_decoration = 0
    missing_local = 0
    session = requests.Session() if fetch_missing else None

    for img in list(soup.find_all("img")):
        src = (img.get("src") or "").strip()

        if not src:
            continue

        if is_data_url(src):
            continue

        if is_remote_url(src):
            local_path = None
            remote_urls = remote_image_urls(img)
            for remote_url in remote_urls:
                local_path = find_archived_remote_image(html_path, remote_url)
                if local_path:
                    break

            if local_path:
                img["src"] = file_to_data_uri(local_path)
                clean_image_attrs(img)
                recovered_remote += 1
                continue

            if fetch_missing and session:
                local_path = fetch_archived_remote_image(html_path, remote_urls, session)
                if local_path:
                    img["src"] = file_to_data_uri(local_path)
                    clean_image_attrs(img)
                    fetched_remote += 1
                    continue

            if is_decoration_image(img):
                remove_image_node(img)
                skipped_decoration += 1
                continue

            remove_image_node(img)
            missing_local += 1
            continue

        local_path = resolve_local_path(html_path, src)
        if not local_path:
            missing_local += 1
            continue

        img["src"] = file_to_data_uri(local_path)
        clean_image_attrs(img)
        embedded += 1

    return embedded, recovered_remote, fetched_remote, skipped_decoration, missing_local


def inject_local_assets(soup):
    if soup.head is None:
        head = soup.new_tag("head")
        if soup.html:
            soup.html.insert(0, head)
        else:
            soup.insert(0, head)

    style = soup.new_tag("style")
    style.string = LOCAL_STYLE
    soup.head.append(style)

    if soup.body is None:
        body = soup.new_tag("body")
        body.extend(soup.contents)
        soup.append(body)

    script = soup.new_tag("script")
    script.string = LIGHTBOX_SCRIPT
    soup.body.append(script)


def export_html(html_path, output_path, fetch_missing=False):
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(text, "html.parser")

    remove_remote_dependencies(soup)
    remove_douban_chrome_and_actions(soup)
    normalize_archive_layout(soup)
    embedded, recovered_remote, fetched_remote, skipped_decoration, missing_local = embed_images(
        soup,
        html_path,
        fetch_missing=fetch_missing,
    )
    inject_local_assets(soup)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(str(soup), encoding="utf-8")

    return {
        "embedded": embedded,
        "recovered_remote": recovered_remote,
        "fetched_remote": fetched_remote,
        "skipped_decoration": skipped_decoration,
        "missing_local": missing_local,
    }


def iter_html_files(target):
    if target.is_file() and target.suffix.lower() in {".html", ".htm"}:
        yield target
        return

    for path in target.rglob("*"):
        if any(part.startswith("_single_html") for part in path.parts):
            continue
        if path.suffix.lower() in {".html", ".htm"}:
            yield path


def make_output_path(target, html_path, output_dir):
    if target.is_file():
        return output_dir / f"{html_path.stem}_single.html"

    relative = html_path.relative_to(target)
    return output_dir / relative


def parse_args():
    parser = argparse.ArgumentParser(
        description="把已下载的帖子 HTML 和 images/ 图片批量导出为单文件 HTML。",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="要导出的 HTML 文件或目录。默认处理当前目录。",
    )
    parser.add_argument(
        "-o",
        "--output",
        help=f"输出目录。默认在目标目录下生成 {OUTPUT_DIR_NAME}/。",
    )
    parser.add_argument(
        "--fetch-missing",
        action="store_true",
        help="导出时尝试联网补下载本地缺失的豆瓣图片。",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    target = Path(args.target).resolve()

    if not target.exists():
        print(f"找不到目标：{target}")
        return

    if args.output:
        output_dir = Path(args.output).resolve()
    elif target.is_file():
        output_dir = target.parent / OUTPUT_DIR_NAME
    else:
        output_dir = target / OUTPUT_DIR_NAME

    html_files = list(iter_html_files(target))
    if not html_files:
        print("没有找到 HTML 文件。")
        return

    total_embedded = 0
    total_recovered_remote = 0
    total_fetched_remote = 0
    total_skipped_decoration = 0
    total_missing = 0

    print(f"准备导出 {len(html_files)} 个 HTML")
    print(f"输出目录：{output_dir}")

    for html_path in html_files:
        output_path = make_output_path(target, html_path, output_dir)
        stats = export_html(html_path, output_path, fetch_missing=args.fetch_missing)
        total_embedded += stats["embedded"]
        total_recovered_remote += stats["recovered_remote"]
        total_fetched_remote += stats["fetched_remote"]
        total_skipped_decoration += stats["skipped_decoration"]
        total_missing += stats["missing_local"]
        print(f"已导出：{output_path}")

    print("\n完成")
    print(f"嵌入本地图片：{total_embedded}")
    print(f"从远程地址恢复本地图片：{total_recovered_remote}")
    print(f"联网补下载图片：{total_fetched_remote}")
    print(f"跳过页面装饰图片：{total_skipped_decoration}")
    print(f"本地未找到图片：{total_missing}")


if __name__ == "__main__":
    main()
