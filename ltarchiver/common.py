import datetime
import enum
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import typing
import psutil
from os import access, R_OK, W_OK
from dataclasses import dataclass

METADATA_DIR_NAME = ".ltarchiver"

recordbook_file_name = "recordbook.txt"
if "DEBUG" in os.environ:
    DEBUG = True
    recordbook_dir = pathlib.Path("test_data") / METADATA_DIR_NAME
else:
    DEBUG = False
    recordbook_dir = pathlib.Path.home() / METADATA_DIR_NAME
recordbook_path = recordbook_dir / recordbook_file_name
recordbook_checksum_file_path = recordbook_dir / "checksum.txt"
RECORD_PATH = recordbook_dir / "new_transaction.txt"
ecc_dir_name = "ecc"
chunksize = 1024  # bytes
eccsize = 16  # bytes


class LTAError(Exception):
    pass


class Validation(enum.Enum):
    ECC_DOESNT_EXIST = "The ecc of the file doesn't exist"
    ECC_CORRUPTED = "The ecc of the file was corrupted"
    DOESNT_EXIST = "The file doesn't exist"
    NO_CHECKSUM_FILE = "The Checksum file doesn't exist"
    CORRUPTED = "The file appears to have been corrupted"
    VALID = "No errors found"

    def __str__(self):
        return self.value


@dataclass
class TerminalMenu:
    title: str
    options: typing.Dict[str, typing.Callable]
    with_abort: bool = True
    REDISPLAY_MENU = "REDISPLAY_MENU"

    @classmethod
    def get_null_option(cls, fun):
        """For a callable returns another callable that will not cause the menu to close if chosen as an option."""

        def f():
            fun()
            return TerminalMenu.REDISPLAY_MENU

        return f

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
                if callbacks[user_input - 1]() == TerminalMenu.REDISPLAY_MENU:
                    continue
                else:
                    break


@dataclass(frozen=True)
class Record:
    timestamp: datetime.datetime
    source: pathlib.Path
    destination: str
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

    def get_validation(self) -> Validation:
        """True if file exists and checksum matches"""
        root = get_root_from_uuid(self.destination)
        path = self.file_path(root)
        if not path.exists():
            return Validation.DOESNT_EXIST
        checksum = get_file_checksum(path)
        if checksum != self.checksum:
            return Validation.CORRUPTED

        ecc_file_path = self.ecc_file_path(root)
        if not ecc_file_path.exists():
            return Validation.ECC_DOESNT_EXIST
        checksum = get_file_checksum(ecc_file_path)
        if checksum != self.ecc_checksum:
            return Validation.ECC_CORRUPTED
        return Validation.VALID

    def file_path(self, root: pathlib.Path):
        return root / self.file_name

    def ecc_file_path(self, root: pathlib.Path) -> pathlib.Path:
        return root / METADATA_DIR_NAME / ecc_dir_name / self.checksum

    def __str__(self):
        return f"Record of {self.file_name} stored on {self.destination}"


def error(msg: str):
    print(msg, file=sys.stderr)
    exit(1)


def get_file_checksum(source: pathlib.Path):
    return subprocess.check_output(
        [f"md5sum", source], encoding="utf-8"
    ).split()[0]


class FileValidation(enum.Enum):
    FILE_DOESNT_EXIST = enum.auto()
    DIRECTORY_DOESNT_EXIST = enum.auto()
    IS_DIRECTORY = enum.auto
    NO_WRITE_PERMISSION_FILE = enum.auto()
    NO_WRITE_PERMISSION_DIRECTORY = enum.auto()
    NO_READ_PERMISSION_FILE = enum.auto()
    NOT_A_FILE = enum.auto()


def file_ok(path: pathlib.Path, source=True):
    """Test for the usefulness of path.

    If source is true the path must exist, be a file and readable.

    If source is False, will test if it's a directory and writable
    or a path that sits in a directory that's writable.

    In case any test fails this function will throw an LTAError with the
    reason.
    """
    if source:
        if not path.exists():
            return LTAError(
                f"File {path} does not exist", FileValidation.FILE_DOESNT_EXIST
            )
        if not path.is_file():
            return LTAError(
                f"Path {path} does not point to a file", FileValidation.NOT_A_FILE
            )
        if not access(path, R_OK):
            return LTAError(
                f"File {path} is not readable", FileValidation.NO_READ_PERMISSION_FILE
            )
    else:
        if not path.exists():
            if not path.parent.exists():
                LTAError(
                    f"Directory {path} does not exist",
                    FileValidation.DIRECTORY_DOESNT_EXIST,
                )
            else:
                if not access(path.parent, W_OK):
                    return LTAError(
                        f"Cannot write to {path} directory",
                        FileValidation.NO_WRITE_PERMISSION_DIRECTORY,
                    )
        if not access(path, W_OK):
            return LTAError(
                f"File {path} is not writable", FileValidation.NO_WRITE_PERMISSION_FILE
            )


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
                    destination=destination,
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
            destination=destination,
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


def get_root_from_uuid(uuid: str) -> pathlib.Path:
    uuid_to_device = {}
    for p in pathlib.Path("/dev/disk/by-uuid").iterdir():
        uuid_to_device[p.name] = p.resolve()
    device_to_path = {}
    for partition in psutil.disk_partitions():
        device_to_path[pathlib.Path(partition.device)] = pathlib.Path(
            partition.mountpoint
        )
    try:
        device = uuid_to_device[uuid]
        try:
            return device_to_path[device]
        except KeyError as err:
            raise AttributeError(
                f"Could not find the root of the device {device}. Is it mounted?"
            ) from err
    except KeyError as err:
        raise AttributeError(
            f"Could not find the device associated with the UUID {uuid}."
            f" Is it pluged int?"
        ) from err


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


class RecordBook:
    def __init__(self, path: pathlib.Path, checksum_file_path: pathlib.Path):
        self.path = path
        self.records: typing.Set[Record] = set(get_records(path))
        self.checksum_file_path = checksum_file_path
        self.valid = True
        self.invalid_reason: Validation = Validation.VALID
        self.validate()

    def merge(self, other_recordbook: "RecordBook"):
        self.records = self.records.union(other_recordbook.records)
        self.write()

    def write(self):
        remove_file(self.path)
        for record in self.records:
            record.write(self.path)
        subprocess.check_call(
            f"md5sum {self.path} > {self.checksum_file_path}", shell=True
        )

    def get_records_by_uuid(self, device_uuid: str) -> typing.Iterable[Record]:
        for record in self.records:
            if record.destination == device_uuid:
                yield record

    def validate(self):
        if not self.path.exists():
            self.valid = False
            self.invalid_reason = Validation.DOESNT_EXIST
        elif not self.checksum_file_path.exists():
            self.valid = False
            self.invalid_reason = Validation.NO_CHECKSUM_FILE
        elif not self.checksum_file_path.read_text() == get_file_checksum(self.path):
            self.valid = False
            self.invalid_reason = Validation.CORRUPTED

    def __str__(self):
        return f"Recordbook stored on {self.path}, {len(self.records)} entries"


def remove_file(path: pathlib.Path):
    try:
        os.remove(path)
    except IsADirectoryError:
        shutil.rmtree(path, ignore_errors=True)
    except FileNotFoundError:
        pass


def validate_and_recover_recordbooks(
    home_recordbook: RecordBook, device_recordbook: RecordBook, first_time_ok=False
):
    home_recordbook.validate()
    device_recordbook.validate()

    def copy_recordbook_callback(a: RecordBook, b: RecordBook):
        def cp():
            b.records = a.records
            b.write()
            b.validate()

        return cp

    if home_recordbook.valid and device_recordbook.valid:
        return
    elif not home_recordbook.valid and not device_recordbook.valid:

        def overwrite_checksums():
            home_recordbook.write()
            device_recordbook.write()

        if (
            home_recordbook.invalid_reason == Validation.DOESNT_EXIST
            and device_recordbook.invalid_reason == Validation.DOESNT_EXIST
        ):
            print("No recordbook found.")
            if not first_time_ok:
                raise LTAError("Please store a file first with the store command.")
            else:
                print("Assuming this is the first time you are running ltarchiver.")
        else:
            # todo recordbooks can have different reasons for being invalid
            TerminalMenu(
                f"Neither the home recordbook {home_recordbook.path}"
                f"\nnor the device recordbook {device_recordbook}"
                f"\nmatches its checksum. What do you want to do?",
                {
                    "Show contents of home recordbook": TerminalMenu.get_null_option(
                        lambda: print(home_recordbook.path.read_text())
                    ),
                    "Show contents of device recordbook": TerminalMenu.get_null_option(
                        lambda: print(device_recordbook.path.read_text())
                    ),
                    "Overwrite checksum files": overwrite_checksums(),
                },
            )
    elif not home_recordbook.valid:
        if home_recordbook.invalid_reason == Validation.NO_CHECKSUM_FILE:
            TerminalMenu(
                f"No checksum found for the home recordbook: {home_recordbook.path}."
                f"\nDo you want to recreate it?"
                f"\nIf you don't have any reason to not do so, you should answer yes.",
                {
                    "Yes": (lambda: home_recordbook.write()),
                },
            ).show()
        elif device_recordbook.valid:
            if home_recordbook.invalid_reason == Validation.DOESNT_EXIST:
                copy_recordbook_callback(device_recordbook, home_recordbook)()
                return

            elif home_recordbook.invalid_reason == Validation.CORRUPTED:
                TerminalMenu(
                    f"The home recordbook's checksum doesn't correspond to its contents': {home_recordbook.path}."
                    f"\nHowever the device recordbook is valid: {device_recordbook.path}"
                    f"\nDo you want to copy the device recordbook content into the home recordbook?",
                    {
                        "Show diff": TerminalMenu.get_null_option(
                            lambda: subprocess.check_call(
                                ["diff", home_recordbook.path, device_recordbook.path]
                            )
                        ),
                        "Yes": copy_recordbook_callback(
                            device_recordbook, home_recordbook
                        ),
                    },
                ).show()
    else:
        # only home_recordbook is valid
        if device_recordbook.invalid_reason == Validation.DOESNT_EXIST:
            copy_recordbook_callback(home_recordbook, device_recordbook)
        elif device_recordbook.invalid_reason == Validation.NO_CHECKSUM_FILE:
            TerminalMenu(
                f"No checksum found for the device recordbook: {device_recordbook.path}."
                f"\nDo you want to recreate it?"
                f"\nIf you don't have any reason to not do so, you should answer yes.",
                {
                    "Yes": (lambda: device_recordbook.write()),
                },
            ).show()
        elif device_recordbook.invalid_reason == Validation.CORRUPTED:
            TerminalMenu(
                f"The device recordbook's checksum doesn't correspond to its contents': {device_recordbook.path}."
                f"\nHowever the home recordbook is valid: {home_recordbook.path}"
                f"\nDo you want to copy the home recordbook content into the device recordbook?",
                {
                    "Show diff": TerminalMenu.get_null_option(
                        lambda: subprocess.check_call(
                            ["diff", home_recordbook.path, device_recordbook.path]
                        )
                    ),
                    "Yes": copy_recordbook_callback(home_recordbook, device_recordbook),
                },
            ).show()
