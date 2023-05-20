import pathlib
import subprocess
import sys

from ltarchiver import common


def refresh(device_uuid: str, device_root: pathlib.Path):
    print(f"Attempting to refresh the device {device_uuid}.")
    device_metadata_dir = device_root / "ltarchiver"
    device_recorbook = common.RecordBook(
        device_metadata_dir / common.recordbook_file_name,
        device_metadata_dir / "checksum.txt",
    )
    home_recordbook = common.RecordBook(
        common.recordbook_path, common.recordbook_checksum_file_path
    )
    common.validate_and_recover_recorbooks(home_recordbook, device_recorbook)
    home_recordbook.merge(device_recorbook)
    device_recorbook.records = home_recordbook.records
    device_recorbook.write()
    for record in home_recordbook.get_records_by_uuid(device_uuid):
        original_file_path = record.file_path(device_root)
        original_ecc_path = record.file_path(device_root)
        recovery_file_path = original_file_path.with_stem(".rec")
        recovery_ecc_path = original_ecc_path.with_stem(".rec")
        validation = record.get_validation()
        if validation == common.Validation.DOESNT_EXIST or validation == common.Validation.ECC_DOESNT_EXIST:
            print(f"{validation}. Skipping this file.")
            continue
        elif validation != common.Validation.VALID:
            print(f"{validation}. Attempting to recover.")
            subprocess.check_call(
                [
                    "c-ltarchiver/out/ltarchiver_restore",
                    str(original_file_path),
                    str(recovery_file_path),
                    str(original_ecc_path),
                    str(recovery_ecc_path),
                ]
            )
        else:
            print(f"No errors found with {record.file_name}. Copying to new location.")
            subprocess.check_call(["cp", original_file_path, recovery_file_path])
            subprocess.check_call(["cp", original_ecc_path, recovery_ecc_path])
        print("Success. Moving the created files to the original location.")
        subprocess.check_call(["mv", recovery_file_path, original_file_path])
        subprocess.check_call(["mv", recovery_ecc_path, original_ecc_path])
        print(f"Finished processing {record.file_name}.")


def run():
    if sys.argv != 2:
        common.error(f"usage: {sys.argv[0]} <path_to_to_device_to_refresh>")
    else:
        device_path = pathlib.Path(sys.argv[1])
        if device_path.exists():
            uuid, root = common.get_device_uuid_and_root_from_path(device_path)
            if common.DEBUG:
                refresh(uuid, device_path)
            else:
                refresh(uuid, root)
        else:
            common.error(f"{device_path} doesn't exist!")
