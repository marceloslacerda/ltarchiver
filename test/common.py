import os
import pathlib
import shutil
import subprocess
import unittest
from ltarchiver import common
import datetime

TEST_FILE_CHECKSUM = "5eb63bbbe01eeed093cb22bb8f5acdc3"
TEST_SOURCE_FILE = pathlib.Path("test_data/test_source")
TEST_RECORD_FILE = pathlib.Path("test_data/test_record_file")
TEST_DESTINATION_DIRECTORY = pathlib.Path("test_data/test_destination_dir")


def remove_file(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def write_test_recorbook(path: pathlib.Path = TEST_RECORD_FILE):
    with open(path, "w") as f:
        f.write("Item\n")
        f.write("Version: 1\n")
        f.write("Deleted: false\n")
        f.write(f"File-Name: test_source\n")
        f.write(f"Source: {TEST_SOURCE_FILE.absolute()}\n")
        f.write(f"Destination: {TEST_DESTINATION_DIRECTORY.absolute()}\n")
        f.write(f"Bytes-per-chunk: {common.chunksize}\n")
        f.write(f"EC-bytes-per-chunk: {common.eccsize}\n")
        f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
        f.write(f"Checksum-Algorithm: md5\n")
        f.write(f"Checksum: {TEST_FILE_CHECKSUM}\n")

def write_checksum_of_file(file: pathlib.Path, checksum_path: pathlib.Path):
    subprocess.call(f"md5sum {file} > {checksum_path}", shell=True)

class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree("test_data", ignore_errors=True)
        common.recordbook_dir.mkdir(parents=True)
        TEST_SOURCE_FILE.write_text("hello world")
        write_checksum_of_file(TEST_SOURCE_FILE, common.recordbook_checksum_file_path)


    def test_decide_recordbooks_option_1(self):
        output = "1"

        def fake_input():
            return output

        common.input = fake_input
        common.recordbook_path.write_text("text 1")
        dest_recordbook = pathlib.Path("test_data/other_recordbook.txt")
        dest_recordbook_checksum = pathlib.Path("test_data/other_recordbook_checksum.txt")
        dest_recordbook.write_text("text 2")
        write_checksum_of_file(dest_recordbook, dest_recordbook_checksum)
        common.decide_recordbooks(dest_recordbook, dest_recordbook_checksum)
        self.assertEqual(dest_recordbook.read_text(), "text 2")
        common.input = input

    def test_decide_recordbooks_option_2(self):
        output = "2"

        def fake_input():
            return output

        common.input = fake_input
        common.recordbook_path.write_text("text 1")
        dest_recordbook = pathlib.Path("other_recordbook.txt")
        dest_recordbook_checksum = pathlib.Path("test_data/other_recordbook_checksum.txt")
        write_checksum_of_file(dest_recordbook, dest_recordbook_checksum)
        dest_recordbook.write_text("text 2")
        common.decide_recordbooks(dest_recordbook, dest_recordbook_checksum)
        self.assertEqual(common.recordbook_path.read_text(), "text 1")
        common.input = input

    def test_decide_recordbooks_option_3(self):
        output = "3"

        def fake_input():
            return output

        common.input = fake_input
        common.recordbook_path.write_text("text 1")
        dest_recordbook_checksum = pathlib.Path("test_data/other_recordbook_checksum.txt")
        write_checksum_of_file(common.recordbook_path, dest_recordbook_checksum)
        self.assertRaises(common.LTAError, common.decide_recordbooks, TEST_RECORD_FILE, dest_recordbook_checksum)
        common.input = input

    def test_get_file_checksum(self):
        self.assertEqual(TEST_FILE_CHECKSUM, common.get_file_checksum(TEST_SOURCE_FILE))

    def test_file_ok_source_or_destination(self):
        # to test the errors of permission I'd have to remove the r/w permissions of a file but doing so is impossible
        # for a regular user to do onto himself (remove from himself the permission to a file that he owns)
        # you would need to log as a different user (eg: root) and them remove the permission
        # but doing so would require sudo or a login which it's far too annoying to repeat automatically, so I'm going
        # to leave that usecase untested.
        common.file_ok(TEST_SOURCE_FILE)

    def test_get_records_empty(self):
        with open(TEST_RECORD_FILE, "w") as f:
            f.write("\n")
        records = list(common.get_records(TEST_RECORD_FILE))
        self.assertEqual(len(records), 0)

    def test_get_records(self):
        write_test_recorbook()
        records = list(common.get_records(TEST_RECORD_FILE))
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.version, 1)
        self.assertEqual(record.deleted, False)
        self.assertEqual(record.file_name, "test_source")
        self.assertEqual(record.source, TEST_SOURCE_FILE.absolute())
        self.assertEqual(
            record.destination, TEST_DESTINATION_DIRECTORY.absolute()
        )
        self.assertEqual(record.chunksize, common.chunksize)
        self.assertEqual(record.eccsize, common.eccsize)
        self.assertEqual(record.checksum_algorithm, "md5")
        self.assertEqual(record.checksum, TEST_FILE_CHECKSUM)

    def test_get_records_two_entries(self):
        with open(TEST_RECORD_FILE, "w") as f:
            f.write("Item\n")
            f.write("Version: 1\n")
            f.write("Deleted: false\n")
            f.write(f"File-Name: test_source\n")
            f.write(f"Source: {TEST_SOURCE_FILE.absolute()}\n")
            f.write(f"Destination: {TEST_DESTINATION_DIRECTORY.absolute()}\n")
            f.write(f"Bytes-per-chunk: {common.chunksize}\n")
            f.write(f"EC-bytes-per-chunk: {common.eccsize}\n")
            f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Checksum-Algorithm: md5\n")
            f.write(f"Checksum: {TEST_FILE_CHECKSUM}\n")
            f.write("Item\n")
            f.write("Version: 2\n")
            f.write("Deleted: true\n")
            f.write(f"File-Name: test_source2\n")
            f.write(f"Source: {TEST_SOURCE_FILE.absolute()}2\n")
            f.write(f"Destination: {TEST_DESTINATION_DIRECTORY.absolute()}2\n")
            f.write(f"Bytes-per-chunk: 40\n")
            f.write(f"EC-bytes-per-chunk: 10\n")
            f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Checksum-Algorithm: sha1\n")
            f.write(f"Checksum: 4321\n")
        records = list(common.get_records(TEST_RECORD_FILE))
        self.assertEqual(len(records), 2)
        record = records[0]
        self.assertEqual(record.version, 1)
        self.assertEqual(record.deleted, False)
        self.assertEqual(record.file_name, "test_source")
        self.assertEqual(record.source, TEST_SOURCE_FILE.absolute())
        self.assertEqual(
            record.destination, TEST_DESTINATION_DIRECTORY.absolute()
        )
        self.assertEqual(record.chunksize, common.chunksize)
        self.assertEqual(record.eccsize, common.eccsize)
        self.assertEqual(record.checksum_algorithm, "md5")
        self.assertEqual(record.checksum, TEST_FILE_CHECKSUM)
        record = records[1]
        self.assertEqual(record.version, 2)
        self.assertEqual(record.deleted, True)
        self.assertEqual(record.file_name, "test_source2")
        self.assertEqual(str(record.source), str(TEST_SOURCE_FILE.absolute()) + "2")
        self.assertEqual(
            str(record.destination), str(TEST_DESTINATION_DIRECTORY.absolute()) + "2"
        )
        self.assertEqual(record.chunksize, 40)
        self.assertEqual(record.eccsize, 10)
        self.assertEqual(record.checksum_algorithm, "sha1")
        self.assertEqual(record.checksum, "4321")


if __name__ == "__main__":
    unittest.main()
