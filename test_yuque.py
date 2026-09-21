import tempfile
import unittest
from pathlib import Path

from yuque import Document, save_markdown, safe_name, attachment_name, library_url


class MarkdownTests(unittest.TestCase):
    def test_body_survives_attachment_and_viewer_removal(self):
        html = '''<ne-p>第一段正文</ne-p>
        <ne-card data-card-name="localdoc"><div data-testid="ne-card-local-doc-viewer">secret.pdf<iframe>预览</iframe></div></ne-card>
        <ne-p>第二段正文 <strong>重点</strong></ne-p>
        <ne-p><ne-card data-card-name="bookmarkInline"><img data-testid="ne-card-bookmark-icon" src="data:icon"><a href="/reference">参考</a></ne-card></ne-p>
        <ne-p><img src="/figure.png"></ne-p>'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            save_markdown(html, Document('标题', 'https://foundationml.yuque.com/a/b/c'), path)
            result = (path / '说明.md').read_text(encoding='utf-8')
            self.assertIn('第一段正文\n\n第二段正文', result)
            self.assertIn('**重点**', result)
            self.assertIn('[参考](https://foundationml.yuque.com/reference)', result)
            self.assertIn('https://foundationml.yuque.com/figure.png', result)
            for unwanted in ('secret.pdf', '预览', 'data:icon', 'ne-card'):
                self.assertNotIn(unwanted, result)
            save_markdown('<ne-p>已更新</ne-p>', Document('标题', 'https://foundationml.yuque.com/a/b/c'), path)
            self.assertNotIn('第一段正文', (path / '说明.md').read_text(encoding='utf-8'))

    def test_windows_names_and_library_scope(self):
        self.assertEqual(safe_name('CON'), '_CON')
        self.assertEqual(safe_name('a:b/c'), 'a_b_c')
        self.assertTrue(attachment_name('长' * 300 + '.pdf').endswith('.pdf'))
        self.assertEqual(library_url('https://foundationml.yuque.com/a/b/c?x=1'), 'https://foundationml.yuque.com/a/b')
        with self.assertRaises(ValueError):
            library_url('https://yuque.com.evil.example/a/b')


if __name__ == '__main__':
    unittest.main()
