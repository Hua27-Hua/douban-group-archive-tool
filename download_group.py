import os
import json
import time
import re
import hashlib
import base64
import argparse
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

IMAGE_ATTRS = (
    'data-original',
    'data-origin-src',
    'data-photo-url',
    'data-orig',
    'data-raw-src',
    'data-src',
    'src',
)
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.avif'}
IMAGE_MAGIC_EXTS = {
    b'\xff\xd8\xff': '.jpg',
    b'\x89PNG\r\n\x1a\n': '.png',
    b'GIF87a': '.gif',
    b'GIF89a': '.gif',
    b'BM': '.bmp',
}
AD_SELECTORS = [
    '[id^="dale_"]',
    '[ad-status]',
    '[id^="gdt-ad"]',
    '#gdt-ad-container',
    '.ad-topic-lable',
    '.aside',
    'iframe',
]
AD_URL_KEYWORDS = (
    'erebor.douban.com',
    'gdtimg.com',
    'gtimg.com/union',
    'doubleclick.net',
    'googlesyndication.com',
    '/ad/',
    'ad=',
    'ad_type=',
)
AD_TEXT_MARKERS = (
    'dale_',
    'doubanadslots',
    'gdt-ad',
    'gdtimg.com',
    'erebor.douban.com',
)
CONTENT_SELECTORS = [
    '#content .article',
    '#content',
]


def init_driver():
    """初始化浏览器驱动"""
    print("正在初始化浏览器...")
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    print("✓ 浏览器初始化完成")
    return driver


def login(driver):
    """登录豆瓣"""
    print("\n" + "=" * 60)
    print("请先登录豆瓣")
    print("=" * 60)
    driver.get("https://www.douban.com")
    time.sleep(3)
    input("登录完成后按回车继续...")
    print("✓ 登录成功")
    return True


def get_session_from_driver(driver):
    """从 Selenium 获取 cookies 创建 requests session"""
    session = requests.Session()

    # 复制所有 cookies
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'])

    # 设置请求头
    session.headers.update({
        'User-Agent': driver.execute_script("return navigator.userAgent;"),
        'Referer': 'https://www.douban.com/',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })

    return session


def is_ad_url(url):
    lower_url = url.lower()
    return any(keyword in lower_url for keyword in AD_URL_KEYWORDS)


def remove_ad_blocks(soup):
    for tag in soup.find_all(['script', 'noscript']):
        marker_text = ' '.join([
            tag.get('src', ''),
            tag.get_text(' ', strip=True),
        ]).lower()
        if any(marker in marker_text for marker in AD_TEXT_MARKERS):
            tag.decompose()

    for selector in AD_SELECTORS:
        for tag in soup.select(selector):
            tag.decompose()

    for tag in soup.find_all(True):
        if not getattr(tag, 'attrs', None):
            continue
        text = ' '.join(
            str(value) for key, value in tag.attrs.items()
            if key in ('id', 'class', 'data-type', 'data-sell-type')
        ).lower()
        ad_tokens = ('dale_', 'gdt-ad', ' ad-', '-ad', '_ad', 'advert', 'sponsor')
        if any(token in f' {text}' for token in ad_tokens) or tag.get_text(strip=True)[:10] == '广告':
            tag.decompose()


def remove_scripts(soup):
    for tag in soup.find_all(['script', 'noscript']):
        tag.decompose()


def remove_correct_answer_lines(soup):
    answer_markers = ('正确答案：', '正确答案:')
    block_tags = {'p', 'div', 'li', 'span', 'td', 'blockquote'}

    for text_node in list(soup.find_all(string=lambda text: text and any(marker in text for marker in answer_markers))):
        parent = text_node.parent
        if not parent or parent.name in ('script', 'style', 'noscript'):
            continue

        original_text = str(text_node)
        kept_lines = [
            line for line in original_text.splitlines()
            if not any(marker in line for marker in answer_markers)
        ]

        if not kept_lines:
            if parent.name in block_tags and parent.get_text(strip=True) == original_text.strip():
                parent.decompose()
            else:
                text_node.extract()
            continue

        text_node.replace_with('\n'.join(kept_lines))


def add_local_image_viewer(soup):
    css = """
img[src] {
    cursor: zoom-in;
}
.local-image-viewer {
    position: fixed;
    inset: 0;
    z-index: 999999;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: rgba(0, 0, 0, 0.86);
}
.local-image-viewer.is-open {
    display: flex;
}
.local-image-viewer img {
    max-width: 96vw;
    max-height: 92vh;
    width: auto;
    height: auto;
    object-fit: contain;
    cursor: zoom-out;
    background: #fff;
}
.local-image-viewer-close {
    position: fixed;
    top: 14px;
    right: 18px;
    color: #fff;
    font-size: 32px;
    line-height: 1;
    cursor: pointer;
    user-select: none;
}
.image-download-failed {
    display: inline-block;
    max-width: 100%;
    margin: 8px 0;
    padding: 10px 12px;
    border: 1px dashed #bbb;
    background: #fafafa;
    color: #666;
    font-size: 14px;
    line-height: 1.6;
}
.image-download-failed a {
    color: #3377aa;
    text-decoration: none;
}
.image-download-failed a:hover {
    text-decoration: underline;
}
"""
    js = """
(function () {
    function ready(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    ready(function () {
        var viewer = document.createElement('div');
        viewer.className = 'local-image-viewer';
        viewer.innerHTML = '<span class="local-image-viewer-close">&times;</span><img alt="">';
        document.body.appendChild(viewer);

        var viewerImg = viewer.querySelector('img');

        function findImageTarget(target) {
            while (target && target !== document && target !== viewer) {
                if (target.tagName && target.tagName.toLowerCase() === 'img' && target.getAttribute('src')) {
                    return target;
                }
                target = target.parentNode;
            }
            return null;
        }

        function closeViewer() {
            viewer.classList.remove('is-open');
            viewerImg.removeAttribute('src');
        }

        document.addEventListener('click', function (event) {
            var img = findImageTarget(event.target);
            if (!img) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            viewerImg.src = img.currentSrc || img.src;
            viewerImg.alt = img.alt || '';
            viewer.classList.add('is-open');
        }, true);

        viewer.addEventListener('click', function (event) {
            if (event.target === viewer || event.target.className === 'local-image-viewer-close' || event.target === viewerImg) {
                closeViewer();
            }
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                closeViewer();
            }
        });
    });
})();
"""
    style_tag = soup.new_tag('style')
    style_tag.string = css
    script_tag = soup.new_tag('script')
    script_tag.string = js

    if not soup.head:
        head = soup.new_tag('head')
        if soup.html:
            soup.html.insert(0, head)
        else:
            soup.insert(0, head)
    soup.head.append(style_tag)

    if soup.body:
        soup.body.append(script_tag)
    else:
        soup.append(script_tag)


def pick_content_root(soup):
    for selector in CONTENT_SELECTORS:
        root = soup.select_one(selector)
        if root:
            return root
    return soup


def pick_image_src(img):
    for attr in IMAGE_ATTRS:
        src = img.get(attr)
        if src and not src.startswith('data:'):
            return src.strip()

    srcset = img.get('srcset')
    if srcset:
        candidates = [item.strip().split()[0] for item in srcset.split(',') if item.strip()]
        if candidates:
            return candidates[-1]

    return ''


def image_filename(img_url):
    parsed = urlparse(img_url)
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext not in IMAGE_EXTS:
        ext = '.jpg'

    digest = hashlib.md5(img_url.encode('utf-8')).hexdigest()[:12]
    return f"img_{digest}{ext}"


def detect_image_ext(data):
    for magic, ext in IMAGE_MAGIC_EXTS.items():
        if data.startswith(magic):
            return ext
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return '.webp'
    if len(data) >= 12 and data[4:8] == b'ftyp' and data[8:12] in (b'avif', b'avis'):
        return '.avif'
    return ''


def is_valid_image_file(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    try:
        with open(path, 'rb') as f:
            return bool(detect_image_ext(f.read(32)))
    except OSError:
        return False


def existing_valid_image_path(save_path):
    base, ext = os.path.splitext(save_path)
    candidates = [save_path]
    candidates.extend(base + image_ext for image_ext in IMAGE_EXTS if image_ext != ext)
    for candidate in candidates:
        if is_valid_image_file(candidate):
            return candidate
    return ''


def image_url_candidates(img_url):
    candidates = []

    def add_candidate(url):
        if url not in candidates:
            candidates.append(url)

    add_candidate(img_url)
    replacements = [
        ('/view/richtext/s/', '/view/richtext/large/'),
        ('/view/richtext/s/', '/view/richtext/raw/'),
        ('/view/richtext/s/', '/view/richtext/l/'),
        ('/view/richtext/m/', '/view/richtext/large/'),
        ('/view/richtext/m/', '/view/richtext/raw/'),
        ('/view/richtext/l/', '/view/richtext/large/'),
        ('/view/richtext/l/', '/view/richtext/raw/'),
        ('/view/richtext/large/', '/view/richtext/raw/'),
        ('/view/richtext/large/', '/view/richtext/l/'),
        ('/view/richtext/large/', '/view/richtext/s/'),
        ('/view/richtext/large/public/', '/view/richtext/public/'),
        ('/view/richtext/raw/', '/view/richtext/large/'),
        ('/view/richtext/raw/', '/view/richtext/l/'),
        ('/view/richtext/raw/', '/view/richtext/s/'),
        ('/view/richtext/raw/public/', '/view/richtext/public/'),
        ('/view/photo/l/public/', '/view/photo/raw/public/'),
        ('/view/photo/m/public/', '/view/photo/l/public/'),
        ('/view/group_topic/l/public/', '/view/group_topic/raw/public/'),
    ]
    for old, new in replacements:
        if old in img_url:
            add_candidate(img_url.replace(old, new))

    doubanio_hosts = ('img1.doubanio.com', 'img2.doubanio.com', 'img3.doubanio.com', 'img9.doubanio.com')
    for candidate in list(candidates):
        parsed = urlparse(candidate)
        if parsed.netloc in doubanio_hosts:
            for host in doubanio_hosts:
                if host != parsed.netloc:
                    add_candidate(parsed._replace(netloc=host).geturl())
    return candidates


def rewrite_image_tag(img, local_src, original_url):
    img['src'] = local_src
    img['data-archived-original-url'] = original_url
    for attr in list(img.attrs):
        if attr in IMAGE_ATTRS and attr != 'src':
            del img.attrs[attr]
        elif attr in ('srcset', 'loading', 'data-original-url', 'data-lazy-src'):
            del img.attrs[attr]


def replace_failed_image_tag(soup, img, original_url):
    wrapper = soup.new_tag('div')
    wrapper['class'] = 'image-download-failed'
    link = soup.new_tag('a', href=original_url, target='_blank', rel='noopener noreferrer')
    link.string = '图片下载失败，点击打开原图'
    wrapper.append(link)
    img.replace_with(wrapper)


def write_failed_image(post_dir, page_url, img_url, reason):
    failed_file = os.path.join(post_dir, 'failed_images.jsonl')
    with open(failed_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            'page_url': page_url,
            'image_url': img_url,
            'reason': reason,
            'saved_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }, ensure_ascii=False) + '\n')


def save_image_bytes(data, save_path):
    detected_ext = detect_image_ext(data[:32])
    if not detected_ext:
        return ''

    final_path = save_path
    current_ext = os.path.splitext(save_path)[1].lower()
    if current_ext != detected_ext:
        final_path = os.path.splitext(save_path)[0] + detected_ext

    with open(final_path, 'wb') as f:
        f.write(data)
    return final_path


def download_image_with_browser(driver, img_url, save_path):
    if not driver:
        return '', '浏览器不可用'

    original_page = driver.current_url
    failures = []
    for candidate_url in image_url_candidates(img_url):
        try:
            driver.get(candidate_url)
            time.sleep(1)
            result = driver.execute_async_script("""
                const done = arguments[arguments.length - 1];
                fetch(window.location.href, { credentials: 'include', cache: 'reload' })
                  .then(response => {
                    if (!response.ok) {
                      throw new Error('状态码 ' + response.status);
                    }
                    return response.blob();
                  })
                  .then(blob => {
                    const reader = new FileReader();
                    reader.onloadend = () => done({ ok: true, data: reader.result });
                    reader.onerror = () => done({ ok: false, error: '读取图片失败' });
                    reader.readAsDataURL(blob);
                  })
                  .catch(error => done({ ok: false, error: String(error) }));
            """)

            if not result or not result.get('ok'):
                failures.append(f"{candidate_url} ({(result or {}).get('error', '浏览器读取失败')})")
                continue

            data_url = result.get('data', '')
            if ',' not in data_url or not data_url.startswith('data:image/'):
                failures.append(f"{candidate_url} (非图片数据)")
                continue

            image_data = base64.b64decode(data_url.split(',', 1)[1])
            final_path = save_image_bytes(image_data, save_path)
            if final_path:
                try:
                    driver.get(original_page)
                except Exception:
                    pass
                return final_path, ''
            failures.append(f"{candidate_url} (非有效图片)")
        except Exception as e:
            failures.append(f"{candidate_url} ({str(e)[:80]})")

    try:
        driver.get(original_page)
    except Exception:
        pass

    return '', '; '.join(failures) or '浏览器兜底下载失败'


def download_image(session, img_url, save_path, referer, driver=None):
    """下载单张图片"""
    try:
        existing_path = existing_valid_image_path(save_path)
        if existing_path:
            return existing_path, ''

        headers = {
            'Referer': referer,
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
        }
        failures = []
        for candidate_url in image_url_candidates(img_url):
            response = session.get(candidate_url, headers=headers, timeout=30, allow_redirects=True)
            if response.status_code != 200:
                reason = f"状态码 {response.status_code}"
                failures.append(f"{candidate_url} ({reason})")
                print(f"  ⚠️ 图片下载失败 ({reason}): {candidate_url}")
                continue

            content_type = response.headers.get('Content-Type', '').lower()
            final_path = save_image_bytes(response.content, save_path)
            if not final_path:
                kind = content_type or 'unknown'
                failures.append(f"{candidate_url} (非图片响应 {kind})")
                print(f"  ⚠️ 跳过非图片响应 ({kind}): {candidate_url}")
                continue

            return final_path, ''

        browser_path, browser_reason = download_image_with_browser(driver, img_url, save_path)
        if browser_path:
            return browser_path, ''
        if browser_reason:
            failures.append(f"浏览器兜底失败：{browser_reason}")

        return '', '; '.join(failures) or '所有候选地址均下载失败'
    except Exception as e:
        reason = str(e)[:120]
        print(f"  ⚠️ 图片下载出错: {reason[:50]}")
        return '', reason


def process_images_in_html(html_content, base_url, post_dir, session, driver=None, filter_correct_answers=True):
    """
    处理 HTML 中的图片：下载到本地并替换链接
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    remove_ad_blocks(soup)
    remove_scripts(soup)
    if filter_correct_answers:
        remove_correct_answer_lines(soup)
    add_local_image_viewer(soup)

    # 创建图片保存目录
    images_dir = os.path.join(post_dir, 'images')
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    # 只下载正文区域图片，避免把导航、侧栏和广告素材一起保存下来
    content_root = pick_content_root(soup)
    img_tags = content_root.find_all('img')

    if not img_tags:
        return str(soup)

    print(f"  发现 {len(img_tags)} 张图片，开始下载...")

    downloaded = 0
    skipped = 0
    for img in img_tags:
        src = pick_image_src(img)
        if not src:
            skipped += 1
            continue

        # 处理相对路径
        img_url = urljoin(base_url, src)
        if is_ad_url(img_url):
            skipped += 1
            continue

        # 生成本地文件名
        img_filename = image_filename(img_url)
        img_path = os.path.join(images_dir, img_filename)

        # 下载图片
        saved_path, fail_reason = download_image(session, img_url, img_path, base_url, driver=driver)
        if saved_path:
            # 替换为本地相对路径
            rewrite_image_tag(img, f"images/{os.path.basename(saved_path)}", img_url)
            downloaded += 1
        else:
            replace_failed_image_tag(soup, img, img_url)
            write_failed_image(post_dir, base_url, img_url, fail_reason)
            skipped += 1

    print(f"  ✓ 成功下载 {downloaded}/{len(img_tags)} 张图片，跳过 {skipped} 张")

    return str(soup)


def get_discussions(driver, groupid, groupname):
    """获取小组所有讨论帖子链接"""
    print(f"\n{'=' * 60}")
    print(f"开始获取 {groupname}_{groupid} 小组的帖子列表")
    print(f"{'=' * 60}")

    discussion_urls = []

    # 访问小组首页
    group_url = f'https://www.douban.com/group/{groupid}/discussion?start=0&type=new'
    driver.get(group_url)
    time.sleep(3)

    page_num = 1

    while True:
        print(f"\n正在获取第 {page_num} 页帖子列表...")

        try:
            # 等待页面加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.olt, #content"))
            )
            time.sleep(2)

            # 获取页面源码
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # 查找所有帖子链接
            results = soup.find_all('td', attrs={'class': 'title'})

            if not results:
                print("⚠️ 未找到帖子，可能需要重新登录或已到最后一页")
                break

            page_count = 0
            for result in results:
                s_result = result.find('a')
                if s_result:
                    link = s_result.get('href', '')
                    title = s_result.get('title', s_result.text.strip())
                    if link and title:
                        discussion_urls.append({'link': link, 'title': title})
                        page_count += 1

            print(f"✓ 本页获取 {page_count} 个帖子，累计 {len(discussion_urls)} 个")

            # 查找下一页按钮
            next_page = soup.find('span', attrs={'class': 'next'})
            if not next_page:
                print("✓ 已到最后一页")
                break

            next_link = next_page.find('a')
            if not next_link:
                print("✓ 已到最后一页")
                break

            # 访问下一页
            next_url = next_link.get('href')
            if next_url:
                driver.get(next_url)
                time.sleep(3)
                page_num += 1
            else:
                break

        except Exception as e:
            print(f"⚠️ 获取帖子列表出错: {str(e)}")
            break

    print(f"\n✓ 共获取 {len(discussion_urls)} 个帖子")
    return discussion_urls


def save_discussion_with_images(driver, session, discussion_url, post_dir, filter_correct_answers=True):
    """保存单个帖子的所有页面（含图片）"""
    link = discussion_url['link']
    title = discussion_url['title']

    page_count = 1

    while True:
        try:
            print(f"  正在保存第 {page_count} 页...")

            # 访问帖子页面
            driver.get(link)
            time.sleep(3)

            # 等待页面加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "content"))
            )
            time.sleep(2)

            # 获取页面源码
            page_source = driver.page_source

            # 处理图片：下载并替换链接
            processed_html = process_images_in_html(
                page_source,
                link,
                post_dir,
                session,
                driver=driver,
                filter_correct_answers=filter_correct_answers,
            )

            # 保存 HTML
            html_filename = os.path.join(post_dir, f'{page_count}.html')
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(processed_html)

            print(f"  ✓ 第 {page_count} 页保存完成")

            # 查找下一页
            soup = BeautifulSoup(page_source, 'html.parser')
            next_page = soup.find('span', attrs={'class': 'next'})

            if not next_page:
                break

            next_link = next_page.find('a')
            if not next_link:
                break

            link = next_link.get('href')
            if not link:
                break

            page_count += 1
            time.sleep(2)

        except Exception as e:
            print(f"  ⚠️ 保存第 {page_count} 页出错: {str(e)}")
            break

    return page_count


def save_discussions(driver, groupid, groupname, discussion_urls, filter_correct_answers=True):
    """保存所有讨论帖子的内容（含图片）"""
    group_dir = f'{groupname}_{groupid}'

    # 创建保存文件夹
    if os.path.exists(group_dir):
        print(f"\n{group_dir} 文件夹已存在，请注意不要误覆盖文件！")
        print("输入大写字母 Y 继续保存文件：", end='')
        s = input()
        if s != 'Y':
            print(f"退出保存 {group_dir}。")
            return
    else:
        os.makedirs(group_dir)

    # 创建 requests session（用于下载图片）
    session = get_session_from_driver(driver)

    # 开始保存帖子
    total = len(discussion_urls)
    success_count = 0

    for index, discussion_url in enumerate(discussion_urls, 1):
        title = discussion_url['title']

        print(f"\n{'=' * 60}")
        print(f"[{index}/{total}] 保存帖子：{title}")
        print(f"{'=' * 60}")

        # 创建帖子文件夹（处理文件名非法字符）
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        safe_title = safe_title[:100]  # 限制文件名长度
        post_dir = os.path.join(group_dir, safe_title)

        try:
            if not os.path.exists(post_dir):
                os.makedirs(post_dir)

            # 保存帖子（含图片）
            pages_saved = save_discussion_with_images(
                driver,
                session,
                discussion_url,
                post_dir,
                filter_correct_answers=filter_correct_answers,
            )

            if pages_saved > 0:
                print(f"✓ 帖子保存完成，共 {pages_saved} 页")
                success_count += 1
            else:
                print(f"⚠️ 帖子保存失败")

            # 保存帖子元信息
            meta_file = os.path.join(post_dir, 'meta.json')
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'title': title,
                    'link': discussion_url['link'],
                    'pages': pages_saved,
                    'saved_at': time.strftime('%Y-%m-%d %H:%M:%S')
                }, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"⚠️ 保存帖子出错: {str(e)}")
            continue

        # 避免请求过快
        time.sleep(2)

    print(f"\n{'=' * 60}")
    print(f"✅ 所有帖子保存完成！")
    print(f"   成功: {success_count}/{total}")
    print(f"   保存位置: {os.path.abspath(group_dir)}")
    print(f"{'=' * 60}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='豆瓣小组帖子本地存档工具')
    parser.add_argument(
        '--keep-correct-answer',
        action='store_true',
        help='保留帖子问答里的“正确答案：”行。默认会删除这些行。',
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("豆瓣小组爬虫 - Selenium 版（含图片下载）")
    print("=" * 60)
    if args.keep_correct_answer:
        print("保留问答正确答案行：开启")
    else:
        print("过滤问答正确答案行：开启")

    # 读取配置文件
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("⚠️ 未找到 config.json 文件")
        print("请创建 config.json 文件，格式如下：")
        print(json.dumps({
            "grouplist": [
                {"groupid": "your_group_id", "groupname": "your_group_name"}
            ]
        }, ensure_ascii=False, indent=2))
        return

    # 初始化浏览器
    driver = init_driver()

    try:
        # 登录
        if not login(driver):
            print("登录失败，程序退出")
            return

        # 处理每个小组
        for group in config['grouplist']:
            groupid = group['groupid']
            groupname = group['groupname']

            # 获取帖子列表
            discussion_urls = get_discussions(driver, groupid, groupname)

            if not discussion_urls:
                print(f"⚠️ 小组 {groupname}_{groupid} 没有获取到帖子")
                continue

            # 保存帖子（含图片）
            save_discussions(
                driver,
                groupid,
                groupname,
                discussion_urls,
                filter_correct_answers=not args.keep_correct_answer,
            )

        print("\n🎉 所有任务完成！")

    except Exception as e:
        print(f"\n⚠️ 程序出错: {str(e)}")

    finally:
        try:
            input("\n按回车关闭浏览器...")
        except:
            pass
        driver.quit()


if __name__ == '__main__':
    main()
