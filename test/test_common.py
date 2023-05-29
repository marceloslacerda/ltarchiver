import pathlib
import shutil
import unittest
import datetime

import test
from ltarchiver import common

from test import (
    TEST_FILE_CHECKSUM,
    TEST_DIRECTORY,
    TEST_SOURCE_FILE,
    TEST_RECORD_FILE,
    TEST_DESTINATION_DIRECTORY,
    write_test_recorbook,
    write_checksum_of_file,
    setup_test_files,
)


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        setup_test_files()

    def test_decide_recordbooks_option_1(self):
        output = "1"

        def fake_input():
            return output

        common.input = fake_input
        common.recordbook_path.write_text("text 1")
        dest_recordbook = pathlib.Path("test_data/other_recordbook.txt")
        dest_recordbook_checksum = pathlib.Path(
            "test_data/other_recordbook_checksum.txt"
        )
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
        TEST_DESTINATION_DIRECTORY.mkdir(parents=True)
        dest_recordbook = TEST_DESTINATION_DIRECTORY / "other_recordbook.txt"
        dest_recordbook_checksum = (
            TEST_DESTINATION_DIRECTORY / "other_recordbook_checksum.txt"
        )
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
        test.TEST_DESTINATION_DIRECTORY.mkdir(parents=True, exist_ok=True)
        common.recordbook_path.write_text("text 1")
        dest_recordbook = test.TEST_DESTINATION_DIRECTORY / common.recordbook_file_name
        dest_recordbook_checksum = (
            test.TEST_DESTINATION_DIRECTORY / "other_recordbook_checksum.txt"
        )
        dest_recordbook.write_text("text 1")
        write_checksum_of_file(dest_recordbook, dest_recordbook_checksum)
        self.assertRaises(
            common.LTAError,
            common.decide_recordbooks,
            dest_recordbook,
            dest_recordbook_checksum,
        )
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
        records = list(common.get_records(common.recordbook_path))
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.version, 1)
        self.assertEqual(record.deleted, False)
        self.assertEqual(record.file_name, "test_source")
        self.assertEqual(record.source, TEST_SOURCE_FILE.absolute())
        self.assertEqual(record.destination, str(TEST_DESTINATION_DIRECTORY.absolute()))
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
        self.assertEqual(record.destination, str(TEST_DESTINATION_DIRECTORY.absolute()))
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

    def test_get_device_uuid_from_path(self):
        print(common.get_device_uuid_and_root_from_path(pathlib.Path("/")))
        self.assertTrue(True)

    def test_record_file_path(self):
        write_test_recorbook()
        record = list(common.get_records(common.recordbook_path))[0]
        self.assertEqual(record.file_path(TEST_DIRECTORY), TEST_SOURCE_FILE)

    def test_ecc_file_path(self):
        write_test_recorbook()
        record = list(common.get_records(common.recordbook_path))[0]
        self.assertEqual(
            record.ecc_file_path(TEST_DIRECTORY),
            TEST_DIRECTORY / common.METADATA_DIR_NAME / "ecc" / TEST_FILE_CHECKSUM,
        )

    def test_get_validation_valid(self):
        uuid, _ = common.get_device_uuid_and_root_from_path(pathlib.Path("."))
        record = common.Record(
            datetime.datetime.now(),
            TEST_SOURCE_FILE,
            uuid,
            TEST_SOURCE_FILE.name,
            TEST_FILE_CHECKSUM,
            TEST_FILE_CHECKSUM,
        )
        ecc_path = record.ecc_file_path(TEST_DIRECTORY)
        ecc_path.parent.mkdir(parents=True)
        # copy necessary for the checksums to match
        shutil.copy(TEST_SOURCE_FILE, ecc_path)
        old_method = common.get_root_from_uuid

        def test_get(uuid_: str):
            return TEST_DIRECTORY

        common.get_root_from_uuid = test_get
        self.assertEqual(record.get_validation(), common.Validation.VALID)
        common.get_root_from_uuid = old_method

    def test_get_validation_ecc_corrupted(self):
        uuid, _ = common.get_device_uuid_and_root_from_path(pathlib.Path("."))
        record = common.Record(
            datetime.datetime.now(),
            TEST_SOURCE_FILE,
            uuid,
            TEST_SOURCE_FILE.name,
            TEST_FILE_CHECKSUM,
            "asdf",
        )
        ecc_path = record.ecc_file_path(TEST_DIRECTORY)
        ecc_path.parent.mkdir(parents=True)
        # copy necessary for the checksums to match
        shutil.copy(TEST_SOURCE_FILE, ecc_path)
        old_method = common.get_root_from_uuid

        def test_get(uuid_: str):
            return TEST_DIRECTORY

        common.get_root_from_uuid = test_get
        self.assertEqual(record.get_validation(), common.Validation.ECC_CORRUPTED)
        common.get_root_from_uuid = old_method

    def test_get_validation_corrupted(self):
        uuid, _ = common.get_device_uuid_and_root_from_path(pathlib.Path("."))
        record = common.Record(
            datetime.datetime.now(),
            TEST_SOURCE_FILE,
            uuid,
            TEST_SOURCE_FILE.name,
            "asdf",
            TEST_FILE_CHECKSUM,
        )
        ecc_path = record.ecc_file_path(TEST_DIRECTORY)
        ecc_path.parent.mkdir(parents=True)
        # copy necessary for the checksums to match
        shutil.copy(TEST_SOURCE_FILE, ecc_path)
        old_method = common.get_root_from_uuid

        def test_get(uuid_: str):
            return TEST_DIRECTORY

        common.get_root_from_uuid = test_get
        self.assertEqual(record.get_validation(), common.Validation.CORRUPTED)
        common.get_root_from_uuid = old_method

    def test_get_validation_doesnt_exist(self):
        uuid, _ = common.get_device_uuid_and_root_from_path(pathlib.Path("."))
        record = common.Record(
            datetime.datetime.now(),
            TEST_SOURCE_FILE,
            uuid,
            TEST_SOURCE_FILE.name,
            TEST_FILE_CHECKSUM,
            TEST_FILE_CHECKSUM,
        )
        ecc_path = record.ecc_file_path(TEST_DIRECTORY)
        ecc_path.parent.mkdir(parents=True)
        # copy necessary for the checksums to match
        shutil.copy(TEST_SOURCE_FILE, ecc_path)
        old_method = common.get_root_from_uuid

        def test_get(uuid_: str):
            return TEST_DIRECTORY

        common.get_root_from_uuid = test_get
        common.remove_file(TEST_SOURCE_FILE)
        self.assertEqual(record.get_validation(), common.Validation.DOESNT_EXIST)
        common.get_root_from_uuid = old_method

    def test_get_validation_ecc_doesnt_exist(self):
        uuid, _ = common.get_device_uuid_and_root_from_path(pathlib.Path("."))
        record = common.Record(
            datetime.datetime.now(),
            TEST_SOURCE_FILE,
            uuid,
            TEST_SOURCE_FILE.name,
            TEST_FILE_CHECKSUM,
            TEST_FILE_CHECKSUM,
        )
        ecc_path = record.ecc_file_path(TEST_DIRECTORY)
        ecc_path.parent.mkdir(parents=True)
        # copy necessary for the checksums to match
        shutil.copy(TEST_SOURCE_FILE, ecc_path)
        old_method = common.get_root_from_uuid

        def test_get(uuid_: str):
            return TEST_DIRECTORY

        common.get_root_from_uuid = test_get
        common.remove_file(ecc_path)
        self.assertEqual(record.get_validation(), common.Validation.ECC_DOESNT_EXIST)
        common.get_root_from_uuid = old_method

    def test_get_root_from_uuid(self):
        # just test that it doesn't fail
        uuid, root_first = common.get_device_uuid_and_root_from_path(pathlib.Path("."))
        root_second = common.get_root_from_uuid(uuid)
        self.assertEqual(root_first, root_second)


if __name__ == "__main__":
    unittest.main()
