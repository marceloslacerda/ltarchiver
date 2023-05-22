import unittest
import subprocess
import shlex

import test
from ltarchiver import common
from test import store_test_file


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        test.setup_test_files()
        common.remove_file(test.TEST_DESTINATION_DIRECTORY)
        common.remove_file(test.TEST_RECOVERY_FILE)

    def test_create_and_restore_small(self):
        original_md5 = common.get_file_checksum(test.TEST_SOURCE_FILE)
        self.assertFalse(test.TEST_DESTINATION_FILE.exists())
        self.assertFalse(test.TEST_RECOVERY_FILE.exists())
        store_test_file()
        destination_md5 = common.get_file_checksum(test.TEST_DESTINATION_FILE)
        self.assertEqual(original_md5, destination_md5)
        test.add_errors_to_file(test.TEST_DESTINATION_FILE)
        destination_md5 = common.get_file_checksum(test.TEST_DESTINATION_FILE)
        self.assertNotEqual(original_md5, destination_md5)
        subprocess.check_call(
            shlex.split(
                f"python3 -m ltarchiver.check_and_restore {test.TEST_DESTINATION_FILE} {test.TEST_RECOVERY_FILE}"
            )
        )
        recovered_md5 = common.get_file_checksum(test.TEST_RECOVERY_FILE)
        self.assertEqual(original_md5, recovered_md5)

    def test_restore_small_ecc(self):
        store_test_file()
        original_ecc_md5 = common.get_file_checksum(test.TEST_CHECKSUM_FILE)
        test.add_errors_to_file(test.TEST_CHECKSUM_FILE)
        self.assertRaises(
            subprocess.CalledProcessError,
            subprocess.check_call,
            shlex.split(
                f"python3 -m ltarchiver.check_and_restore {test.TEST_DESTINATION_FILE} {test.TEST_RECOVERY_FILE}"
            ),
        )
        new_ecc_md5 = common.get_file_checksum(test.TEST_CHECKSUM_FILE)
        self.assertNotEqual(original_ecc_md5, new_ecc_md5)

    def test_create_and_restore_small_too_many_errors(self):
        original_md5 = common.get_file_checksum(test.TEST_SOURCE_FILE)
        self.assertFalse(test.TEST_DESTINATION_FILE.exists())
        self.assertFalse(test.TEST_RECOVERY_FILE.exists())
        store_test_file()
        destination_md5 = common.get_file_checksum(test.TEST_DESTINATION_FILE)
        self.assertEqual(original_md5, destination_md5)
        test.add_errors_to_file(test.TEST_DESTINATION_FILE, 2)
        destination_md5 = common.get_file_checksum(test.TEST_DESTINATION_FILE)
        self.assertNotEqual(original_md5, destination_md5)
        self.assertRaises(
            subprocess.CalledProcessError,
            subprocess.check_call,
            shlex.split(
                f"python3 -m ltarchiver.check_and_restore {test.TEST_DESTINATION_FILE} {test.TEST_RECOVERY_FILE}"
            ),
        )

        recovered_md5 = common.get_file_checksum(test.TEST_RECOVERY_FILE)
        self.assertNotEqual(original_md5, recovered_md5)

    def test_create_and_restore_large(self):
        test.make_random_file(test.TEST_SOURCE_FILE, 1024 * 1024)
        original_md5 = common.get_file_checksum(test.TEST_SOURCE_FILE)
        self.assertFalse(test.TEST_DESTINATION_FILE.exists())
        self.assertFalse(test.TEST_RECOVERY_FILE.exists())
        store_test_file()
        destination_md5 = common.get_file_checksum(test.TEST_DESTINATION_FILE)
        self.assertEqual(original_md5, destination_md5)
        test.add_errors_to_file(test.TEST_DESTINATION_FILE)
        destination_md5 = common.get_file_checksum(test.TEST_DESTINATION_FILE)
        self.assertNotEqual(original_md5, destination_md5)
        subprocess.check_call(
            shlex.split(
                f"python3 -m ltarchiver.check_and_restore {test.TEST_DESTINATION_FILE} {test.TEST_RECOVERY_FILE}"
            )
        )
        recovered_md5 = common.get_file_checksum(test.TEST_RECOVERY_FILE)
        self.assertEqual(original_md5, recovered_md5)


if __name__ == "__main__":
    unittest.main()
