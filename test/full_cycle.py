import os
import pathlib
import re
import shutil
import unittest
import subprocess
import shlex
import random
import tempfile
from test import common
from ltarchiver.common import get_file_checksum

TEST_DESTINATION_DIRECTORY = pathlib.Path("test_destination")
TEST_DESTINATION_FILE = TEST_DESTINATION_DIRECTORY / common.TEST_SOURCE_FILE.name
TEST_RECOVERY_FILE = pathlib.Path("restore_dir/test_source")
TEST_CHECKSUM_FILE = (
    TEST_DESTINATION_DIRECTORY
    / pathlib.Path("ltarchiver/ecc/")
    / common.TEST_FILE_CHECKSUM
)


def add_errors_to_file(file_path: pathlib.Path, error_no: int = 1):
    chunksize = 253
    out_path = pathlib.Path('test_data/temp_file')
    with file_path.open("rb") as f:
        with out_path.open("wb") as out:
            while True:
                original_bytes = f.read(chunksize)
                content = bytearray(original_bytes)
                if not content:
                    break
                idxs = random.sample(range(len(content)), error_no)
                for idx in idxs:
                    content[idx] = (content[idx] + random.randint(0, 254)) % 0xFF
                    # content[idx] = 0x00
                out.write(content)
    os.sync()
    shutil.copy(str(out_path), str(file_path))
    common.remove_file(out_path)



def make_random_file(file_path: pathlib.Path, file_size: int):
    subprocess.check_call(["dd", "if=/dev/random", "of=" + str(file_path), "count=1", "bs=" + str(file_size)])


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        common.setup_test_files()
        common.remove_file(TEST_DESTINATION_DIRECTORY)
        common.remove_file(TEST_RECOVERY_FILE)

    def test_create_and_restore_small(self):
        original_md5 = get_file_checksum(common.TEST_SOURCE_FILE)
        self.assertFalse(TEST_DESTINATION_FILE.exists())
        self.assertFalse(TEST_RECOVERY_FILE.exists())
        subprocess.check_call(
            shlex.split(
                f"python3 -m ltarchiver.store {common.TEST_SOURCE_FILE} {TEST_DESTINATION_DIRECTORY}"
            )
        )
        destination_md5 = get_file_checksum(TEST_DESTINATION_FILE)
        self.assertEqual(original_md5, destination_md5)
        add_errors_to_file(TEST_DESTINATION_FILE)
        destination_md5 = get_file_checksum(TEST_DESTINATION_FILE)
        self.assertNotEqual(original_md5, destination_md5)
        subprocess.check_call(
            shlex.split(
                f"python3 -m ltarchiver.check_and_restore {TEST_DESTINATION_FILE} {TEST_RECOVERY_FILE}"
            )
        )
        recovered_md5 = get_file_checksum(TEST_RECOVERY_FILE)
        self.assertEqual(original_md5, recovered_md5)

    def test_restore_small_ecc(self):
        original_md5 = get_file_checksum(common.TEST_SOURCE_FILE)
        subprocess.check_call(
            shlex.split(
                f"python3 -m ltarchiver.store {common.TEST_SOURCE_FILE} {TEST_DESTINATION_DIRECTORY}"
            )
        )
        original_ecc_md5 = get_file_checksum(TEST_CHECKSUM_FILE)
        add_errors_to_file(TEST_CHECKSUM_FILE)
        self.assertRaises(
            subprocess.CalledProcessError,
            subprocess.check_call,
            shlex.split(
                f"python3 -m ltarchiver.check_and_restore {TEST_DESTINATION_FILE} {TEST_RECOVERY_FILE}"
            )
            )
        new_ecc_md5 = get_file_checksum(TEST_CHECKSUM_FILE)
        self.assertNotEqual(original_ecc_md5, new_ecc_md5)

    def test_create_and_restore_small_too_many_errors(self):
        original_md5 = get_file_checksum(common.TEST_SOURCE_FILE)
        self.assertFalse(TEST_DESTINATION_FILE.exists())
        self.assertFalse(TEST_RECOVERY_FILE.exists())
        subprocess.check_call(
            shlex.split(
                f"python3 -m ltarchiver.store {common.TEST_SOURCE_FILE} {TEST_DESTINATION_DIRECTORY}"
            )
        )
        destination_md5 = get_file_checksum(TEST_DESTINATION_FILE)
        self.assertEqual(original_md5, destination_md5)
        add_errors_to_file(TEST_DESTINATION_FILE, 2)
        destination_md5 = get_file_checksum(TEST_DESTINATION_FILE)
        self.assertNotEqual(original_md5, destination_md5)
        self.assertRaises(
            subprocess.CalledProcessError,
            subprocess.check_call,
            shlex.split(
                f"python3 -m ltarchiver.check_and_restore {TEST_DESTINATION_FILE} {TEST_RECOVERY_FILE}"
            )
        )

        recovered_md5 = get_file_checksum(TEST_RECOVERY_FILE)
        self.assertNotEqual(original_md5, recovered_md5)

    def test_create_and_restore_large(self):
        make_random_file(common.TEST_SOURCE_FILE, 1024*1024)
        original_md5 = get_file_checksum(common.TEST_SOURCE_FILE)
        self.assertFalse(TEST_DESTINATION_FILE.exists())
        self.assertFalse(TEST_RECOVERY_FILE.exists())
        subprocess.check_call(
            shlex.split(
                f"python3 -m ltarchiver.store {common.TEST_SOURCE_FILE} {TEST_DESTINATION_DIRECTORY}"
            )
        )
        destination_md5 = get_file_checksum(TEST_DESTINATION_FILE)
        self.assertEqual(original_md5, destination_md5)
        add_errors_to_file(TEST_DESTINATION_FILE)
        destination_md5 = get_file_checksum(TEST_DESTINATION_FILE)
        self.assertNotEqual(original_md5, destination_md5)
        subprocess.check_call(
            shlex.split(
                f"python3 -m ltarchiver.check_and_restore {TEST_DESTINATION_FILE} {TEST_RECOVERY_FILE}"
            )
        )
        recovered_md5 = get_file_checksum(TEST_RECOVERY_FILE)
        self.assertEqual(original_md5, recovered_md5)



if __name__ == "__main__":
    unittest.main()
