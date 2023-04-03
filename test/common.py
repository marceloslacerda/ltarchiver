import os
import pathlib
import stat

TEST_SOURCE_FILE = pathlib.Path("test/test_source")
import unittest
import shutil
from ltarchiver import common


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        TEST_SOURCE_FILE.write_text("hello world")
    def tearDown(self) -> None:
        os.remove(TEST_SOURCE_FILE)
    def test_get_file_checksum(self):
        self.assertEqual(
            '5eb63bbbe01eeed093cb22bb8f5acdc3',
            common.get_file_checksum(TEST_SOURCE_FILE))
    def test_file_ok_source_or_destination(self):
        # to test the errors of permission I'd have to remove the r/w permissions of a file but doing so is impossible
        # for a regular user to do onto himself (remove from himself the permission to a file that he owns)
        # you would need to log as a different user (eg: root) and them remove the permission
        # but doing so would require sudo or a login which it's far too annoying to repeat automatically, so I'm going
        # to leave that usecase untested.
        common.file_ok(TEST_SOURCE_FILE)

    # todo implement test get_records

if __name__ == '__main__':
    unittest.main()
