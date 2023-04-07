import os
import pathlib
import unittest
from ltarchiver import common
import datetime

TEST_FILE_CHECKSUM = '5eb63bbbe01eeed093cb22bb8f5acdc3'
TEST_SOURCE_FILE = pathlib.Path("test/test_source")
TEST_RECORD_FILE = pathlib.Path("test/test_record_file")
TEST_DESTINATION_DIRECTORY = pathlib.Path("test/test_destination_dir")


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


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        TEST_SOURCE_FILE.write_text("hello world")

    def tearDown(self) -> None:
        os.remove(TEST_SOURCE_FILE)
        try:
            os.remove(TEST_RECORD_FILE)
        except FileNotFoundError:
            pass

    def test_get_file_checksum(self):
        self.assertEqual(
            TEST_FILE_CHECKSUM,
            common.get_file_checksum(TEST_SOURCE_FILE))

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
        self.assertEqual(
            {"version", "deleted", "file_name", "source", "destination", "chunksize", "eccsize", "timestamp",
             "checksum_alg", "checksum"}, set(record.keys()))
        self.assertEqual(record["version"], 1)
        self.assertEqual(record["deleted"], False)
        self.assertEqual(record["file_name"], "test_source")
        self.assertEqual(record["source"], str(TEST_SOURCE_FILE.absolute()))
        self.assertEqual(record["destination"], str(TEST_DESTINATION_DIRECTORY.absolute()))
        self.assertEqual(record["chunksize"], common.chunksize)
        self.assertEqual(record["eccsize"], common.eccsize)
        self.assertEqual(record["checksum_alg"], "md5")
        self.assertEqual(record["checksum"], TEST_FILE_CHECKSUM)

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
        self.assertEqual(
            {"version", "deleted", "file_name", "source", "destination", "chunksize", "eccsize", "timestamp",
             "checksum_alg", "checksum"}, set(record.keys()))
        self.assertEqual(record["version"], 1)
        self.assertEqual(record["deleted"], False)
        self.assertEqual(record["file_name"], "test_source")
        self.assertEqual(record["source"], str(TEST_SOURCE_FILE.absolute()))
        self.assertEqual(record["destination"], str(TEST_DESTINATION_DIRECTORY.absolute()))
        self.assertEqual(record["chunksize"], common.chunksize)
        self.assertEqual(record["eccsize"], common.eccsize)
        self.assertEqual(record["checksum_alg"], "md5")
        self.assertEqual(record["checksum"], TEST_FILE_CHECKSUM)
        record = records[1]
        self.assertEqual(
            {"version", "deleted", "file_name", "source", "destination", "chunksize", "eccsize", "timestamp",
             "checksum_alg", "checksum"}, set(record.keys()))
        self.assertEqual(record["version"], 2)
        self.assertEqual(record["deleted"], True)
        self.assertEqual(record["file_name"], "test_source2")
        self.assertEqual(record["source"], str(TEST_SOURCE_FILE.absolute()) + "2")
        self.assertEqual(record["destination"], str(TEST_DESTINATION_DIRECTORY.absolute()) + "2")
        self.assertEqual(record["chunksize"], 40)
        self.assertEqual(record["eccsize"], 10)
        self.assertEqual(record["checksum_alg"], "sha1")
        self.assertEqual(record["checksum"], "4321")


if __name__ == '__main__':
    unittest.main()
