import unittest

from ltarchiver import refresh_device, common
import test


class MyTestCase(test.BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        test.setup_test_files()
        common.remove_file(test.TEST_DESTINATION_DIRECTORY)
        common.remove_file(test.TEST_RECOVERY_FILE)
        test.store_test_file()

    def test_basic(self):
        refresh_device.refresh(str(test.TEST_DIRECTORY), test.TEST_DIRECTORY)
        self.assertTrue(True)

    def test_corrupted(self):
        test.add_errors_to_file(test.TEST_DESTINATION_FILE, 1)
        refresh_device.refresh(str(test.TEST_DIRECTORY), test.TEST_DIRECTORY)
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
