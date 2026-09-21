"""语雀 DOM 操作。所有站点 selector 集中于本文件。"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from markdownify import markdownify

LOG = logging.getLogger(__name__)
# 2026-09-21 在 foundationml.yuque.com 的组会报告页面实际检查。
TREE = '#navBox .lark-virtual-tree'
EXPAND_ALL = '#navBox .larkui-icon-catalog-expand'
TREE_LINK = 'a[href]'
ROW = '[data-rbd-draggable-id]'
TITLE = '#article-title'
BODY = 'article#content .ne-viewer-body'
CARD = 'ne-card'
FILE_CARD = '[data-testid="ne-card-local-doc-viewer"]'
FILE_TITLE = '[data-testid="ne-card-local-doc-title"]'
DOWNLOAD = '[data-testid="ne-card-local-doc-btn-download"]'
REMOVE = 'ne-card[data-card-name="localdoc"], ' + FILE_CARD + ', iframe, script, style, button, .ne-inner-overlay-container, [data-testid="ne-card-bookmark-icon"], [ne-filler]'


@dataclass(frozen=True)
class Document:
    title: str
    url: str


def library_url(url):
    parsed = urlsplit(url.strip())
    parts = parsed.path.strip('/').split('/')
    if parsed.scheme != 'https' or not (parsed.hostname == 'yuque.com' or (parsed.hostname or '').endswith('.yuque.com')) or len(parts) < 2:
        raise ValueError('请输入 https://...yuque.com/空间/知识库 URL（也可以输入库内文档 URL）')
    return urlunsplit((parsed.scheme, parsed.netloc, '/' + '/'.join(parts[:2]), '', ''))


def safe_name(text, limit=140):
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', text).strip().rstrip('. ')
    text = text[:limit].rstrip('. ') or 'untitled'
    if text.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        text = '_' + text
    return text


def attachment_name(text):
    suffix = Path(text.strip()).suffix
    return safe_name(Path(text.strip()).stem, 110) + safe_name(suffix, 20) if suffix else safe_name(text, 130)


def get_document_list(page, url):
    """滚动真实虚拟目录，按目录顺序收集本知识库文档，不读取私有 API。"""
    base = library_url(url)
    tree = page.locator(TREE)
    tree.wait_for(state='visible', timeout=30000)
    if page.locator(EXPAND_ALL).count():
        page.locator(EXPAND_ALL).click()
        page.wait_for_timeout(500)
    tree.evaluate('(e) => { e.scrollTop = 0; }')
    docs = {}
    seen_rows = set()
    stable_bottom = 0
    for _ in range(2000):
        page.wait_for_timeout(250)  # 虚拟列表需要一次渲染，不能只读初始 DOM。
        snapshot = tree.evaluate('''(e, s) => ({
          links: [...e.querySelectorAll(s.link)].map(a=>({title:a.textContent.trim(),url:a.href})),
          rows: [...e.querySelectorAll(s.row)].map(r=>r.getAttribute('data-rbd-draggable-id')),
          top:e.scrollTop, height:e.clientHeight, total:e.scrollHeight
        })''', {'link': TREE_LINK, 'row': ROW})
        before = len(seen_rows)
        seen_rows.update(snapshot['rows'])
        for item in snapshot['links']:
            clean = item['url'].split('#')[0].split('?')[0]
            if clean.startswith(base + '/') and len(urlsplit(clean).path.strip('/').split('/')) == 3:
                docs.setdefault(clean, Document(item['title'], clean))
        bottom = snapshot['top'] + snapshot['height'] >= snapshot['total'] - 2
        stable_bottom = stable_bottom + 1 if bottom and len(seen_rows) == before else 0
        if stable_bottom >= 3:
            break
        tree.evaluate('(e) => { e.scrollTop = Math.min(e.scrollTop + e.clientHeight * 0.75, e.scrollHeight); }')
    else:
        raise RuntimeError('目录滚动超过上限，不能确认列表完整，停止下载')
    if not docs:
        raise RuntimeError('目录没有文档，请检查权限和 yuque.py 中的 selector')
    LOG.info('已遍历目录到底部：%d 个目录条目，%d 篇文档', len(seen_rows), len(docs))
    tree.evaluate('(e) => { e.scrollTop = 0; }')
    return list(docs.values())


def load_document(page, document):
    page.goto(document.url, wait_until='domcontentloaded', timeout=60000)
    page.locator(TITLE).wait_for(timeout=30000)
    body = page.locator(BODY)
    body.wait_for(timeout=30000)
    # 等待正文 DOM 连续稳定；不等待会不断请求资源的附件 viewer networkidle。
    previous = None
    stable = 0
    for _ in range(60):
        html = body.inner_html()
        stable = stable + 1 if html == previous else 0
        if stable >= 3:
            return body
        previous = html
        page.wait_for_timeout(300)
    raise RuntimeError('正文 DOM 长时间不稳定，未保存可能不完整的内容')


def save_markdown(html, document, folder):
    soup = BeautifulSoup(html, 'html.parser')
    for element in soup.select(REMOVE):
        element.decompose()
    # Lake 使用 ne-p 等自定义标签；先恢复 HTML 语义，避免段落粘连。
    for element in soup.find_all():
        if element.name.startswith('ne-') and element.name[3:] in {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'pre', 'code'}:
            element.name = element.name[3:]
    for element in soup.select('[href], [src]'):
        for attr in ('href', 'src'):
            if element.has_attr(attr):
                element[attr] = urljoin(document.url, element[attr])
    content = markdownify(str(soup), heading_style='ATX').replace('\u200b', '').strip()
    title = ' '.join(document.title.split())
    text = f'# {title}\n\n来源：{document.url}\n\n'
    text += content + '\n' if content else '（本页除附件外无正文。）\n'
    (folder / '说明.md').write_text(text, encoding='utf-8')
    LOG.info('已保存说明.md（正文 %d 字符）', len(content))


def download_attachments(page, body, folder):
    downloaded = skipped = 0
    errors = []
    # 未识别的附件类型不能默默当作没有附件。
    kinds = body.locator(CARD).evaluate_all('(es)=>es.map(e=>e.getAttribute("data-card-name"))')
    unknown = set(kinds) - {'localdoc', 'bookmarkInline', 'image', 'table', 'codeblock', 'hr', 'math', 'link', None}
    if unknown:
        errors.append('发现尚未适配的卡片类型：' + ', '.join(sorted(unknown)))
    cards = body.locator(FILE_CARD)
    LOG.info('附件：%d 个', cards.count())
    used_names = {'说明.md'}
    for index in range(cards.count()):
        card = cards.nth(index)
        try:
            raw = card.locator(FILE_TITLE).inner_text(timeout=15000)
            name = attachment_name(raw)
            number = 2
            original = Path(name)
            while name.casefold() in used_names:
                name = f'{original.stem}__{number}{original.suffix}'
                number += 1
            used_names.add(name.casefold())
            target = folder / name
            if target.is_file():
                skipped += 1
                LOG.info('跳过已有附件：%s', name)
                continue
            LOG.info('下载 [%d/%d]：%s', index + 1, cards.count(), name)
            with page.expect_download(timeout=60000) as event:
                card.locator(DOWNLOAD).click(timeout=15000)
            download = event.value
            temporary = folder / (name + '.part')
            try:
                download.save_as(str(temporary))
                if temporary.stat().st_size == 0:
                    raise RuntimeError('下载文件为空')
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            downloaded += 1
            LOG.info('已保存：%s（%d bytes）', name, target.stat().st_size)
        except Exception as exc:
            LOG.error('附件 %d 失败：%s', index + 1, exc)
            errors.append(f'附件 {index + 1}: {exc}')
    return downloaded, skipped, errors
