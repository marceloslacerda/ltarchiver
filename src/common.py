import pathlib
import shlex
import subprocess
import sys
from os import access, R_OK, W_OK

recordbook_file_name = "recordbook.txt"
recordbook_dir = pathlib.Path.home() / ".ltarchiver"
recordbook_path = recordbook_dir / recordbook_file_name
recordbook_checksum_file_path = recordbook_dir / "checksum.txt"
RECORD_PATH = recordbook_dir / "new_transaction.txt"
ecc_dir_name = "ecc"
chunksize = 128  # bytes
eccsize = 8  # bytes


def error(msg: str):
    print(msg, file=sys.stderr)
    exit(1)


def get_file_checksum(source: pathlib.Path):
    return subprocess.check_output(
        shlex.split(f"md5sum {source}"), encoding="utf-8"
    ).split()[0]


def file_ok(path: pathlib.Path, source=True):
    if not path.exists():
        error(f"File {path} does not exist")
    if source:
        if not path.is_file():
            error(f"Path {path} does not point to a file")
        if not access(path, R_OK):
            error(f"File {path} is not readable")
    else:
        if not path.is_dir():
            error(f"Path {path} does not point to a file")
        if not access(path, W_OK):
            error(f"File {path} is not writable")
