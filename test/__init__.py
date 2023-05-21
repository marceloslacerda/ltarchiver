import datetime
import pathlib
import shutil
import subprocess

from ltarchiver import common

TEST_FILE_CHECKSUM = "5eb63bbbe01eeed093cb22bb8f5acdc3"
TEST_DIRECTORY = pathlib.Path("test_data")
TEST_SOURCE_FILE = TEST_DIRECTORY / "test_source"
TEST_RECORD_FILE = TEST_DIRECTORY / "test_record_file"
TEST_DESTINATION_DIRECTORY = TEST_DIRECTORY / "test_destination_dir"


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


def setup_test_files():
    shutil.rmtree("test_data", ignore_errors=True)
    common.recordbook_dir.mkdir(parents=True)
    TEST_SOURCE_FILE.write_text("hello world")
    write_checksum_of_file(TEST_SOURCE_FILE, common.recordbook_checksum_file_path)
