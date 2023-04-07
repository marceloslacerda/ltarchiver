import os
import pathlib
import subprocess
import unittest
import datetime
from ltarchiver import common, store
from test.common import TEST_FILE_CHECKSUM, TEST_RECORD_FILE, TEST_SOURCE_FILE, TEST_DESTINATION_DIRECTORY, \
    write_test_recorbook, remove_file


class MyTestCase(unittest.TestCase):
    def test_file_not_exists_no_recordbook(self):
        remove_file(common.recordbook_path)
        self.assertRaises(FileNotFoundError, store.file_not_exists, "", pathlib.Path("nopath"))

    def test_file_not_exists_file_in_recordbook(self):
        write_test_recorbook(common.recordbook_path)
        self.assertRaises(common.LTAError, store.file_not_exists, 'bogus md5', TEST_SOURCE_FILE.name)
        self.assertRaises(common.LTAError, store.file_not_exists, TEST_FILE_CHECKSUM, "bogus name")
        store.file_not_exists("bogus md5", "bogus name")

    def test_check_recordbook_file_not_found(self):
        remove_file(common.recordbook_checksum_file_path)
        self.assertRaises(FileNotFoundError, store.check_recordbook_md5, common.recordbook_checksum_file_path)
        f = open(common.recordbook_checksum_file_path, "wt")
        f.close()
        self.assertTrue(common.recordbook_checksum_file_path.exists())
        self.assertRaises(FileNotFoundError, store.check_recordbook_md5, common.recordbook_checksum_file_path)

    def test_check_recordbook_correct_md5(self):
        write_test_recorbook(common.recordbook_path)
        subprocess.check_output(
            f"md5sum {common.recordbook_path} > {common.recordbook_checksum_file_path}", encoding='utf-8', shell=True
        )
        store.check_recordbook_md5(common.recordbook_checksum_file_path)

    def test_check_recordbook_incorrect_md5(self):
        write_test_recorbook(common.recordbook_path)
        common.recordbook_checksum_file_path.write_text("incorrect md5")
        self.assertRaises(common.LTAError, store.check_recordbook_md5, common.recordbook_checksum_file_path)

    def test_sync_recordbooks_no_file(self):
        try:
            os.rmdir("test_data")
        except FileNotFoundError:
            pass
        os.mkdir("test_data")
        self.assertRaises(FileNotFoundError, store.sync_recordbooks, pathlib.Path("test_data"))

if __name__ == '__main__':
    unittest.main()
