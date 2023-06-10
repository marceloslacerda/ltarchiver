import datetime
import os
import pathlib
import random
import shlex
import shutil
import subprocess
import unittest

from ltarchiver import common

TEST_FILE_CHECKSUM = "5eb63bbbe01eeed093cb22bb8f5acdc3"
TEST_ECC_CHECKSUM = "30db10ac181aa54fcc306ead2b8fb87a"
TEST_DIRECTORY = pathlib.Path("test_data").resolve()
TEST_SOURCE_FILE = TEST_DIRECTORY / "test_source"
TEST_RECORD_FILE = (
    TEST_DIRECTORY / common.METADATA_DIR_NAME / common.recordbook_file_name
)
TEST_DESTINATION_DIRECTORY = TEST_DIRECTORY / "test_destination_dir"
TEST_DESTINATION_FILE = TEST_DESTINATION_DIRECTORY / TEST_SOURCE_FILE.name
TEST_RECOVERY_FILE = pathlib.Path("restore_dir/test_source")
TEST_CHECKSUM_FILE = (
    TEST_DESTINATION_DIRECTORY
    / common.METADATA_DIR_NAME
    / pathlib.Path("ecc/")
    / TEST_FILE_CHECKSUM
)


def write_test_recorbook(path: pathlib.Path = common.recordbook_path):
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


def setup_test_files():
    shutil.rmtree("test_data", ignore_errors=True)
    common.recordbook_dir.mkdir(parents=True)
    TEST_SOURCE_FILE.write_text("hello world")
    write_checksum_of_file(TEST_SOURCE_FILE, common.recordbook_checksum_file_path)
    TEST_DESTINATION_DIRECTORY.mkdir(parents=True, exist_ok=True)


class BaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        setup_test_files()


def add_errors_to_file(file_path: pathlib.Path, error_no: int = 1):
    chunksize = 253
    out_path = pathlib.Path("test_data/temp_file")
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
    subprocess.check_call(
        [
            "dd",
            "if=/dev/random",
            "of=" + str(file_path),
            "count=1",
            "bs=" + str(file_size),
        ]
    )


def store_test_file():
    subprocess.check_call(
        shlex.split(
            f"python3 -m ltarchiver.store {TEST_SOURCE_FILE} {TEST_DESTINATION_DIRECTORY}"
        )
    )
