# 语雀组会资料下载器 V2

Python + Playwright，同步串行下载。读取真实知识库目录；Markdown 使用语雀官方“导出 Markdown”流程生成；附件从官方导出的 Markdown 中解析语雀链接，并用已登录浏览器直接访问链接捕获下载。不调用语雀私有 API，不解析 CDN 下载链接。

## 安装

需要 Windows、Python 3.10+ 和 Google Chrome。当前项目已建立 `.venv`，可以直接使用下方运行命令。新环境安装：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

程序使用已安装的 Chrome（`channel="chrome"`），无需另外安装 Playwright Chromium。如果 `python` 指向缺少 pip 的 MSYS Python，请改用标准 Windows Python 的完整路径创建虚拟环境。

## 登录与运行

默认使用 `launch_persistent_context()`，登录配置保存在当前项目 `.browser-profile` 中。首次运行按终端提示手动登录，能看到知识库目录后在终端按 Enter；以后复用 session。登录失效可以加 `--login`。请勿同时运行两个程序占用同一个配置目录。

本机首次在 Playwright 启动的 Chrome 中手动拖滑块未通过；已验证的处理方式是先用普通 Chrome 打开**项目专属配置目录**手动登录，再关闭该窗口，运行下载器。辅助命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\login_chrome.ps1
```

此脚本只是普通启动 Chrome，不读取日常浏览器 Cookie、不修改指纹、不自动操作滑块。默认不开放调试端口。登录成功后必须关闭专属窗口释放配置目录。下载器再以 persistent context 复用登录；本机已验证登录和目录读取可用。

### 本机已知问题与可用的兼容运行方式

本机 Chrome 153 使用 `launch_persistent_context()` 能复用登录、读取目录，但下载时会发生原生崩溃（`0xC0000005`），本地纯文本下载也复现。不要将这一模式的下载视为已通过验证。Playwright 上游有[类似持久化配置下载崩溃报告](https://github.com/microsoft/playwright/issues/42506)，但其环境不同，不能据此认定根因相同。

本机请使用以下**兼容命令**。依然复用同一个磁盘配置目录，文件下载仍是 Playwright 的 `expect_download()` 捕获浏览器下载；区别仅在于 Chrome 正常启动后通过 CDP 连接，而非 `launch_persistent_context()` 启动：

```powershell
# 没有项目专属 Chrome 窗口时先启动一次，保持窗口打开
powershell -ExecutionPolicy Bypass -File .\login_chrome.ps1 -Connect

.\.venv\Scripts\python.exe main.py "https://foundationml.yuque.com/foundationml/seminar"  --connect http://127.0.0.1:9223
```

兼容模式仅监听本机 9223，不连接日常 Chrome。程序完成后会断开连接，窗口可继续复用；不用时正常关闭专属 Chrome。不要同时开启默认模式和兼容模式占用同一个目录。

其他环境的默认 persistent context 入口如下；本机按上面的兼容命令执行。测试目录前 10 篇（按照语雀目录顺序，不重新按日期排序）：

```powershell
.\.venv\Scripts\python.exe main.py "https://foundationml.yuque.com/foundationml/seminar" --limit 10
```

也可以不传 URL，程序会在终端询问。接受知识库 URL 或库内文档 URL，始终处理所属知识库目录中的文档，不跟随正文中的外部文档链接。

### 从已导出 Markdown 下载附件

`--markdown` 模式读取单个已导出的 Markdown 文件，提取其中所有语雀附件链接，并把附件下载到该 Markdown 所在目录。链接先解析标准 `[文件名](URL)`，再做全文 URL 兜底扫描；按 URL 去重，优先使用 Markdown 中的文件名。本地同名文件不会被覆盖，会自动使用 `文件名_2.ext`、`文件名_3.ext` 等后缀。

本机推荐配合项目专属 Chrome 的兼容模式使用：

```powershell
.\.venv\Scripts\python.exe main.py --markdown "E:\FML\某文档__slug\说明.md" --connect http://127.0.0.1:9223
```

该模式不使用 `requests`，而是让已登录浏览器直接访问附件 URL，并用 Playwright `expect_download()` 捕获下载；原 Markdown 文件不会被修改。单个附件失败会记录错误并继续处理后续附件，最后输出发现、成功和失败数量。

### 单独导出评论

如果正文和附件已经下载完成，可以单独运行 `export_comments.py`。它会遍历输出根目录下形如 `<标题>__<slug>` 的文档目录，逐篇打开原文档读取页面评论区，并在同目录保存 `评论.md`；不会重新下载正文和附件。已有 `评论.md` 默认跳过，加 `--overwrite` 才覆盖：

```powershell
.\.venv\Scripts\python.exe export_comments.py --connect http://127.0.0.1:9223
```

常用参数：`--only "2023-09-06 郑钦城"` 只处理目录名匹配的文档，`--limit 10` 控制数量，`--overwrite` 覆盖已生成文件。日志写入项目 `export_comments.log`，失败记录追加到输出根目录 `comments_failed.txt`。

```powershell
# 只检查全部文档标题与 URL，不下载
.\.venv\Scripts\python.exe main.py "https://foundationml.yuque.com/foundationml/seminar" --list-only

# 全量运行：确认前十篇测试结果后，自行移除 --limit
.\.venv\Scripts\python.exe main.py "https://foundationml.yuque.com/foundationml/seminar"

# 自定义输出位置
.\.venv\Scripts\python.exe main.py "https://foundationml.yuque.com/foundationml/seminar" --limit 10 --output "E:\FML"
```

## 输出与重复运行

默认输出 `E:\FML\<文档标题>__<文档标识>\`，每篇包含全部已识别附件及 `说明.md`。Windows 非法字符替换为下划线，标题加文档标识避免同名文档混淆。单页同名附件增加 `__2` 等后缀。

- 已存在的附件按文件名跳过，不校验远端更新；需要更新时先手动移走旧文件。
- 下载先写 `.part`，成功后才改为最终文件名，失败时清理本次临时文件。
- `说明.md` 每次覆盖，内容来自语雀官方 Markdown 导出，不再由页面 HTML 转换。
- 官方导出文件名会记录到日志；本地统一保存为 `说明.md`，便于批量归档。
- 某篇或某附件失败会记录到输出根目录 `failed.txt`，继续后续文档。该文件追加历史失败，重跑成功不会删除旧记录，以当前终端汇总为准。
- 清晰日志同时写终端与项目的 `download.log`；正常完成退出码 0，有失败退出码 1，手动中止为 130。

## 文件与实现范围

- `main.py`：参数、持久化浏览器、串行遍历、错误记录。
- `export_comments.py`：单独遍历已下载目录并导出每篇文档评论。
- `yuque.py`：所有语雀 selector、虚拟目录滚动、Markdown 附件链接提取、直接下载和官方 Markdown 导出。
- `requirements.txt`：测试环境的依赖版本。
- `login_chrome.ps1`：本机首次手动登录的辅助入口。
- `log-01.md`：第一版验收记录和已知边界。
- `log-02.md`：第二版官方 Markdown 导出验证记录。

目录 selector 来自 2026-09-22 对实际页面 DOM 的检查：`#navBox .lark-virtual-tree` 是虚拟目录，程序展开并逐屏滚动到底部；正文定位 `article#content .ne-viewer-body`。该站 DOM 变化时只需优先检查 `yuque.py`。

附件下载不再依赖正文里的附件卡片和下载按钮，因此不受旧版卡片 DOM 差异影响。若官方 Markdown 中没有附件链接、链接失效或无权限，该附件会失败并写入 `failed.txt`。Markdown 的排版 fidelity 由语雀官方导出决定。

没有数据库、state.json、并发、API Token、GUI、Web UI 或 LLM 功能。`.browser-profile` 包含登录信息，已加入 `.gitignore`，不要分享该目录。

## 本次验收（2026-09-21）

V1 曾全量采集 199 篇目录，并由页面 HTML 生成 199 份 Markdown；101 篇文档无错误完成，98 篇因附件失败标记失败。V2 已改用官方导出，并在 3 篇文档上验证导出链路；另用主程序处理目录前 2 篇，2 篇官方 Markdown、2 个附件均成功，退出码 0。

详细记录见 `log-01.md` 和 `log-02.md`。`failed.txt` 保留了开发期间原生浏览器崩溃和已修复卡片误报的历史记录；它不是当前未完成清单。

文件名处理和知识库 URL 校验的回归检查：

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```
