import datetime
import pathlib
import shlex
import shutil
import subprocess
import sys
import typing
from os import access, R_OK, W_OK
from dataclasses import dataclass

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


@dataclass
class TerminalMenu:
    title: str
    options: typing.Dict[str, typing.Callable]
    with_abort: bool = True

    def __post_init__(self):
        def abort():
            raise LTAError("Aborted by the request of the user")

        if self.with_abort:
            self.options["Abort"] = abort

    def show(self):
        callbacks = list(self.options.values())
        while True:
            print(self.title)
            option_count = 1
            for text in self.options.keys():
                print(option_count, '-', text)
                option_count += 1
            s = input()
            try:
                user_input = int(s)
            except ValueError:
                print(f"{s} is not a number")
                continue
            if 1 > user_input > option_count - 1:
                print(f"{s} is not a number between 1 and {option_count - 1}")
                continue
            else:
                callbacks[user_input - 1]()
                break


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


def decide_recordbooks(destination_recordbook_path: pathlib.Path, destination_recordbook_checksum_path: pathlib.Path):
    subprocess.call(shlex.split(f"diff {recordbook_path} {destination_recordbook_path}"))

    def copy_from_to(from_file: pathlib.Path, from_checksum: pathlib.Path, to_file: pathlib.Path,
                     to_checksum: pathlib.Path):
        def copy():
            shutil.copy(from_file, to_file)
            shutil.copy(from_checksum, to_checksum)

        return copy

    menu = TerminalMenu(
        "What should be done?",
        {
            f"Overwrite the contents of {recordbook_path} with {destination_recordbook_path}": (
                copy_from_to(destination_recordbook_path, destination_recordbook_checksum_path, recordbook_path,
                             recordbook_checksum_file_path)
            )
            ,
            f"Overwrite the contents of {destination_recordbook_path} with {recordbook_path}": (
                copy_from_to(recordbook_path, recordbook_checksum_file_path, destination_recordbook_path,
                             destination_recordbook_checksum_path))
        }
    )
    menu.show()


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
