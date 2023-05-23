import pathlib
import unittest
import datetime

from ltarchiver import refresh_device, common
import test

uuid, root = common.get_device_uuid_and_root_from_path(pathlib.Path("."))

class MyTestCase(test.BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        test.setup_test_files()
        common.remove_file(test.TEST_DESTINATION_DIRECTORY)
        common.remove_file(test.TEST_RECOVERY_FILE)
        test.store_test_file()
        self.record = common.Record(
            timestamp=datetime.datetime.now(),
            file_name=test.TEST_SOURCE_FILE.name,
            source=test.TEST_SOURCE_FILE,
            destination=test.TEST_DESTINATION_DIRECTORY,
            checksum=test.TEST_FILE_CHECKSUM,
            ecc_checksum=test.TEST_ECC_CHECKSUM,
        )

        def test_get_root(uuid_: str):
            return test.TEST_DESTINATION_DIRECTORY

        refresh_device.common.get_root_from_uuid = test_get_root

    def test_basic(self):
        refresh_device.refresh_record(self.record, test.TEST_DESTINATION_DIRECTORY)
        self.assertTrue(test.TEST_DESTINATION_FILE.exists())
        checksum = common.get_file_checksum(test.TEST_DESTINATION_FILE)
        self.assertEqual(test.TEST_FILE_CHECKSUM, checksum)

    def test_corrupted(self):
        test.add_errors_to_file(test.TEST_DESTINATION_FILE, 1)
        refresh_device.refresh_record(self.record, test.TEST_DIRECTORY)
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
