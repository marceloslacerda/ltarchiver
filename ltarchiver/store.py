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
    blkid = ""
    try:
        blkid = get_device_uuid(destination)
    except subprocess.SubprocessError as err:
        error(f"Error trying to obtain the blkid of {destination}:\n{err}")
    record.write("\n")
    record.write("Item\n")
    record.write("Version: 1\n")
    record.write("Deleted: false\n")
    source_file_name = source.name
    record.write(f"File-Name: {source_file_name}\n")
    record.write(f"Source: {source}\n")
    record.write(f"Destination: {blkid}\n")
    record.write(f"Bytes-per-chunk: {chunksize}\n")
    record.write(f"EC-bytes-per-chunk: {eccsize}\n")
    record.write(f"Timestamp: {datetime.now().isoformat()}\n")
    md5 = ""
    try:
        md5 = get_file_checksum(source)
    except subprocess.SubprocessError as err:
        error(f"Error calculating the md5 of source: {err}")
    file_not_exists(md5, source_file_name)
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
        error("ECC files on source and destination devices do not match")
    os.remove(ecc_bkp_file_path)
    record.close()
    recordbook = recordbook_path.open("wt")
    recordbook.write(recordbook_path.read_text() + "\n" + RECORD_PATH.read_text())
    recordbook.close()
    shutil.copy(recordbook_path, bkp_dir)
    recordbook_checksum_file = recordbook_checksum_file_path.open("wt")
    out = subprocess.check_output(
        shlex.split(f"md5sum {recordbook_path}"), encoding='utf-8'
    )
    recordbook_checksum_file.write(out)
    recordbook_checksum_file.close()
    pathlib.Path(bkp_dir / "checksum.txt").write_text(out.split(' ', 1)[0] + ' ' + str(bkp_dir / "recordbook.txt"))
    os.sync()
    print("All done")


def get_device_uuid(destination):
    fs = (
        subprocess.check_output(shlex.split(f"df --output=source {destination}"), encoding="utf-8")
        .split("\n")[1]
        .strip()
    )
    for p in pathlib.Path("/dev/disk/by-uuid/").iterdir():
        if pathlib.Path(fs) == (pathlib.Path("/dev") / p.readlink().name):
            return p.name
    raise LTAError(f"UUID not found for {destination}")


def file_not_exists(md5: str, file_name: str):
    if not recordbook_path.exists():
        raise FileNotFoundError("The recordbook doesn't exist")
    for record in get_records(recordbook_path):
        if record["checksum"] == md5 and not record["deleted"]:
            raise LTAError(
                f"File was already stored in the record book\n{record['source']=}\n{record['destination']=}"
            )
        if record["file_name"] == file_name and not record["deleted"]:
            raise LTAError(
                f"Another file was already stored with that name{record['source']=}\n{record['destination']=}\n{record['file_name']=}")


def check_recordbook_md5(recordbook_checksum: pathlib.Path):
    if not recordbook_checksum.exists() or recordbook_checksum.stat().st_size == 0:
        raise FileNotFoundError(f"Recordbook checksum file {recordbook_checksum} not found or empty")
    try:
        subprocess.check_call(shlex.split(f"md5sum -c {recordbook_checksum}"))
    except subprocess.CalledProcessError as err:
        raise LTAError(
            f"The recordbook checksum file {recordbook_checksum} doesn't match what's stored. Please validate it and retry."
        ) from err


def sync_recordbooks(bkp_dir: pathlib.Path):
    if not (bkp_dir / "checksum.txt").exists():
        return
    check_recordbook_md5(recordbook_checksum_file_path)
    bkp_dir.mkdir(exist_ok=True)
    dest_recordbook_path = bkp_dir / recordbook_file_name
    if not recordbook_path.exists() and not dest_recordbook_path.exists():
        return
    elif not recordbook_path.exists() and dest_recordbook_path.exists():
        error("A record book exists on destination but not on origin")
    elif not dest_recordbook_path.exists():
        shutil.copy(recordbook_path, dest_recordbook_path)
    else:
        check_recordbook_md5(bkp_dir / "checksum.txt")
        dest_size = dest_recordbook_path.stat().st_size
        source_size = recordbook_path.stat().st_size
        if dest_size < source_size:
            shutil.copy(recordbook_path, dest_recordbook_path)
        elif dest_size > source_size:
            shutil.copy(dest_recordbook_path, recordbook_path)


if __name__ == "__main__":
    try:
        main()
    except LTAError as err:
        error(err.args[0])
