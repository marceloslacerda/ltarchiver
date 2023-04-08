import os
import shutil
import subprocess

import reedsolo

from datetime import datetime

from ltarchiver.common import *


def main():
    if len(sys.argv) != 3:
        error(f"usage: {sys.argv[0]} <source> <destination>")
    recordbook_dir.mkdir(parents=True, exist_ok=True)
    record = RECORD_PATH.open("wt")
    source = pathlib.Path(sys.argv[1]).absolute()
    destination = pathlib.Path(sys.argv[2]).absolute()
    bkp_dir = destination / "ltarchiver"
    file_ok(destination, False)
    sync_recordbooks(bkp_dir)
    file_ok(source)
    source_file_name = source.name
    try:
        md5 = get_file_checksum(source)
    except subprocess.SubprocessError as err:
        raise LTAError(f"Error calculating the md5 of source: {err}") from err
    try:
        file_not_exists(md5, source_file_name, destination / source_file_name)
    except FileNotFoundError:
        pass  # Triggered when the recordbook is not found. This usually means that it's the first time that ltarchiver
        # is running
        # if file were to exist on destination's recordbook it would have been already copied during sync
    blkid = ""
    try:
        blkid = get_device_uuid(destination)
    except subprocess.SubprocessError as err:
        error(f"Error trying to obtain the blkid of {destination}:\n{err}")
    record.write("\n")
    record.write("Item\n")
    record.write("Version: 1\n")
    record.write("Deleted: false\n")
    record.write(f"File-Name: {source_file_name}\n")
    record.write(f"Source: {source}\n")
    record.write(f"Destination: {blkid}\n")
    record.write(f"Bytes-per-chunk: {chunksize}\n")
    record.write(f"EC-bytes-per-chunk: {eccsize}\n")
    record.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
    record.write(f"Checksum-Algorithm: md5\n")
    record.write(f"Checksum: {md5}\n")
    destination_file_path = destination / source_file_name
    shutil.copyfile(source, destination_file_path)
    ecc_dir = bkp_dir / ecc_dir_name
    ecc_dir.mkdir(parents=True, exist_ok=True)
    ecc_file_path = ecc_dir / md5
    ecc_file = ecc_file_path.open("wb")
    ecc_bkp_file_path = pathlib.Path("/tmp") / md5
    ecc_bkp_file = ecc_bkp_file_path.open("wb")
    rsc = reedsolo.RSCodec(eccsize)
    source_file = source.open("rb")
    while True:
        ba = source_file.read(chunksize)
        if len(ba) == 0:
            break
        out = rsc.encode(ba)[-eccsize:]
        ecc_file.write(out)
        ecc_bkp_file.write(out)
    source_file.close()
    ecc_file.close()
    ecc_bkp_file.close()
    os.sync()
    if get_file_checksum(ecc_file_path) != get_file_checksum(ecc_bkp_file_path):
        raise LTAError("ECC files on source and destination devices do not match")
    os.remove(ecc_bkp_file_path)
    record.close()
    recordbook = recordbook_path.open("wt")
    recordbook.write(recordbook_path.read_text() + "\n" + RECORD_PATH.read_text())
    recordbook.close()
    shutil.copy(recordbook_path, bkp_dir)
    recordbook_checksum_file = recordbook_checksum_file_path.open("wt")
    out = subprocess.check_output(
        shlex.split(f"md5sum {recordbook_path}"), encoding="utf-8"
    )
    recordbook_checksum_file.write(out)
    recordbook_checksum_file.close()
    pathlib.Path(bkp_dir / "checksum.txt").write_text(
        out.split(" ", 1)[0] + " " + str(bkp_dir / "recordbook.txt")
    )
    os.sync()
    print("All done")


def get_device_uuid(destination):
    fs = (
        subprocess.check_output(
            shlex.split(f"df --output=source {destination}"), encoding="utf-8"
        )
        .split("\n")[1]
        .strip()
    )
    for p in pathlib.Path("/dev/disk/by-uuid/").iterdir():
        if pathlib.Path(fs) == (pathlib.Path("/dev") / p.readlink().name):
            return p.name
    raise LTAError(f"UUID not found for {destination}")


def file_not_exists(md5: str, file_name: str, destination_path: pathlib.Path):
    """The function fails if the file is in the recordbook and it's not deleted"""
    if not recordbook_path.exists():
        raise FileNotFoundError("The recordbook doesn't exist")
    record_no = 0
    for record in get_records(recordbook_path):
        if record.checksum == md5 and not record.deleted:
            if destination_path.exists():
                raise LTAError(
                    f"File was already stored in the record book\n{record.source=}\n{record.destination=}"
                )
            else:
                mark_record_as_deleted(record_no - 1)
        if record.file_name == file_name and not record.deleted:
            raise LTAError(
                f"Another file was already stored with that name{record.source=}\n{record.destination=}\n{record.file_name=}"
            )
        record_no += 1


def sync_recordbooks(bkp_dir: pathlib.Path):
    bkp_dir.mkdir(exist_ok=True, parents=True)
    dest_recordbook_path = bkp_dir / recordbook_file_name
    dest_recordbook_checksum_path = bkp_dir / "checksum.txt"
    if not recordbook_path.exists() and not dest_recordbook_path.exists():
        return  # Nothing to sync since neither exists
    elif not recordbook_path.exists() and dest_recordbook_path.exists():
        print("A record book exists on destination but not on origin")
        menu = TerminalMenu(
            "What would you like to be done?",
            {
                f"Copy the definition on {dest_recordbook_path} back to {recordbook_path}?": (
                    copy_recordbook_from_to(
                        dest_recordbook_path,
                        dest_recordbook_checksum_path,
                        recordbook_path,
                        recordbook_checksum_file_path,
                    )
                )
            },
        )
        menu.show()
    elif not dest_recordbook_path.exists():
        check_recordbook_md5(recordbook_checksum_file_path)
        shutil.copy(recordbook_path, dest_recordbook_path)
    else:
        if (
            dest_recordbook_checksum_path.read_text().split()[0]
            != recordbook_checksum_file_path.read_text().split()[0]
        ):
            print("Recordbooks checksum on source and destination differ.")
            decide_recordbooks(dest_recordbook_path, dest_recordbook_checksum_path)


if __name__ == "__main__":
    try:
        main()
    except LTAError as err:
        error(err.args[0])
