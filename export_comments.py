"""从语雀文档页面导出评论，不重新下载正文和附件。"""
import argparse
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from yuque import library_url


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = Path(r"E:\FML")
COMMENT_CONTAINER = "#comment-floor-container"


@dataclass(frozen=True)
class Comment:
    comment_id: str
    author: str
    time: str
    content: str
    parent_id: str | None


def normalize_comment_text(text):
    text = text.replace("\u200b", "").replace("\r", "").strip()
    lines = [line.rstrip() for line in text.splitlines()]
    result = []
    previous_empty = False
    for line in lines:
        empty = not line.strip()
        if empty and previous_empty:
            continue
        result.append(line)
        previous_empty = empty
    return "\n".join(result).strip()


def document_directories(output_root):
    directories = []
    for path in output_root.iterdir():
        if not path.is_dir() or "__" not in path.name:
            continue
        title, separator, slug = path.name.rpartition("__")
        if separator and title and slug:
            directories.append((title, slug, path))
    return sorted(directories, key=lambda item: item[2].name)


def extract_comments(page):
    comments = page.evaluate(
        """() => {
          const container = document.querySelector('#comment-floor-container');
          if (!container) return [];
          return [...container.querySelectorAll('[id^="comment-"]')]
            .filter((element) => element.id !== 'comment-floor-container')
            .map((element) => ({
              id: element.id,
              author: element.querySelector('[class^="commentFloorListItem-module_name_"]')?.innerText.trim() || '',
              time: element.querySelector('[class^="commentFloorListItem-module_time_"]')?.innerText.trim() || '',
              content: element.querySelector('[class^="commentFloorListItem-module_content_"]')?.innerText.trim() || '',
              parentId: element.parentElement?.closest('[id^="comment-"]')?.id || null,
            }));
        }"""
    )
    return [
        Comment(
            comment_id=item["id"],
            author=item["author"],
            time=item["time"],
            content=normalize_comment_text(item["content"]),
            parent_id=item["parentId"],
        )
        for item in comments
    ]


def scroll_comments(page):
    for _ in range(100):
        before = {comment.comment_id for comment in extract_comments(page)}
        page.evaluate(
            """() => {
              const container = document.querySelector('#comment-floor-container');
              if (!container) return;
              [...container.querySelectorAll('*'), container]
                .filter((element) => element.scrollHeight > element.clientHeight + 2)
                .forEach((element) => {
                  element.scrollTop = Math.min(
                    element.scrollTop + Math.ceil(element.clientHeight * 0.8),
                    element.scrollHeight,
                  );
                });
            }"""
        )
        page.wait_for_timeout(300)
        after = {comment.comment_id for comment in extract_comments(page)}
        if after == before:
            stable_count = 0
            for _ in range(3):
                page.wait_for_timeout(300)
                current = {comment.comment_id for comment in extract_comments(page)}
                if current != after:
                    break
                stable_count += 1
            if stable_count == 3:
                return


def comments_to_markdown(comments):
    if not comments:
        return "# 评论\n\n无评论\n"
    lines = ["# 评论", ""]
    by_id = {comment.comment_id: comment for comment in comments}
    root_number = 0
    reply_number = 0
    for comment in comments:
        is_root = comment.parent_id not in by_id
        if is_root:
            root_number += 1
            reply_number = 0
            number = str(root_number)
            heading = "##"
        else:
            reply_number += 1
            number = f"{root_number}.{reply_number}"
            heading = "###"
        metadata = " · ".join(part for part in (comment.author, comment.time) if part)
        lines.append(f"{heading} {number}. {metadata}")
        lines.append("")
        lines.append(comment.content or "（空评论）")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_one(page, base_url, slug, folder, overwrite=False):
    target = folder / "评论.md"
    if target.is_file() and not overwrite:
        logging.info("跳过已有评论：%s", folder.name)
        return False

    url = f"{base_url}/{slug}"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.locator(COMMENT_CONTAINER).wait_for(timeout=30000)
    except PlaywrightTimeout:
        raise RuntimeError("页面没有出现评论区")
    page.wait_for_timeout(1000)
    scroll_comments(page)
    comments = extract_comments(page)
    markdown = comments_to_markdown(comments)

    temporary = folder / "评论.md.part"
    temporary.write_text(markdown, encoding="utf-8")
    temporary.replace(target)
    logging.info("已保存评论：%s（%d 条，%d bytes）", folder.name, len(comments), target.stat().st_size)
    return True


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT, help="已下载文档的输出根目录")
    parser.add_argument("--url", default="https://foundationml.yuque.com/foundationml/seminar", help="知识库 URL")
    parser.add_argument("--connect", help="连接本机 9223 的专属 Chrome 调试地址")
    parser.add_argument("--only", help="只处理目录名包含该文本的文档")
    parser.add_argument("--limit", type=int, help="最多处理 N 个目录")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的评论.md")
    args = parser.parse_args()
    if args.connect and args.connect not in ("http://127.0.0.1:9223", "http://localhost:9223"):
        parser.error("--connect 仅接受本机 9223 端口")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit 必须大于 0")
    return args


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / "export_comments.log", encoding="utf-8")],
    )
    if not args.output.is_dir():
        raise RuntimeError(f"输出目录不存在：{args.output}")

    base_url = library_url(args.url).rstrip("/")
    directories = document_directories(args.output)
    if args.only:
        directories = [item for item in directories if args.only in item[2].name]
    if args.limit:
        directories = directories[: args.limit]
    if not directories:
        logging.info("没有找到可处理的文档目录：%s", args.output)
        return 0

    with sync_playwright() as playwright:
        if args.connect:
            browser = playwright.chromium.connect_over_cdp(args.connect)
            context = browser.contexts[0]
        else:
            context = playwright.chromium.launch_persistent_context(
                str(ROOT / ".browser-profile"),
                channel="chrome",
                headless=False,
                viewport={"width": 1360, "height": 900},
            )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            succeeded = failed = skipped = 0
            for index, (title, slug, folder) in enumerate(directories, 1):
                logging.info("处理评论 [%d/%d] %s", index, len(directories), title)
                try:
                    changed = export_one(
                        page,
                        base_url,
                        slug,
                        folder,
                        overwrite=args.overwrite,
                    )
                    if changed:
                        succeeded += 1
                    else:
                        skipped += 1
                except Exception as exc:
                    failed += 1
                    logging.error("评论导出失败，继续下一篇：%s：%s", folder.name, exc)
                    with (args.output / "comments_failed.txt").open("a", encoding="utf-8") as stream:
                        stream.write(f'{datetime.now().isoformat(timespec="seconds")}\t{folder.name}\t{base_url}/{slug}\t{str(exc).replace(chr(10), " ")}\n')
            logging.info(
                "结束：评论新保存 %d，已有跳过 %d，失败 %d；输出 %s",
                succeeded,
                skipped,
                failed,
                args.output,
            )
            return 1 if failed else 0
        finally:
            if args.connect:
                browser.close()
            else:
                context.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n用户中止，已完成的评论文件保留。")
        raise SystemExit(130)
