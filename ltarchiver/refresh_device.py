import pathlib
import sys

from ltarchiver import common


def refresh(device_uuid: str, device_root: pathlib.Path):
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
        if record.is_valid():
            # todo restore to bkp_location
            pass
        else:
            # todo cp file bkp_location
            pass
        # mv bkp_location file


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
