# log-02：第二版官方 Markdown 导出

日期：2026-09-21

## 目标

第一版由页面 HTML 直接转换 Markdown。第二版改为使用语雀官方导出流程：

1. 点击文档右侧 `Rightboard` 图标。
2. 在侧栏菜单中点击 `导出...`。
3. 选择 `fileTypeSelectorItem-markdown`。
4. 点击右侧栏底部的主按钮 `导出`。
5. 用 Playwright `expect_download()` 捕获下载，并保存为每篇目录下的 `说明.md`。

## 选择器

- 右侧图标：`svg[data-name="Rightboard"]`
- 导出菜单：文本 `导出...`
- Markdown 类型：`[data-testid="fileTypeSelectorItem-markdown"]`
- 最终导出按钮：`button.ant-btn-primary` 且文本为 `导出`

## 实测结果

在以下三篇文档中完整执行官方导出：

- `2020-04-23 张宇杰 Empirical Study on Data Shift`：成功，导出 2086 bytes。
- `2026-08-05 石广超 [Summer Seminar] AI 4 Math & Neuro-Symbolic AI`：成功，导出 162 bytes。
- `2026-08-04 巫昊聪 [Summer Seminar] On Policy Distillation`：成功，导出 155 bytes。

三篇文档均能找到唯一的右侧图标、导出菜单、Markdown 选项和最终导出按钮；下载文件均为 `.md`。其中两篇正文较短，官方导出仅包含附件链接，这是语雀导出的实际内容，不是本地转换丢失。

## 主流程集成验证

使用 V2 主程序处理目录前 2 篇：

- `2026-08-05 石广超 [Summer Seminar] AI 4 Math & Neuro-Symbolic AI`：附件 4007866 bytes，官方 Markdown 162 bytes。
- `2026-08-04 巫昊聪 [Summer Seminar] On Policy Distillation`：附件 10251277 bytes，官方 Markdown 155 bytes。

结果：文档成功 2，失败 0；官方 Markdown 2；附件新下载 2；退出码 0。输出中的 `说明.md` 均为官方导出的 Markdown，并包含附件原始链接。

## V2 行为

- Markdown 来源改为官方导出，不再使用 BeautifulSoup/markdownify 转换页面 HTML。
- 附件下载逻辑保持第一版行为。
- 每篇文档统一保存 `说明.md`，下载临时文件使用 `说明.md.part`，成功后原子替换。
- 官方导出失败时该篇记录到 `failed.txt`，继续处理后续文档。
