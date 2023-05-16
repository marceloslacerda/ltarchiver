import datetime
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import typing
from os import access, R_OK, W_OK
from dataclasses import dataclass

recordbook_file_name = "recordbook.txt"
if "DEBUG" in os.environ:
    DEBUG = True
    recordbook_dir = pathlib.Path("test_data") / ".ltarchiver"
else:
    DEBUG = False
    recordbook_dir = pathlib.Path.home() / ".ltarchiver"
recordbook_path = recordbook_dir / recordbook_file_name
recordbook_checksum_file_path = recordbook_dir / "checksum.txt"
RECORD_PATH = recordbook_dir / "new_transaction.txt"
ecc_dir_name = "ecc"
chunksize = 1024  # bytes
eccsize = 16  # bytes


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
                print(option_count, "-", text)
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


@dataclass
class Record:
    timestamp: datetime.datetime
    source: pathlib.Path
    destination: pathlib.Path
    file_name: str
    checksum: str
    ecc_checksum: str
    chunksize: int = chunksize
    eccsize: int = eccsize
    checksum_algorithm: str = "md5"
    deleted: bool = False
    version: int = 1

    def write(self, recordbook: pathlib.Path = recordbook_path):
        with recordbook.open("at") as f:
            f.write("Item\n")
            f.write(f"Version: {self.version}\n")
            f.write(f"Deleted: {self.deleted}\n")
            f.write(f"File-Name: {self.file_name}\n")
            f.write(f"Source: {self.source.absolute()}\n")
            f.write(f"Destination: {self.destination}\n")
            f.write(f"Bytes-per-chunk: {self.chunksize}\n")
            f.write(f"EC-bytes-per-chunk: {self.eccsize}\n")
            f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Checksum-Algorithm: {self.checksum_algorithm}\n")
            f.write(f"Checksum: {self.checksum}\n")
            f.write(f"ECC-Checksum: {self.ecc_checksum}\n")


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


def copy_recordbook_from_to(
    from_file: pathlib.Path,
    from_checksum: pathlib.Path,
    to_file: pathlib.Path,
    to_checksum: pathlib.Path,
):
    def copy():
        check_recordbook_md5(from_checksum)
        shutil.copy(from_file, to_file)
        shutil.copy(from_checksum, to_checksum)

    return copy


def decide_recordbooks(
    destination_recordbook_path: pathlib.Path,
    destination_recordbook_checksum_path: pathlib.Path,
):
    subprocess.call(
        shlex.split(f"diff {recordbook_path} {destination_recordbook_path}")
    )
    menu = TerminalMenu(
        "What should be done?",
        {
            f"Overwrite the contents of {recordbook_path} with {destination_recordbook_path}": (
                copy_recordbook_from_to(
                    destination_recordbook_path,
                    destination_recordbook_checksum_path,
                    recordbook_path,
                    recordbook_checksum_file_path,
                )
            ),
            f"Overwrite the contents of {destination_recordbook_path} with {recordbook_path}": (
                copy_recordbook_from_to(
                    recordbook_path,
                    recordbook_checksum_file_path,
                    destination_recordbook_path,
                    destination_recordbook_checksum_path,
                )
            ),
        },
    )
    menu.show()


def get_records(recordbook_path: pathlib.Path) -> [Record]:
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
    ecc_checksum = None
    for line in recordbook:
        line = line.strip()
        parts = line.split(" ")
        if parts[0] == "Item":
            if first_item:
                first_item = False
            else:
                yield Record(
                    source=pathlib.Path(source),
                    destination=pathlib.Path(destination),
                    file_name=file_name,
                    deleted=deleted,
                    version=version,
                    chunksize=chunksize_,
                    eccsize=eccsize_,
                    timestamp=timestamp,
                    checksum=checksum,
                    checksum_algorithm=checksum_alg,
                    ecc_checksum=ecc_checksum,
                )
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
        elif parts[0] == "ECC-Checksum:":
            ecc_checksum = parts[1]
        elif parts[0] == "Version:":
            version = int(parts[1])
    recordbook.close()
    if first_item:
        return []
    else:
        yield Record(
            source=pathlib.Path(source),
            destination=pathlib.Path(destination),
            file_name=file_name,
            deleted=deleted,
            version=version,
            chunksize=chunksize_,
            eccsize=eccsize_,
            timestamp=timestamp,
            checksum=checksum,
            checksum_algorithm=checksum_alg,
            ecc_checksum=ecc_checksum,
        )


def check_recordbook_md5(recordbook_checksum: pathlib.Path):
    if not recordbook_checksum.exists() or recordbook_checksum.stat().st_size == 0:
        raise FileNotFoundError(
            f"Recordbook checksum file {recordbook_checksum} not found or empty"
        )
    try:
        subprocess.check_call(shlex.split(f"md5sum -c {recordbook_checksum}"))
    except subprocess.CalledProcessError as err:
        raise LTAError(
            f"The recordbook checksum file {recordbook_checksum} doesn't match what's stored. Please validate it and retry."
        ) from err


def mark_record_as_deleted(record_idx: int):
    records = list(get_records(recordbook_path))
    records[record_idx].deleted = True
    os.remove(recordbook_path)
    for record in records:
        record.write()


def get_device_uuid_and_root_from_path(path: pathlib.Path) -> (str, pathlib.Path):
    devices_to_uuids = {}
    for line in subprocess.check_output(
        ["ls", "-l", "/dev/disk/by-uuid"], encoding="utf-8"
    ).split("\n")[1:]:
        if not line.strip():
            break
        parts = line.split()
        devices_to_uuids[
            (pathlib.Path("/dev/disk/by-uuid") / pathlib.Path(parts[-1])).resolve(
                strict=True
            )
        ] = parts[-3]
    path_to_devices = {}
    for line in subprocess.check_output("mount", encoding="utf-8").split("\n"):
        if not line.strip():
            break
        if line.startswith("/dev/"):
            parts = line.split()
            path_to_devices[pathlib.Path(parts[2]).resolve(strict=True)] = pathlib.Path(
                parts[0]
            ).resolve(strict=True)
    prev_parent = None
    parent = path.absolute()
    while prev_parent != parent:
        if parent in path_to_devices:
            return devices_to_uuids[path_to_devices[parent]], parent
        else:
            prev_parent = parent
            parent = parent.parent
    raise AttributeError(f"Could not find the device associated with the path {path}")


def record_of_file(
    recordbook_path: pathlib.Path,
    backup_file_checksum: str,
    backup_file_path: pathlib.Path,
):
    for record in get_records(recordbook_path):
        if not record.deleted and (
            record.checksum == backup_file_checksum
            or record.file_name == backup_file_path.name
        ):
            return record
