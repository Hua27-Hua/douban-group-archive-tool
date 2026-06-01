# 豆瓣小组帖子本地存档工具

这是一个用于本地保存豆瓣小组帖子的 Python 工具。脚本会通过浏览器登录豆瓣，保存帖子 HTML，下载帖子中的图片，并把页面里的图片地址改成本地路径，方便离线查看或之后放到静态网页服务中查看。

## 最快使用流程

先安装依赖：

```bash
pip install -r requirements.txt
```

所有脚本都可以也可以直接在 PyCharm 里打开对应脚本后点击右上角绿色运行按钮(推荐，更简单)，也可以参考下列命令行代码，在 PowerShell/终端里运行命令。

### 方式一：保存整个小组
保存整个小组：改 douban_group_downloader_qrcode/config.json，点击绿色运行按钮,运行 download_group.py

1. 修改 `douban_group_downloader_qrcode/config.json`，填入要保存的小组 ID 和小组名。
2. 运行：

```bash
cd douban_group_downloader_qrcode
python download_group.py
```

运行后会询问是否保留帖子问答里的 `正确答案：`。直接回车默认删除，输入 `2` 会保留。

如果想跳过交互，直接保留正确答案行，可以运行：

```bash
python download_group.py --keep-correct-answer
```

3. （可选但推荐）爬完后回到项目根目录，导出更适合长期保存的单文件 HTML：

```bash
cd ..
python export_single_html.py douban_group_downloader_qrcode/小组名_小组ID
```

### 方式二：只保存指定帖子
改 douban_group_downloader_captcha/config.json，点击绿色运行按钮,运行 download_posts.py  

1. 修改 `douban_group_downloader_captcha/config.json`，把要保存的帖子 URL 放进 `single_posts`。
2. 运行：

```bash
cd douban_group_downloader_captcha
python download_posts.py
```

运行后会询问是否保留帖子问答里的 `正确答案：`。直接回车默认删除，输入 `2` 会保留。

如果想跳过交互，直接保留正确答案行，可以运行：

```bash
python download_posts.py --keep-correct-answer
```

3. （可选但推荐）爬完后回到项目根目录，导出单文件 HTML：

```bash
cd ..
python export_single_html.py douban_group_downloader_captcha/single_posts
```

### 可选：先提取小组帖子 URL（此办法可指定大量帖子进行保存）

推荐流程：先用 `extract_urls.py` 提取小组帖子链接；如果链接太多，可以用 `filter_urls.py` 按关键词筛选；然后把筛出来的 JSON 配置给 `download_posts.py` 批量保存。保存完成后，推荐再用 `export_single_html.py` 导出成单文件 HTML，方便本地打开和长期保存。

如果想先从一个小组里提取帖子链接，再挑选部分帖子保存：

```bash
cd douban_group_downloader_qrcode
python extract_urls.py
```

运行后可以选择提取范围：最新讨论、精华帖、热门讨论或自定义列表页。

如果只想提取精华帖 URL，也可以直接运行：

```bash
python extract_urls.py --list-type elite
```

它会生成可复制到 `douban_group_downloader_captcha/config.json` 的指定帖子配置。

如果提取出来的 URL 太多，可以继续运行筛选脚本，按标题关键词快速挑帖子：

```bash
python filter_urls.py
```

例如只筛标题里包含“闲聊楼”或“资源”的帖子：

```bash
python filter_urls.py --input 小组名_小组ID_urls.json --include "闲聊楼 资源"
```

## 功能

- 可以批量保存整个豆瓣小组帖子。
- 可以只保存指定帖子 URL，适合精准存档少量重要帖子。
- 可以先提取小组全部帖子 URL，再按关键词筛选出自己想保存的帖子。
- 可以单独提取和保存小组精华帖。
- 可以一次放入多个帖子 URL，按顺序批量保存。
- 保存后的本地 HTML 可以离线查看，图片也会尽量一起保存下来。
- 本地 HTML 支持点击图片放大查看。
- 运行爬取脚本时可以选择是否保留帖子问答里的 `正确答案：` 行；直接回车默认过滤。
- 爬完后可以导出成单文件 HTML，更方便双击打开、整理和长期保存。

## 文件说明

```text
douban_group_downloader-main/
├─ douban_group_downloader_qrcode/
│  ├─ download_group.py                 # 按小组批量保存帖子
│  ├─ extract_urls.py                   # 从小组列表提取帖子 URL，并生成指定帖子配置
│  ├─ filter_urls.py                    # 从 URL 清单里按关键词筛选想保存的帖子
│  └─ config.json                       # 小组批量保存配置 运行前必配置
├─ douban_group_downloader_captcha/
│  ├─ download_posts.py                 # 按指定帖子 URL 保存帖子
│  └─ config.json                       # 指定帖子保存配置 
├─ export_single_html.py                # 把已下载帖子导出为单文件 HTML，推荐爬完后运行
├─ .gitignore
├─ README.md
└─ requirements.txt
```

### `download_group.py`

按小组批量保存帖子。它会读取 `douban_group_downloader_qrcode/config.json` 中的 `grouplist`，进入小组讨论列表，逐页获取帖子链接并保存内容。

运行时会询问是否保留帖子问答里的 `正确答案：` 行。直接回车默认过滤，输入 `2` 保留。

如果想跳过交互，可以使用：

```bash
python download_group.py --keep-correct-answer
python download_group.py --filter-correct-answer
```


### `download_posts.py`

按指定帖子 URL 保存。它会读取 `douban_group_downloader_captcha/config.json` 中的 `single_posts`，可以一次放入多个帖子 URL，适合快速、精准地选中并保存你需要的帖子。

运行时会询问是否保留帖子问答里的 `正确答案：` 行。直接回车默认过滤，输入 `2` 保留。

如果想跳过交互，可以使用：

```bash
python download_posts.py --keep-correct-answer
python download_posts.py --filter-correct-answer
```


### `extract_urls.py`

辅助指定帖子 URL 使用，和 `download_group.py` 放在同一个目录里，共用 `douban_group_downloader_qrcode/config.json` 里的小组配置。它会从小组讨论列表、精华帖列表或自定义列表页提取帖子 URL。默认只生成 JSON 文件：

```text
小组名_小组ID_urls.json
小组名_小组ID_urls_single_posts_config.json
```

其中 `小组名_小组ID_urls_single_posts_config.json` 是给 `download_posts.py` 使用的配置格式。你可以把它的内容复制到 `douban_group_downloader_captcha/config.json`，然后运行指定帖子下载脚本。

如果还想额外生成 CSV 或 TXT，运行时加 `--save-extra-formats`。

如果提取的是精华帖，文件名会带上 `_elite`，例如 `小组名_小组ID_elite_urls_single_posts_config.json`，避免覆盖普通讨论列表提取结果。

### `filter_urls.py`

URL 快速筛选工具。先用 `extract_urls.py` 批量提取小组全部帖子 URL，再用这个脚本按标题关键词筛选，适合从几百上千个帖子里快速挑出想保存的内容。

可以直接交互运行：

```bash
cd douban_group_downloader_qrcode
python filter_urls.py
```

也可以用命令直接筛：

```bash
python filter_urls.py --input 小组名_小组ID_urls.json --include "闲聊楼 资源" --exclude "投票"
```

`--include` 里的多个关键词默认命中任意一个就会保留。若希望必须同时命中所有关键词，加：

```bash
python filter_urls.py --input 小组名_小组ID_urls.json --include "书 女性" --mode all
```

筛选后默认只生成 `*_selected_single_posts_config.json`，把它的内容复制到 `douban_group_downloader_captcha/config.json` 后，就可以运行 `download_posts.py` 精准保存这些帖子。

如果还想额外生成 CSV 或 TXT，运行时加：

```bash
python filter_urls.py --input 小组名_小组ID_urls.json --include "闲聊楼 资源" --save-extra-formats
```

### `export_single_html.py`

单文件导出工具。它用于爬取完成之后，把已经保存好的 `1.html` 和 `images/` 图片整合成单个 HTML 文件。导出的 HTML 可以直接在资源管理器里双击打开，不再依赖旁边的 `images/` 文件夹。

导出时会移除远程 CSS/JS 依赖，并注入一份简洁的阅读样式。

强烈推荐在爬完帖子后都运行一次这个脚本，把结果整理成更方便长期保存和分享的单文件 HTML。

## 环境准备

需要安装：

- Python 3
- Chrome 浏览器

安装依赖：

```bash
pip install -r requirements.txt
```

## 配置说明

首次运行前，需要先修改对应目录里的 `config.json`。仓库自带的是示例配置，不能直接用于真实爬取。

### 小组批量保存配置

编辑 `douban_group_downloader_qrcode/config.json`：

```json
{
  "grouplist": [
    {
      "groupid": "123456",
      "groupname": "示例小组"
    }
  ]
}
```

`groupid` 是小组主页 URL 中的 ID，例如：

```text
https://www.douban.com/group/123456/
```

上面这个小组 URL 里，需要填进配置的是 `123456`，不是整条 URL。`groupname` 可以自己取一个容易识别的名字，它会用于本地输出文件夹名。

如果要保存多个小组，可以在 `grouplist` 里继续增加：

```json
{
  "grouplist": [
    {
      "groupid": "123456",
      "groupname": "示例小组一"
    },
    {
      "groupid": "234567",
      "groupname": "示例小组二"
    }
  ]
}
```

### 指定帖子保存配置

编辑 `douban_group_downloader_captcha/config.json`：

```json
{
  "single_posts": [
    {
      "url": "https://www.douban.com/group/topic/123456789/",
      "title": "示例帖子一"
    },
    {
      "url": "https://www.douban.com/group/topic/234567890/",
      "title": "示例帖子二"
    },
    {
      "url": "https://www.douban.com/group/topic/345678901/",
      "title": "示例帖子三"
    }
  ]
}
```

`url` 是帖子地址，`title` 会用作本地保存目录名。`single_posts` 里可以放多个帖子对象，脚本会按顺序逐个保存。

## 使用方法

### 在 PyCharm 里运行

如果你不熟悉命令行，可以直接在 PyCharm 左侧文件栏打开脚本，然后点击右上角绿色运行按钮。

- 保存整个小组：打开 `douban_group_downloader_qrcode/download_group.py`，点击绿色运行按钮。
- 保存指定帖子：打开 `douban_group_downloader_captcha/download_posts.py`，点击绿色运行按钮。
- 提取小组 URL：打开 `douban_group_downloader_qrcode/extract_urls.py`，点击绿色运行按钮。
- 筛选 URL：打开 `douban_group_downloader_qrcode/filter_urls.py`，点击绿色运行按钮。
- 导出单文件 HTML：打开 `export_single_html.py`，更推荐在终端里带目录参数运行。

爬取脚本运行后会打开浏览器。请在脚本打开的浏览器里登录豆瓣，登录完成后回到 PyCharm 下方运行窗口按回车继续。

如果运行 `download_group.py` 或 `download_posts.py`，程序会询问是否保留问答正确答案：

```text
1. 不保留，自动删除正确答案（推荐）
2. 保留正确答案
```

直接回车默认选择 `1`；如果要保留，输入 `2` 后回车。

### 批量保存整个小组

```bash
cd douban_group_downloader_qrcode
python download_group.py
```

程序会打开浏览器。你登录豆瓣后，在命令行按回车继续。

运行时会询问是否保留问答正确答案。直接回车默认删除；输入 `2` 会保留。

如果只想批量保存该小组的精华帖：

```bash
python download_group.py --list-type elite
```

### 保存指定帖子

```bash
cd douban_group_downloader_captcha
python download_posts.py
```

程序会按 `config.json` 中的帖子列表逐个保存。你可以把多个想保存的帖子 URL 都放进 `single_posts`，这样不用保存整个小组，也能快速精准地保存选中的帖子。

运行时会询问是否保留问答正确答案。直接回车默认删除；输入 `2` 会保留。

### 先提取 URL，再保存指定帖子

如果你想先从某个小组整理出帖子 URL，再决定保存哪些帖子，可以运行：

```bash
cd douban_group_downloader_qrcode
python extract_urls.py
```

`extract_urls.py` 会读取 `douban_group_downloader_qrcode/config.json` 里的 `grouplist`。也就是说，如果你要提取某个小组的帖子 URL，先改这个小组配置，再运行 `extract_urls.py`。

如果只想提取精华帖 URL：

```bash
python extract_urls.py --list-type elite
```

如果豆瓣页面入口比较特殊，也可以复制浏览器里打开的列表页地址，直接指定：

```bash
python extract_urls.py --custom-url "https://www.douban.com/group/123456/discussion?start=0&type=elite"
```

运行完成后，可以打开生成的 `小组名_小组ID_urls_single_posts_config.json`，把里面的内容复制到 `douban_group_downloader_captcha/config.json`，再运行：

如果 URL 太多，可以先筛选：

```bash
python filter_urls.py
```

比如只保留标题里包含“闲聊楼”或“资源”的帖子：

```bash
python filter_urls.py --input 小组名_小组ID_urls.json --include "闲聊楼 资源"
```

```bash
cd ../douban_group_downloader_captcha
python download_posts.py
```

### 导出单文件 HTML

爬取完成后，可以把某个小组目录批量导出为单文件 HTML：缺点是html文件会较大，优点是删去了豆瓣冗余页面功能，后续豆瓣更新页面也不影响现有页面留存。

```bash
python export_single_html.py douban_group_downloader_qrcode/小组名_小组ID
```

也可以导出指定帖子保存目录：

```bash
python export_single_html.py douban_group_downloader_captcha/single_posts
```

如果是旧存档，原 HTML 里仍有豆瓣远程图片地址，可以让导出工具补下载缺失图片：

```bash
python export_single_html.py douban_group_downloader_qrcode/小组名_小组ID --fetch-missing
```

默认会在目标目录下生成 `_single_html_exports/`。导出的每个 HTML 都是独立文件，可以直接双击打开。

## 本地 HTML 和图片

每个帖子目录中的 HTML 会引用同目录下的 `images/` 文件夹：

```text
帖子标题/
├─ 1.html
└─ images/
   ├─ img_xxx.jpg
   └─ img_xxx.webp
```

打开 HTML 时，请保持 `images/` 文件夹和 HTML 的相对位置不变。点击图片可以放大；点击背景、图片本身或按 `Esc` 可以关闭。

如果图片下载失败，页面里会显示“图片下载失败，点击打开原图”，并在 `failed_images.jsonl` 中记录失败信息。

## 上线和查看 HTML

推荐在爬完帖子后先运行 `export_single_html.py` 导出单文件 HTML。导出的文件已经嵌入本地图片和阅读样式，可以直接在资源管理器里双击打开，也更适合之后上传到静态网站查看。

如果查看的是未导出的原始保存结果，需要打开具体的 HTML 文件，例如：

```text
帖子标题/1.html
```

只打开“帖子标题”这个文件夹时，静态网站通常会寻找 `index.html`。如果这个文件夹里没有 `index.html`，页面可能会一直加载或显示目录错误。使用单文件导出后，可以直接打开导出的 HTML 文件，通常不需要再保留旁边的 `images/` 文件夹。

如果希望访问文件夹地址时直接打开第一页，可以把该帖子的 `1.html` 复制或改名为 `index.html`。

在 GitHub 仓库页面里点击 `.html` 文件时，GitHub 默认显示源码，不会像网页一样渲染。要在线查看效果，需要使用 GitHub Pages 或其他静态网站服务。未导出的原始 HTML 需要保持 HTML 和 `images/` 文件夹的相对位置不变；单文件导出的 HTML 已经把图片嵌入文件本身，更适合单独发布。

在本地查看时，可以优先用 VS Code 的 Live Server 打开保存目录；也可以直接打开具体的 `1.html`。

## 常见问题

### 为什么有些图片显示“下载失败”？

豆瓣图片可能存在防盗链、临时失效、权限限制或不同图片域名切换。脚本会自动尝试多个 `img*.doubanio.com` 域名和常见图片路径；全部失败时会保留原图链接，方便之后手动打开或补救。

### 可以把 HTML 上线成静态网站吗？

可以。分两种情况
1、未运行export_single_html.py，此状态下爬出的帖子需保持每个帖子目录中的 HTML 和 `images/` 文件夹一起上传。
2、运行export_single_html.py，将导出的单个html文件上传。
## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
