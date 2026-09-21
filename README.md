# 语雀组会资料下载器 V1

Python + Playwright，同步串行下载。读取真实知识库目录，点击附件的真实下载按钮，通过 `expect_download()` 保存文件；不调用语雀私有 API，不解析 CDN 下载链接。

V1 的边界：能访问语雀、遍历目录、保存 Markdown，并下载带真实下载按钮的附件；部分旧 PDF 卡片在页面上没有下载按钮，V1 会记录失败并继续处理后续文档。

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

本机请使用以下**兼容命令**。依然复用同一个磁盘配置目录，文件下载仍是 Playwright 的 `expect_download()` 加真实按钮点击；区别仅在于 Chrome 正常启动后通过 CDP 连接，而非 `launch_persistent_context()` 启动：

```powershell
# 没有项目专属 Chrome 窗口时先启动一次，保持窗口打开
powershell -ExecutionPolicy Bypass -File .\login_chrome.ps1 -Connect

.\.venv\Scripts\python.exe main.py "https://foundationml.yuque.com/foundationml/seminar" --limit 10 --connect http://127.0.0.1:9223
```

兼容模式仅监听本机 9223，不连接日常 Chrome。程序完成后会断开连接，窗口可继续复用；不用时正常关闭专属 Chrome。不要同时开启默认模式和兼容模式占用同一个目录。

其他环境的默认 persistent context 入口如下；本机按上面的兼容命令执行。测试目录前 10 篇（按照语雀目录顺序，不重新按日期排序）：

```powershell
.\.venv\Scripts\python.exe main.py "https://foundationml.yuque.com/foundationml/seminar" --limit 10
```

也可以不传 URL，程序会在终端询问。接受知识库 URL 或库内文档 URL，始终处理所属知识库目录中的文档，不跟随正文中的外部文档链接。

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
- `说明.md` 每次覆盖，包含标题、原文 URL 和清理后的正文。附件卡片和预览 iframe 删除；正文图片保留远程链接，不另外下载图片。
- 没有附件之外的正文时明确写“本页除附件外无正文”。PDF 内容不会被抽取成正文。
- 某篇或某附件失败会记录到输出根目录 `failed.txt`，继续后续文档。该文件追加历史失败，重跑成功不会删除旧记录，以当前终端汇总为准。
- 清晰日志同时写终端与项目的 `download.log`；正常完成退出码 0，有失败退出码 1，手动中止为 130。

## 文件与实现范围

- `main.py`：参数、持久化浏览器、串行遍历、错误记录。
- `yuque.py`：所有语雀 selector、虚拟目录滚动、附件下载、BeautifulSoup 清理和 markdownify 转换。
- `requirements.txt`：测试环境的依赖版本。
- `login_chrome.ps1`：本机首次手动登录的辅助入口。
- `log-01.md`：第一版验收记录和已知边界。

目录 selector 来自 2026-09-21 对实际页面 DOM 的检查：`#navBox .lark-virtual-tree` 是虚拟目录，程序展开并逐屏滚动到底部；正文定位 `article#content .ne-viewer-body`；文件卡片通过 `ne-card-local-doc-*` 的 `data-testid` 定位。该站 DOM 变化时只需优先检查 `yuque.py`。

已适配实际观察到的 `localdoc` 附件组件。发现其他未适配卡片时报告失败，避免静默漏下；不保证未测试的旧版附件组件通用。无权限文档无法下载。复杂正文排版按 markdownify 能力转换，不承诺与网页像素一致。

已知限制：部分旧 PDF 附件卡片没有 `ne-card-local-doc-btn-download` 下载按钮，导致该附件无法通过真实按钮触发下载。此类文档仍会保存 `说明.md`，并写入 `failed.txt`。

没有数据库、state.json、并发、API Token、GUI、Web UI 或 LLM 功能。`.browser-profile` 包含登录信息，已加入 `.gitignore`，不要分享该目录。

## 本次验收（2026-09-21）

实际知识库目录采集 199 篇。前 10 篇冒烟验收全部成功，保存 11 个附件（10 PDF + 1 PPTX）和 10 份说明。随后全量运行：101 篇文档无错误完成，98 篇因至少一个附件失败而标记失败；199 份 `说明.md` 均已保存，95 个附件新下载，11 个附件因已存在跳过。失败附件主要为没有下载按钮的旧 PDF 卡片。

详细记录见 `log-01.md`。`failed.txt` 保留了开发期间原生浏览器崩溃和已修复卡片误报的历史记录；它不是当前未完成清单。

正文清理、相对链接、图片链接、段落保留及覆盖写入的回归检查：

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```
