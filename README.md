# 豆瓣小组帖子本地存档工具

这是一个用于本地保存豆瓣小组帖子的 Python 工具。脚本会通过浏览器登录豆瓣，保存帖子 HTML，下载帖子中的图片，并把页面里的图片地址改成本地路径，方便离线查看或之后放到静态网页服务中查看。

请只保存自己有权限查看的内容。

## 功能

- 支持按小组批量保存帖子。
- 支持按指定帖子 URL 批量保存帖子。
- 自动下载帖子图片到 `images/` 目录。
- HTML 中的图片会替换成本地路径。
- 本地 HTML 支持点击图片放大查看。
- 下载失败的图片会记录到 `failed_images.jsonl`，方便之后排查或手动补救。
- 如果普通图片请求失败，爬虫会再尝试用已登录的浏览器兜底读取图片，适合需要账号权限才能查看原图的私密小组。

## 文件说明

```text
douban_group_downloader-main/
├─ douban_group_downloader_qrcode/
│  ├─ download_group.py                 # 按小组批量保存帖子
│  ├─ extract_urls.py                   # 从小组列表提取帖子 URL，并生成指定帖子配置
│  └─ config.json                       # 小组批量保存配置 运行前必配置
├─ douban_group_downloader_captcha/
│  ├─ download_posts.py                 # 按指定帖子 URL 保存帖子
│  └─ config.json                       # 指定帖子保存配置 
├─ export_single_html.py                # 把已下载帖子导出为单文件 HTML，推荐爬完帖子追求完美保留个人隐私者必运行
├─ .gitignore
├─ README.md
└─ requirements.txt
```

### `download_group.py`

按小组批量保存帖子。它会读取 `douban_group_downloader_qrcode/config.json` 中的 `grouplist`，进入小组讨论列表，逐页获取帖子链接并保存内容。


### `download_posts.py`

按指定帖子 URL 保存。它会读取 `douban_group_downloader_captcha/config.json` 中的 `single_posts`，可以一次放入多个帖子 URL，适合快速、精准地选中并保存你需要的帖子。


### `extract_urls.py`

辅助指定帖子 URL 使用，和 `download_group.py` 放在同一个目录里，共用 `douban_group_downloader_qrcode/config.json` 里的小组配置。它会从小组讨论列表提取帖子 URL，并生成这些文件：

```text
小组名_小组ID_urls.txt
小组名_小组ID_urls.json
小组名_小组ID_urls.csv
小组名_小组ID_urls_single_posts_config.json
```

其中 `小组名_小组ID_urls_single_posts_config.json` 是给 `download_posts.py` 使用的配置格式。你可以把它的内容复制到 `douban_group_downloader_captcha/config.json`，然后运行指定帖子下载脚本。

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

### 批量保存整个小组

```bash
cd douban_group_downloader_qrcode
python download_group.py
```

程序会打开浏览器。你登录豆瓣后，在命令行按回车继续。

### 保存指定帖子

```bash
cd douban_group_downloader_captcha
python download_posts.py
```

程序会按 `config.json` 中的帖子列表逐个保存。你可以把多个想保存的帖子 URL 都放进 `single_posts`，这样不用保存整个小组，也能快速精准地保存选中的帖子。

### 先提取 URL，再保存指定帖子

如果你想先从某个小组整理出帖子 URL，再决定保存哪些帖子，可以运行：

```bash
cd douban_group_downloader_qrcode
python extract_urls.py
```

`extract_urls.py` 会读取 `douban_group_downloader_qrcode/config.json` 里的 `grouplist`。也就是说，如果你要提取某个小组的帖子 URL，先改这个小组配置，再运行 `extract_urls.py`。

运行完成后，可以打开生成的 `小组名_小组ID_urls_single_posts_config.json`，把里面的内容复制到 `douban_group_downloader_captcha/config.json`，再运行：

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
