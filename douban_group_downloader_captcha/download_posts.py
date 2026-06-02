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


def find_local_chromedriver():
    """优先使用用户放在本地的 ChromeDriver，避免网络不好时自动下载失败。"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    search_dirs = [
        os.getcwd(),
        script_dir,
        project_dir,
        os.path.join(os.getcwd(), 'drivers'),
        os.path.join(script_dir, 'drivers'),
        os.path.join(project_dir, 'drivers'),
    ]
    names = ['chromedriver.exe', 'chromedriver']

    for folder in search_dirs:
        for name in names:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
    return ''


def build_chrome_service():
    local_driver = find_local_chromedriver()
    if local_driver:
        print(f"✓ 使用本地 ChromeDriver: {local_driver}")
        return Service(local_driver, log_output=os.devnull)

    print("未找到本地 chromedriver.exe，尝试自动下载匹配版本...")
    return Service(ChromeDriverManager().install(), log_output=os.devnull)


def init_driver():
    """初始化浏览器驱动"""
    print("正在初始化浏览器...")
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--log-level=3')
    options.add_argument('--disable-logging')

    driver = webdriver.Chrome(
        service=build_chrome_service(),
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

    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'])

    session.headers.update({
        'User-Agent': driver.execute_script("return navigator.userAgent;"),
        'Referer': 'https://www.douban.com/',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })

    return session


def expand_folded_comments(driver, max_rounds=5):
    """尽量展开被折叠的评论，再保存页面源码。"""
    total_clicked = 0
    for _ in range(max_rounds):
        try:
            clicked = driver.execute_script("""
                const markers = /(折叠|管理机器人|内容已被)/;

                function isVisible(el) {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && rect.width > 0
                        && rect.height > 0;
                }

                function shouldClick(el) {
                    if (!isVisible(el)) {
                        return false;
                    }
                    const text = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
                    const title = (el.getAttribute('title') || el.getAttribute('aria-label') || '').trim();
                    const combined = `${text} ${title}`.trim();
                    if (!combined.includes('展开')) {
                        return false;
                    }
                    if (markers.test(combined)) {
                        return true;
                    }
                    const block = el.closest('.reply-doc, .comment-item, .topic-reply, li, tr, div');
                    const blockText = block ? (block.innerText || block.textContent || '') : '';
                    return combined === '展开' && markers.test(blockText);
                }

                const candidates = Array.from(document.querySelectorAll('a, button, span, [role="button"], [onclick], .open-reply'));
                let clicked = 0;
                for (const el of candidates) {
                    if (!shouldClick(el)) {
                        continue;
                    }
                    el.scrollIntoView({ block: 'center', inline: 'nearest' });
                    el.click();
                    clicked += 1;
                }
                return clicked;
            """)
        except Exception:
            break

        if not clicked:
            break
        total_clicked += int(clicked)
        time.sleep(1.2)

    if total_clicked:
        print(f"  ✓ 已尝试展开 {total_clicked} 条折叠评论")


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


def remove_douban_people_links(soup):
    for link in list(soup.find_all('a', href=True)):
        href = link.get('href', '').strip()
        if re.search(r'(^https?://www\.douban\.com/people/|^https?://www\.douban\.com/people$|^/people/)', href):
            link.unwrap()


def remove_owner_like_markers(soup):
    markers = ('楼主赞过', '作者赞过')
    removable_tags = {'span', 'a', 'em', 'i', 'b', 'strong', 'small'}

    for text_node in list(soup.find_all(string=lambda text: text and any(marker in text for marker in markers))):
        parent = text_node.parent
        if not parent or parent.name in ('script', 'style', 'noscript'):
            continue

        text = str(text_node)
        for marker in markers:
            text = text.replace(marker, '')

        if text.strip():
            text_node.replace_with(text)
            continue

        if parent.name in removable_tags and any(marker in parent.get_text(' ', strip=True) for marker in markers):
            parent.decompose()
        else:
            text_node.extract()


def remove_display_none(style):
    parts = [
        part.strip()
        for part in (style or '').split(';')
        if part.strip() and not re.match(r'^display\s*:\s*none\s*$', part.strip(), flags=re.I)
    ]
    return '; '.join(parts)


def reveal_folded_comments(soup):
    folded_items = list(soup.select('[data-is_folded="True"], [data-is_folded="true"]'))
    for folded_msg in soup.select('.folded-msg'):
        parent = folded_msg.find_parent(['li', 'div'])
        if parent and parent not in folded_items:
            folded_items.append(parent)

    for item in folded_items:
        for content in item.select('.reply-content'):
            style = remove_display_none(content.get('style', ''))
            if style:
                content['style'] = style
            elif content.has_attr('style'):
                del content['style']

        for tag in item.select('.folded-msg, .reply-folded-reason, .folded-reason, .reply-hidden'):
            tag.decompose()

        if item.has_attr('data-is_folded'):
            item['data-is_folded'] = 'False'


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
        try:
            response = session.get(candidate_url, headers=headers, timeout=(10, 30), allow_redirects=True)
        except requests.RequestException as e:
            reason = str(e).splitlines()[0][:120]
            failures.append(f"{candidate_url} ({reason})")
            print(f"  ⚠️ 图片候选地址连接失败，继续尝试下一个: {candidate_url}")
            continue

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


def process_images_in_html(html_content, base_url, post_dir, session, driver=None, filter_correct_answers=True):
    """处理 HTML 中的图片：下载到本地并替换链接"""
    soup = BeautifulSoup(html_content, 'html.parser')
    remove_ad_blocks(soup)
    remove_scripts(soup)
    remove_douban_people_links(soup)
    remove_owner_like_markers(soup)
    reveal_folded_comments(soup)
    if filter_correct_answers:
        remove_correct_answer_lines(soup)
    add_local_image_viewer(soup)

    images_dir = os.path.join(post_dir, 'images')
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

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

        img_url = urljoin(base_url, src)
        if is_ad_url(img_url):
            skipped += 1
            continue

        img_filename = image_filename(img_url)
        img_path = os.path.join(images_dir, img_filename)

        saved_path, fail_reason = download_image(session, img_url, img_path, base_url, driver=driver)
        if saved_path:
            rewrite_image_tag(img, f"images/{os.path.basename(saved_path)}", img_url)
            downloaded += 1
        else:
            replace_failed_image_tag(soup, img, img_url)
            write_failed_image(post_dir, base_url, img_url, fail_reason)
            skipped += 1

    print(f"  ✓ 成功下载 {downloaded}/{len(img_tags)} 张图片，跳过 {skipped} 张")

    return str(soup)


def save_single_post(driver, session, post_url, post_dir, filter_correct_answers=True):
    """保存单个帖子的所有页面（含图片）"""
    link = post_url
    page_count = 1

    while True:
        try:
            print(f"  正在保存第 {page_count} 页...")

            driver.get(link)
            time.sleep(3)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "content"))
            )
            time.sleep(2)

            expand_folded_comments(driver)
            page_source = driver.page_source

            processed_html = process_images_in_html(
                page_source,
                link,
                post_dir,
                session,
                driver=driver,
                filter_correct_answers=filter_correct_answers,
            )

            html_filename = os.path.join(post_dir, f'{page_count}.html')
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(processed_html)

            print(f"  ✓ 第 {page_count} 页保存完成")

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


def choose_correct_answer_mode(args):
    if args.keep_correct_answer:
        return True
    if args.filter_correct_answer:
        return False

    print("\n是否保留帖子问答里的“正确答案：”？")
    print("1. 不保留，自动删除正确答案（推荐）")
    print("2. 保留正确答案")
    choice = input("请输入 1 或 2，直接回车默认 1：").strip()
    return choice == '2'


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='豆瓣指定帖子本地存档工具')
    parser.add_argument(
        '--keep-correct-answer',
        action='store_true',
        help='保留帖子问答里的“正确答案：”行。默认会删除这些行。',
    )
    parser.add_argument(
        '--filter-correct-answer',
        action='store_true',
        help='删除帖子问答里的“正确答案：”行，用于跳过启动时的交互选择。',
    )
    args = parser.parse_args()
    keep_correct_answer = choose_correct_answer_mode(args)

    print("\n" + "=" * 60)
    print("豆瓣批量单帖子爬虫")
    print("=" * 60)
    if keep_correct_answer:
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
            "single_posts": [
                {
                    "url": "https://www.douban.com/group/topic/123456/",
                    "title": "帖子标题"
                }
            ]
        }, ensure_ascii=False, indent=2))
        return

    # 获取帖子列表
    posts = config.get('single_posts', [])

    if not posts:
        print("⚠️ config.json 中没有找到 single_posts 配置")
        return

    print(f"\n✓ 从配置文件读取到 {len(posts)} 个帖子")

    # 初始化浏览器
    driver = init_driver()

    try:
        # 登录
        if not login(driver):
            print("登录失败，程序退出")
            return

        # 创建session
        session = get_session_from_driver(driver)

        # 创建保存目录
        base_dir = 'single_posts'
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # 批量保存帖子
        total = len(posts)
        success_count = 0

        for index, post in enumerate(posts, 1):
            post_url = post.get('url', '').strip()
            post_title = post.get('title', '').strip()

            if not post_url:
                print(f"\n[{index}/{total}] ⚠️ 跳过：URL为空")
                continue

            # 如果没有标题，从URL提取ID
            if not post_title:
                match = re.search(r'/topic/(\d+)', post_url)
                if match:
                    post_title = f"topic_{match.group(1)}"
                else:
                    post_title = f"post_{index}"

            print(f"\n{'=' * 60}")
            print(f"[{index}/{total}] 保存帖子：{post_title}")
            print(f"URL: {post_url}")
            print(f"{'=' * 60}")

            # 创建帖子目录
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', post_title)
            safe_title = safe_title[:100]
            post_dir = os.path.join(base_dir, safe_title)

            try:
                if not os.path.exists(post_dir):
                    os.makedirs(post_dir)

                # 保存帖子
                pages_saved = save_single_post(
                    driver,
                    session,
                    post_url,
                    post_dir,
                    filter_correct_answers=not keep_correct_answer,
                )

                if pages_saved > 0:
                    print(f"✓ 帖子保存完成，共 {pages_saved} 页")
                    success_count += 1

                    # 保存元信息
                    meta_file = os.path.join(post_dir, 'meta.json')
                    with open(meta_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'title': post_title,
                            'url': post_url,
                            'pages': pages_saved,
                            'saved_at': time.strftime('%Y-%m-%d %H:%M:%S')
                        }, f, ensure_ascii=False, indent=2)
                else:
                    print(f"⚠️ 帖子保存失败")

            except Exception as e:
                print(f"⚠️ 保存帖子出错: {str(e)}")
                continue

            # 避免请求过快
            time.sleep(2)

        print(f"\n{'=' * 60}")
        print(f"✅ 所有帖子保存完成！")
        print(f"   成功: {success_count}/{total}")
        print(f"   保存位置: {os.path.abspath(base_dir)}")
        print(f"{'=' * 60}")

    except Exception as e:
        print(f"\n⚠️ 程序出错: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        try:
            input("\n按回车关闭浏览器...")
        except:
            pass
        driver.quit()


if __name__ == '__main__':
    main()
