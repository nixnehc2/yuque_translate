import unittest

from yuque import safe_name, attachment_name, library_url


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


if __name__ == '__main__':
    unittest.main()
