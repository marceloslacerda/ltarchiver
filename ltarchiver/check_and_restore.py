"""Restore command

Usage:
  ltarchiver-restore <backup> <destination>

"""

import os
import pathlib
import shutil
import subprocess
import shlex

from docopt import docopt

from ltarchiver import common

from ltarchiver.common import (
    error,
    file_ok,
    recordbook_checksum_file_path,
    recordbook_path,
    recordbook_file_name,
    get_file_checksum,
    get_records,
    recordbook_dir,
    record_of_file,
)


def run():
    arguments = docopt(__doc__)
    backup_file_path = pathlib.Path(arguments["<backup>"]).resolve()
    if pathlib.Path(arguments["<destination>"]).is_dir():
        destination_path = (
            pathlib.Path(arguments["<destination>"]) / backup_file_path.name
        )
    else:
        destination_path = pathlib.Path(arguments["<destination>"])
    restore(backup_file_path, destination_path)


def restore(backup_file_path: pathlib.Path, destination_path: pathlib.Path):
    destination_path = destination_path.resolve()
    if destination_path == backup_file_path:
        common.error("Backup and destination are the same.")
    file_ok(backup_file_path)
    print(
        f"This program will check if there are any errors on the file {backup_file_path} and try to restore them if"
        f" necessary.\nDestination: {destination_path}"
    )
    if not common.DEBUG:
        input("Press ENTER to continue. Press Ctrl+C to abort.")
    file_ok(recordbook_checksum_file_path)
    local_record_is_valid = (
        subprocess.call(shlex.split(f"md5sum -c {recordbook_checksum_file_path}")) == 0
    )
    dest_uuid, dest_root = common.get_device_uuid_and_root_from_path(backup_file_path)
    metadata_dir = (
        backup_file_path.parent / common.METADATA_DIR_NAME
        if common.DEBUG
        else dest_root / common.METADATA_DIR_NAME
    )
    backup_checksum_file = metadata_dir / "checksum.txt"

    backup_record_is_valid = False
    if backup_checksum_file.is_file() and os.access(backup_checksum_file, os.R_OK):
        backup_record_is_valid = (
            subprocess.call(shlex.split(f"md5sum -c {backup_checksum_file}")) == 0
        )
    backup_file_checksum = get_file_checksum(backup_file_path)
    # check if file is in either record
    local_record = record_of_file(
        recordbook_path, backup_file_checksum, backup_file_path
    )
    recordbook_backup_path = metadata_dir / recordbook_file_name
    backup_record = record_of_file(
        recordbook_backup_path, backup_file_checksum, backup_file_path
    )

    if local_record:
        if local_record_is_valid:
            record = local_record
            if not backup_record:
                try_copy_recordbook(recordbook_path, recordbook_backup_path)
            else:
                pass  # Nothing to do since backup already has a copy of the record
        else:
            if backup_record:
                if backup_record_is_valid:
                    record = backup_record
                    try_copy_recordbook(recordbook_backup_path, recordbook_path)
                else:
                    input(
                        "The file was found in both recordbooks but they (the recordbooks) don't match their checksums. Press CTR+C to"
                        " abort or Enter to try continuing with the restoration."
                    )
            else:
                input(
                    "The file was found only in the local recordbook but its checksum doesn't match. Press CTR+C to"
                    " abort or Enter to try continuing with the restoration."
                )
    else:
        if backup_record:
            if backup_record_is_valid:
                record = backup_record
                try_copy_recordbook(recordbook_backup_path, recordbook_path)
            else:
                input(
                    "The file was only found in the backup recordbook but it doesn't match the checksum. Press CTR+C to"
                    " abort or Enter to try continuing with the restoration."
                )
        else:
            error(
                f"Neither {backup_file_path.name} or its checksum was found in the recordbooks"
            )

    backup_md5 = get_file_checksum(backup_file_path)
    original_ecc_file_path = (metadata_dir / "ecc") / record.checksum
    original_ecc_checksum = get_file_checksum(original_ecc_file_path)
    if backup_md5 == record.checksum and original_ecc_checksum == record.ecc_checksum:
        print("No errors detected on the file. Beginning copy.")
        shutil.copyfile(backup_file_path, destination_path)
        print("File was successfully copied. Goodbye.")
        exit(0)
    elif backup_md5 == record.checksum and original_ecc_checksum != record.ecc_checksum:
        print(
            "Only the ecc differs from what's stored in the recordbook. The fastest way to go is to call the restore"
            " routine on this file again."
        )
        exit(1)
    else:
        print(
            "Checksum doesn't match. Attempting to restore the file onto destination."
        )
        new_ecc_file_path = recordbook_dir / "temp_ecc.bin"
        subprocess.check_call(
            [
                "c-ltarchiver/out/ltarchiver_restore",
                str(backup_file_path),
                str(destination_path),
                str(original_ecc_file_path),
                str(new_ecc_file_path),
            ]
        )
        print("Checking if the restoration succeeded...")
        new_ecc_checksum = get_file_checksum(new_ecc_file_path)
        destination_checksum = get_file_checksum(destination_path)
        failed = False
        if new_ecc_checksum != record.ecc_checksum:
            print("The restored ECC doesn't match what was expected.")
            failed = True
        if destination_checksum != record.checksum:
            print("The file doesn't match what was expected.")
            failed = True
        if failed:
            print(
                "Sorry! Failed to restore the requested file. You are on your own now."
            )
            exit(1)
        else:
            subprocess.check_call(["cp", new_ecc_file_path, original_ecc_file_path])
            os.remove(new_ecc_file_path)
            print("Restoration successful!")
            exit(0)


def try_copy_recordbook(source, destination):
    destination_records = get_records(destination)
    source_records = get_records(source)
    destination_checksums = {record.checksum for record in destination_records}
    source_checksums = {record.checksum for record in source_records}
    destination_filename = {record.file_name for record in destination_records}
    source_filename = {record.file_name for record in source_records}
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
                f"Do you want to overwrite {destination} with the contents of {source} (yes/no/abort)?"
            ).lower()
            if answer == "yes":
                shutil.copy(source, destination)
                return
            elif answer == "no":
                return
            elif answer == "abort":
                exit(1)
            else:
                pass


if __name__ == "__main__":
    run()
