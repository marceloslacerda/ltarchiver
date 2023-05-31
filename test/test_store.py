import pathlib
import subprocess
import unittest

import test
from ltarchiver import common, store
from test import (
    TEST_FILE_CHECKSUM,
    TEST_SOURCE_FILE,
    write_test_recorbook,
)
from ltarchiver.common import remove_file


class MyTestCase(test.BaseTestCase):
    def test_file_not_exists_no_recordbook(self):
        remove_file(common.recordbook_path)
        self.assertRaises(
            FileNotFoundError,
            store.file_not_exists_in_recordbook,
            "",
            pathlib.Path("nopath"),
            pathlib.Path("nopath"),
        )

    def test_file_not_exists_file_in_recordbook(self):
        write_test_recorbook(common.recordbook_path)
        self.assertRaises(
            common.LTAError,
            store.file_not_exists_in_recordbook,
            "bogus md5",
            TEST_SOURCE_FILE.name,
            TEST_SOURCE_FILE,
        )
        self.assertRaises(
            common.LTAError,
            store.file_not_exists_in_recordbook,
            TEST_FILE_CHECKSUM,
            "bogus name",
            TEST_SOURCE_FILE,
        )
        store.file_not_exists_in_recordbook(
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

    def test_tar_archive(self):
        mydir = test.TEST_DIRECTORY / "mydir"
        mydir.mkdir(parents=True, exist_ok=True)
        tarred = store.tar_directory(mydir)
        self.assertTrue(tarred.exists())
        common.remove_file(mydir)
        self.assertFalse(mydir.exists())
        subprocess.check_call(["tar", "xf", tarred.name], cwd=test.TEST_DIRECTORY)
        self.assertTrue(mydir.exists())

    def test_store(self):
        store.store(
            test.TEST_SOURCE_FILE, test.TEST_DESTINATION_DIRECTORY, non_interactive=True
        )

    def test_store_spaces(self):
        source = test.TEST_DIRECTORY / "test file.txt"
        source.write_text("hello world")
        store.store(source, test.TEST_DESTINATION_DIRECTORY, non_interactive=True)

    def test_store_directory(self):
        source = test.TEST_DIRECTORY / "my dir"
        source.mkdir(parents=True, exist_ok=True)
        store.store(source, test.TEST_DESTINATION_DIRECTORY, non_interactive=True)

    def test_store_twice(self):
        store.store(
            test.TEST_SOURCE_FILE, test.TEST_DESTINATION_DIRECTORY, non_interactive=True
        )
        self.assertRaises(
            common.LTAError,
            store.store,
            test.TEST_SOURCE_FILE,
            test.TEST_DESTINATION_DIRECTORY,
            non_interactive=True,
        )

    def test_store_destination_exists_no_recordbook(self):
        test.TEST_DESTINATION_FILE.write_text("some text")
        self.assertRaises(
            common.LTAError,
            store.store,
            test.TEST_SOURCE_FILE,
            test.TEST_DESTINATION_DIRECTORY,
            non_interactive=True,
        )

    def test_store_destination_exists_with_recordbook(self):
        store.store(
            test.TEST_SOURCE_FILE, test.TEST_DESTINATION_DIRECTORY, non_interactive=True
        )
        other_file_name = "other_file.txt"
        other_file_source = test.TEST_DIRECTORY / other_file_name
        other_file_destination = test.TEST_DESTINATION_DIRECTORY / other_file_name
        other_file_source.write_text("hello second")
        other_file_destination.write_text("something else")
        self.assertRaises(
            common.LTAError,
            store.store,
            other_file_source,
            test.TEST_DESTINATION_DIRECTORY,
            non_interactive=True,
        )


if __name__ == "__main__":
    unittest.main()
