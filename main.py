"""语雀组会资料下载器 V2：同步、串行、真实浏览器下载与官方 Markdown 导出。"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from yuque import TREE, Document, get_document_list, library_url, load_document, safe_name, download_attachments, export_markdown

ROOT = Path(__file__).resolve().parent


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', nargs='?', help='组会报告知识库 URL 或库内文档 URL')
    parser.add_argument('--output', type=Path, default=Path(r'E:\FML'))
    parser.add_argument('--limit', type=int, help='只处理目录前 N 篇；不指定则全量')
    parser.add_argument('--list-only', action='store_true', help='仅获取并打印完整目录')
    parser.add_argument('--login', action='store_true', help='手动登录或修复登录后按 Enter 继续')
    parser.add_argument('--connect', help='兼容模式：连接项目专属 Chrome 的本机调试地址')
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error('--limit 必须大于 0')
    url = args.url or input('请输入组会报告知识库 URL：').strip()
    library_url(url)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S', handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / 'download.log', encoding='utf-8')])
    with sync_playwright() as p:
        if args.connect:
            if args.connect not in ('http://127.0.0.1:9223', 'http://localhost:9223'):
                raise ValueError('--connect 仅接受本机 9223 端口')
            browser = p.chromium.connect_over_cdp(args.connect)
            context = browser.contexts[0]
        else:
            context = p.chromium.launch_persistent_context(str(ROOT / '.browser-profile'), channel='chrome', headless=False, accept_downloads=True, viewport={'width':1360,'height':900})
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            if args.login:
                input('请在浏览器完成手动登录，能看到知识库目录后按 Enter：')
            try:
                page.locator(TREE).wait_for(state='visible', timeout=15000)
            except PlaywrightTimeout:
                input('未看到目录。请手动登录/进入组会报告知识库，完成后按 Enter：')
                page.locator(TREE).wait_for(state='visible', timeout=30000)
            logging.info('知识库目录可访问，使用项目持久化浏览器配置')
            documents = get_document_list(page, url)
            if args.list_only:
                for index, doc in enumerate(documents, 1):
                    logging.info('目录 %03d | %s | %s', index, ' '.join(doc.title.split()), doc.url)
                return 0
            selected = documents[:args.limit] if args.limit else documents
            args.output.mkdir(parents=True, exist_ok=True)
            good = failed = downloaded = skipped = exported = 0
            for index, document in enumerate(selected, 1):
                logging.info('处理 [%d/%d] %s', index, len(selected), document.title)
                try:
                    folder = args.output / (safe_name(document.title) + '__' + document.url.rsplit('/', 1)[-1])
                    folder.mkdir(parents=True, exist_ok=True)
                    body = load_document(page, document)
                    new, old, errors = download_attachments(page, body, folder)
                    downloaded += new
                    skipped += old
                    export_markdown(page, document, folder)
                    exported += 1
                    if errors:
                        raise RuntimeError('; '.join(errors))
                    good += 1
                except Exception as exc:
                    failed += 1
                    logging.error('本篇失败，继续下一篇：%s', exc)
                    with (args.output / 'failed.txt').open('a', encoding='utf-8') as stream:
                        stream.write(f'{datetime.now().isoformat(timespec="seconds")}\t{document.title}\t{document.url}\t{str(exc).replace(chr(10), " ")}\n')
            logging.info('结束：文档成功 %d，失败 %d；官方 Markdown %d；附件新下载 %d，已有跳过 %d；输出 %s', good, failed, exported, downloaded, skipped, args.output.resolve())
            return 1 if failed else 0
        finally:
            if args.connect:
                browser.close()  # CDP 连接断开，保留用户手动启动的窗口。
            else:
                context.close()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\n用户中止，已完成的文件保留。')
        raise SystemExit(130)
    except Exception as exc:
        logging.error('无法继续：%s', exc)
        raise SystemExit(1)
