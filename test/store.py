import pathlib
import subprocess
import unittest
from ltarchiver import common, store
from test.common import (
    TEST_FILE_CHECKSUM,
    TEST_SOURCE_FILE,
    write_test_recorbook,
    setup_test_files,
)
from ltarchiver.common import remove_file


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        setup_test_files()

    def test_file_not_exists_no_recordbook(self):
        remove_file(common.recordbook_path)
        self.assertRaises(
            FileNotFoundError,
            store.file_not_exists,
            "",
            pathlib.Path("nopath"),
            pathlib.Path("nopath"),
        )

    def test_file_not_exists_file_in_recordbook(self):
        write_test_recorbook(common.recordbook_path)
        self.assertRaises(
            common.LTAError,
            store.file_not_exists,
            "bogus md5",
            TEST_SOURCE_FILE.name,
            TEST_SOURCE_FILE,
        )
        self.assertRaises(
            common.LTAError,
            store.file_not_exists,
            TEST_FILE_CHECKSUM,
            "bogus name",
            TEST_SOURCE_FILE,
        )
        store.file_not_exists(
            "bogus md5", "bogus name", pathlib.Path("test_data/bogus_file")
        )  # test that no error is raised

    def test_check_recordbook_file_not_found(self):
        remove_file(common.recordbook_checksum_file_path)
        self.assertRaises(
            FileNotFoundError,
            common.check_recordbook_md5,
            common.recordbook_checksum_file_path,
        )
        f = open(common.recordbook_checksum_file_path, "wt")
        f.close()
        self.assertTrue(common.recordbook_checksum_file_path.exists())
        self.assertRaises(
            FileNotFoundError,
            common.check_recordbook_md5,
            common.recordbook_checksum_file_path,
        )

    def test_check_recordbook_correct_md5(self):
        write_test_recorbook(common.recordbook_path)
        subprocess.check_output(
            f"md5sum {common.recordbook_path} > {common.recordbook_checksum_file_path}",
            encoding="utf-8",
            shell=True,
        )
        common.check_recordbook_md5(common.recordbook_checksum_file_path)

    def test_check_recordbook_incorrect_md5(self):
        write_test_recorbook(common.recordbook_path)
        common.recordbook_checksum_file_path.write_text("incorrect md5")
        self.assertRaises(
            common.LTAError,
            common.check_recordbook_md5,
            common.recordbook_checksum_file_path,
        )


if __name__ == "__main__":
    unittest.main()
