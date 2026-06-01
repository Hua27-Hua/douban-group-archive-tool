# 豆瓣小组帖子本地存档工具

这是一个把豆瓣小组帖子保存到本地电脑的工具。它会打开浏览器让你登录豆瓣，然后按你的选择保存帖子内容和图片。保存后可以离线查看，也可以再导出成一个单独的 HTML 文件，方便长期整理。

## 可以完成什么

- 保存整个豆瓣小组里的帖子。
- 只保存你指定的几个帖子。
- 先提取一个小组的帖子链接，再按关键词挑出想保存的帖子。
- 单独保存小组精华帖。
- 一次保存很多个帖子链接。
- 把帖子里的图片一起保存到本地。
- 本地打开帖子时，可以点击图片放大。
- 爬取时会尽量自动展开被折叠的评论。
- 可以选择是否保留帖子问答里的 `正确答案：`。
- 爬完后可以导出成单文件 HTML，双击就能打开，更适合长期保存。

## 最快流程

第一次使用前，先安装依赖。打开 PyCharm 下方的 Terminal/终端，粘贴这一行后回车：

```bash
pip install -r requirements.txt
```

推荐用 PyCharm 打开项目。不会命令行也没关系，后面大部分操作都可以直接打开对应的 `.py` 文件，然后点右上角绿色运行按钮。

如果你习惯用终端，运行脚本时要写成 `python 文件路径`，例如：

```bash
python douban_group_downloader_captcha/download_posts.py
```

### 保存整个小组

1. 打开 `douban_group_downloader_qrcode/config.json`。
2. 填入小组 ID 和小组名。
3. 打开 `douban_group_downloader_qrcode/download_group.py`。
4. 点 PyCharm 右上角绿色运行按钮，或者在终端输入：

```bash
python douban_group_downloader_qrcode/download_group.py
```

5. 浏览器打开后登录豆瓣，回到 PyCharm 运行窗口按回车继续。
6. 按提示选择是否保留问答正确答案。
7. 等待保存完成。
8. 帖子爬取完成后，推荐用 `export_single_html.py` 导出成单文件 HTML。

### 只保存指定帖子

1. 打开 `douban_group_downloader_captcha/config.json`。
2. 把想保存的帖子链接填进 `single_posts`。
3. 打开 `douban_group_downloader_captcha/download_posts.py`。
4. 点 PyCharm 右上角绿色运行按钮，或者在终端输入：

```bash
python douban_group_downloader_captcha/download_posts.py
```

5. 登录豆瓣后回到运行窗口按回车继续。
6. 按提示选择是否保留问答正确答案。
7. 等待保存完成。
8. 帖子爬取完成后，推荐用 `export_single_html.py` 导出成单文件 HTML。

### 先提取链接，再筛选想保存的帖子

推荐流程：

1. 用 `extract_urls.py` 提取小组帖子链接。
2. 如果链接太多，用 `filter_urls.py` 按关键词筛选，也可以输入不想要的关键词，把不需要的帖子排除掉。
3. 打开筛出来的 JSON 文件，把里面的整段内容复制到 `douban_group_downloader_captcha/config.json`。
4. 用 `download_posts.py` 批量保存筛选后的帖子。
5. 帖子爬取完成后，推荐用 `export_single_html.py` 导出成单文件 HTML。

这个流程适合小组帖子很多、但你只想保存其中一部分的情况。

## 详细步骤

### 1. 准备环境

需要安装：

- Python 3
- Chrome 浏览器
- PyCharm，推荐但不是必须

安装依赖：

```bash
pip install -r requirements.txt
```

如果你不知道在哪里输入这行命令，可以在 PyCharm 下方打开 Terminal/终端，粘贴后回车。

### 2. 保存整个小组

打开：

```text
douban_group_downloader_qrcode/config.json
```

把示例内容改成你要保存的小组：

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

`groupid` 是小组主页 URL 里的数字。例如：

```text
https://www.douban.com/group/123456/
```

这里要填的就是：

```text
123456
```

填好后，运行：

```text
douban_group_downloader_qrcode/download_group.py
```

可以直接点 PyCharm 右上角绿色运行按钮，也可以在项目根目录的终端里输入：

```bash
python douban_group_downloader_qrcode/download_group.py
```

运行时会打开浏览器。请在这个浏览器里登录豆瓣，登录完成后回到 PyCharm 下方运行窗口按回车。

接着程序会问：

```text
1. 不保留，自动删除正确答案（推荐）
2. 保留正确答案
```

直接回车默认选择 `1`。如果你想保留问答正确答案，输入 `2` 后回车。

### 3. 只保存指定帖子

打开：

```text
douban_group_downloader_captcha/config.json
```

把想保存的帖子放进去：

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

`url` 是帖子链接，`title` 是保存到电脑上的文件夹名字。可以一次放很多个帖子。

填好后，运行：

```text
douban_group_downloader_captcha/download_posts.py
```

可以直接点 PyCharm 右上角绿色运行按钮，也可以在项目根目录的终端里输入：

```bash
python douban_group_downloader_captcha/download_posts.py
```

同样会打开浏览器，登录豆瓣后回到运行窗口按回车继续。

### 4. 先提取小组帖子链接

如果一个小组帖子很多，你可以先把帖子链接全部提取出来，再慢慢筛选。

先确认这个文件里已经填好小组信息：

```text
douban_group_downloader_qrcode/config.json
```

然后运行：

```text
douban_group_downloader_qrcode/extract_urls.py
```

可以直接点 PyCharm 右上角绿色运行按钮，也可以在项目根目录的终端里输入：

```bash
python douban_group_downloader_qrcode/extract_urls.py
```

运行后会让你选择提取范围：

```text
1. 最新讨论 / 全部列表
2. 精华帖
3. 热门讨论
4. 自定义列表页 URL
```

选择后会生成 JSON 文件。普通讨论列表会生成类似：

```text
小组名_小组ID_urls.json
小组名_小组ID_urls_single_posts_config.json
```

如果提取的是精华帖，文件名里会带 `_elite`。

### 5. 从链接清单里筛选帖子

如果提取出来的帖子太多，可以运行：

```text
douban_group_downloader_qrcode/filter_urls.py
```

可以直接点 PyCharm 右上角绿色运行按钮，也可以在项目根目录的终端里输入：

```bash
python douban_group_downloader_qrcode/filter_urls.py
```

它会让你选择一个 URL 清单，然后输入想保留的关键词。比如你输入：

```text
闲聊楼 资源
```

脚本会筛出标题里包含这些关键词的帖子。

如果有些帖子你不想保存，也可以在“想排除哪些关键词？”那里输入不想要的词。比如输入：

```text
求助 广告 拼车
```

这样标题里包含这些词的帖子就不会进入最后的保存清单。

筛选完成后，脚本会生成一个新的 JSON 配置文件。

打开这个新 JSON 文件，你会看到类似这样的内容：

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
    }
  ]
}
```

最简单的做法是：全选这个文件里的全部内容，复制，然后打开：

```text
douban_group_downloader_captcha/config.json
```

把 `config.json` 原来的内容全部替换掉，再保存。

也就是说，复制时不要只复制某一条 URL，最好复制从最外层 `{` 到最后一个 `}` 的整段 JSON。这样格式最不容易出错。

保存后运行：

```text
douban_group_downloader_captcha/download_posts.py
```

这样就可以只保存筛选后的帖子。

### 6. 导出单文件 HTML

爬完后，推荐再导出成单文件 HTML。这样每个帖子会变成一个独立 HTML 文件，双击就能打开，也更适合长期整理。

导出整个小组：

```bash
python export_single_html.py douban_group_downloader_qrcode/小组名_小组ID
```

导出指定帖子目录：

```bash
python export_single_html.py douban_group_downloader_captcha/single_posts
```

导出结果会放在 `_single_html_exports` 文件夹里。

## 你会用到的文件

```text
douban_group_downloader_qrcode/download_group.py
保存整个小组，或保存小组精华帖。

douban_group_downloader_qrcode/extract_urls.py
提取小组帖子链接。

douban_group_downloader_qrcode/filter_urls.py
从帖子链接清单里按关键词筛选想保存的帖子。

douban_group_downloader_captcha/download_posts.py
按指定帖子链接批量保存帖子。

export_single_html.py
把已保存的帖子导出成单文件 HTML。
```

## 查看保存结果

如果没有导出单文件 HTML，打开帖子文件夹里的：

```text
1.html
```

如果已经导出单文件 HTML，打开 `_single_html_exports` 里的 HTML 文件即可。

本地查看时，可以直接双击 HTML，也可以用 VS Code 的 Live Server 打开保存目录。

## 常见问题

### 运行时要不要关闭浏览器？

不要。脚本打开的浏览器要一直留着。登录完成后，回到 PyCharm 或终端窗口按回车继续。

### 正确答案要怎么选？

运行 `download_group.py` 或 `download_posts.py` 时会自动询问。

直接回车：不保留正确答案。

输入 `2` 后回车：保留正确答案。

### 图片没有显示怎么办？

少数图片可能因为豆瓣权限、网络或图片地址失效而下载失败。可以重新运行一次，或者爬完后用 `export_single_html.py` 导出单文件 HTML 再查看。

### GitHub 上点 HTML 为什么不是网页？

GitHub 默认把 HTML 当源码显示，不会直接当网页打开。想在线查看，需要用 GitHub Pages 或其他静态网站服务。本地查看的话，直接双击导出的单文件 HTML 最方便。

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
