import tempfile
import unittest
from pathlib import Path

from yuque import extract_attachments, unique_attachment_path, safe_name, attachment_name, library_url


class UtilityTests(unittest.TestCase):
    def test_windows_names(self):
        self.assertEqual(safe_name('CON'), '_CON')
        self.assertEqual(safe_name('a:b/c'), 'a_b_c')
        self.assertTrue(attachment_name('长' * 300 + '.pdf').endswith('.pdf'))

    def test_library_scope(self):
        self.assertEqual(
            library_url('https://foundationml.yuque.com/a/b/c?x=1'),
            'https://foundationml.yuque.com/a/b',
        )
        with self.assertRaises(ValueError):
            library_url('https://yuque.com.evil.example/a/b')


class MarkdownAttachmentTests(unittest.TestCase):
    def test_extract_attachments_prefers_markdown_names_and_dedupes_urls(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '说明.md'
            path.write_text(
                '[Paper One.pdf](https://foundationml.yuque.com/attachments/yuque/0/2020/pdf/a/one.pdf)\n'
                '[Different name.pdf](https://foundationml.yuque.com/attachments/yuque/0/2020/pdf/a/one.pdf)\n'
                'Bare link: https://foundationml.yuque.com/attachments/yuque/0/2020/pdf/a/two.pdf\n'
                '[Other.pdf](https://example.com/attachments/yuque/not-yuque.pdf)\n',
                encoding='utf-8',
            )
            attachments = extract_attachments(path)
            result = [(item.filename, item.url.rsplit('/', 1)[-1]) for item in attachments]
            self.assertEqual(result, [('Paper One.pdf', 'one.pdf'), ('two.pdf', 'two.pdf')])

    def test_unique_attachment_path_does_not_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (Path(folder) / 'paper.pdf').write_bytes(b'old')
            (Path(folder) / 'paper_2.pdf').write_bytes(b'old')

            self.assertEqual(unique_attachment_path(base, 'paper.pdf'), base / 'paper_3.pdf')
            self.assertEqual(unique_attachment_path(base, 'notes.md'), base / 'notes.md')
