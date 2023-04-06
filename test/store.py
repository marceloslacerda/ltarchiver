import os
import pathlib
import unittest
import datetime
from ltarchiver import common, store
from test.common import TEST_FILE_CHECKSUM, TEST_RECORD_FILE, TEST_SOURCE_FILE, TEST_DESTINATION_DIRECTORY, \
    write_test_recorbook


class MyTestCase(unittest.TestCase):
    def test_file_not_exists_no_recordbook(self):
        try:
            os.remove(common.recordbook_path)
        except FileNotFoundError:
            pass
        self.assertRaises(FileNotFoundError, store.file_not_exists, "", pathlib.Path("nopath"))

    def test_file_not_exists_file_in_recordbook(self):
        write_test_recorbook(common.recordbook_path)
        self.assertRaises(common.LTAError, store.file_not_exists, 'bogus md5', TEST_SOURCE_FILE.name)
        self.assertRaises(common.LTAError, store.file_not_exists, TEST_FILE_CHECKSUM, "bogus name")
        store.file_not_exists("bogus md5", "bogus name")


if __name__ == '__main__':
    unittest.main()
