import datetime
import pathlib
import shlex
import shutil
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


class LTAError(Exception):
    def __init__(self, error_message):
        self.args = (error_message,)


def error(msg: str):
    print(msg, file=sys.stderr)
    exit(1)


def get_file_checksum(source: pathlib.Path):
    return subprocess.check_output(
        shlex.split(f"md5sum {source}"), encoding="utf-8"
    ).split()[0]


def file_ok(path: pathlib.Path, source=True):
    if not path.exists():
        return LTAError(f"File {path} does not exist")
    if source:
        if not path.is_file():
            return LTAError(f"Path {path} does not point to a file")
        if not access(path, R_OK):
            return LTAError(f"File {path} is not readable")
    else:
        if not path.is_dir():
            return LTAError(f"Path {path} does not point to a file")
        if not access(path, W_OK):
            return LTAError(f"File {path} is not writable")


def decide_recordbooks(destination_recordbook_path: pathlib.Path):
    subprocess.call(shlex.split(f"diff {recordbook_path} {destination_recordbook_path}"))
    while True:
        print("What should be done?")
        print(f"1 - Overwrite the contents of {recordbook_path} with {destination_recordbook_path}")
        print(f"2 - Overwrite the contents of {destination_recordbook_path} with {recordbook_path}")
        print("3 - Abort")
        s = input()
        if s == "1":
            shutil.copy(destination_recordbook_path, recordbook_path)
        elif s == "2":
            shutil.copy(recordbook_path, destination_recordbook_path)
        elif s == "3":
            raise LTAError("Aborted by the request of the user")
        else:
            print(f"{s} is not a number between 1 and 3")
            continue
        break


def get_records(recordbook_path: pathlib.Path) -> [dict]:
    recordbook = recordbook_path.open("r")
    source = None
    destination = None
    file_name = None
    deleted = None
    version = None
    chunksize_ = None
    eccsize_ = None
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
                    "chunksize": chunksize_,
                    "eccsize": eccsize_,
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
        elif parts[0] == "Bytes-per-chunk:":
            chunksize_ = int(parts[1])
        elif parts[0] == "EC-bytes-per-chunk:":
            eccsize_ = int(parts[1])
        elif parts[0] == "Timestamp:":
            timestamp = datetime.datetime.fromisoformat(parts[1])
        elif parts[0] == "Checksum-Algorithm:":
            checksum_alg = parts[1]
        elif parts[0] == "Version:":
            version = int(parts[1])
    recordbook.close()
    if first_item:
        return []
    else:
        yield {
            "source": source,
            "destination": destination,
            "file_name": file_name,
            "deleted": deleted,
            "version": version,
            "chunksize": chunksize_,
            "eccsize": eccsize_,
            "timestamp": timestamp,
            "checksum": checksum,
            "checksum_alg": checksum_alg
        }
