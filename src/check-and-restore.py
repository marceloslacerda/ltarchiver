import shutil

import reedsolo

from common import *


def main():
    if len(sys.argv) != 3:
        error(f"usage: {sys.argv[0]} <backup> <destination>")
    backup_file_path = pathlib.Path(sys.argv[1])
    file_ok(backup_file_path)
    print(
        f"This program will check if there are any errors on the file {backup_file_path} and try to restore them if"
        f" necessary."
    )

    file_ok(recordbook_checksum_file_path)
    local_record_is_valid = subprocess.call(shlex.split(f"md5sum -c {recordbook_checksum_file_path}")) == 0
    backup_dir = backup_file_path.parent / "ltarchiver"
    backup_checksum_file = backup_dir / "checksum.txt"

    backup_record_is_valid = False
    if backup_checksum_file.is_file() and access(backup_checksum_file, R_OK):
        backup_record_is_valid = subprocess.call(shlex.split(f"md5sum -c {backup_checksum_file}")) == 0
    backup_file_checksum = get_file_checksum(backup_file_path)
    # check if file is in either record
    local_record = record_of_file(recordbook_path, backup_file_checksum)
    record_in_local = local_record is not None
    recordbook_backup_path = backup_dir / recordbook_file_name
    backup_record = record_of_file(recordbook_backup_path, backup_file_checksum)
    record_in_backup = backup_record is not None

    if record_in_local:
        if local_record_is_valid:
            record = local_record
            if not record_in_backup:
                try_copy_recordbook(recordbook_path, recordbook_backup_path)
            else:
                pass  # Nothing to do since backup already has a copy of the record
        else:
            if record_in_backup:
                if backup_record_is_valid:
                    record = backup_record
                    try_copy_recordbook(recordbook_backup_path, recordbook_path)
                else:
                    input("The file was found in both recordbooks but they don't match their checksums. Press CTR+C to"
                          " abort or Enter to try continuing with the restoration.")
            else:
                input("The file was found only in the local recordbook but its checksum doesn't match. Press CTR+C to"
                      " abort or Enter to try continuing with the restoration.")
    else:
        if record_in_backup:
            if backup_record_is_valid:
                record = backup_record
                try_copy_recordbook(recordbook_backup_path, recordbook_path)
            else:
                input("The file was only found in the backup recordbook but it doesn't match the checksum. Press CTR+C to"
                      " abort or Enter to try continuing with the restoration.")
        else:
            error(f"Neither {backup_file_path.name} or its checksum was found in the recordbooks")

    backup_md5 = subprocess.check_output(shlex.split(f"md5sum -c {backup_file_path}"), encoding="utf-8")
    if backup_md5 == record["checksum"]:
        print("No errors detected on the file. Beginning copy.")
        shutil.copyfile(backup_file_path, sys.argv[2])
        print("File was successfully copied. Goodbye.")
    else:
        # if not valid, attempt to repair
        #   if cant be repaired, warn user
        # show restored file path to user and return with success
        raise NotImplementedError()


def try_copy_recordbook(source, destination):
    destination_records = get_records(destination)
    source_records = get_records(source)
    destination_checksums = {record["checksum"] for record in destination_records}
    source_checksums = {record["checksum"] for record in source_records}
    destination_filename = {record["file_name"] for record in destination_records}
    source_filename = {record["file_name"] for record in source_records}
    has_more = False
    if destination_checksums - source_checksums:
        print(f"{destination} has checksums that {source} doesn't")
        has_more = True
    if destination_filename - source_filename:
        print(f"{destination} has files that {source} doesn't")
        has_more = True
    if has_more:
        while True:
            answer = input(
                f"Do you want to overwrite {destination} with the contents of {source} (yes/no/abort)?").lower()
            if answer == "yes":
                shutil.copy(source, destination)
                return
            elif answer == "no":
                return
            elif answer == "abort":
                exit(1)
            else:
                pass


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
        if parts[0] == "Deleted:":
            deleted = parts[1] == "true"
        if parts[0] == "Source:":
            source = parts[1]
        if parts[0] == "Destination:":
            destination = parts[1]
        if parts[0] == "Checksum:":
            checksum = parts[1]
        if parts[0] == "File-Name:":
            file_name = parts[1]


def record_of_file(recordbook_path: pathlib.Path, backup_file_checksum: str):
    for record in get_records(recordbook_path):
        if record["deleted"] and (
                record["checksum"] == backup_file_checksum or record["file_name"] == recordbook_path.name):
            return record


if __name__ == "__main__":
    main()
