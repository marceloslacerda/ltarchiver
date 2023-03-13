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


def get_records(recordbook_path: pathlib.Path) -> [dict]:
    recordbook = recordbook_path.open("r")
    source = None
    destination = None
    file_name = None
    deleted = None
    version = None
    chunksize = None
    eccsize = None
    timestamp = None
    checksum = None
    checksum_alg = None
    first_item = True
    for line in recordbook:
        line = line.strip()
        parts = line.split(" ")
        if parts[0] == "Item":
            if first_item:
                first_item = False
            else:
                yield {
                    "source": source,
                    "destination": destination,
                    "file_name": file_name,
                    "deleted": deleted,
                    "version": version,
                    "chunksize": chunksize,
                    "eccsize": eccsize,
                    "timestamp": timestamp,
                    "checksum": checksum,
                    "checksum_alg": checksum_alg
                }
        elif parts[0] == "Deleted:":
            deleted = parts[1] == "true"
        elif parts[0] == "Source:":
            source = parts[1]
        elif parts[0] == "Destination:":
            destination = parts[1]
        elif parts[0] == "Checksum:":
            checksum = parts[1]
        elif parts[0] == "File-Name:":
            file_name = parts[1]
    yield {
        "source": source,
        "destination": destination,
        "file_name": file_name,
        "deleted": deleted,
        "version": version,
        "chunksize": chunksize,
        "eccsize": eccsize,
        "timestamp": timestamp,
        "checksum": checksum,
        "checksum_alg": checksum_alg
    }
