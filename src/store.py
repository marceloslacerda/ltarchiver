import os
import pathlib
from os import access, R_OK, W_OK

import reedsolo

from common import *
from subprocess import check_output, check_call
from datetime import datetime

import shlex
import subprocess
import sys
import shutil


def check_recordbook(path: pathlib.Path):
    if not path.exists() or path.stat().st_size == 0:
        return
    if check_call(f"md5sum -c {path}"):
        error(f"The checksum of the file {path} doesn't match what's stored. Please validate it and retry.")


def sync_recordbooks(bkp_dir: pathlib.Path):
    check_recordbook(recordbook_path)
    bkp_dir.mkdir(exist_ok=True)
    dest_recordbook_path = bkp_dir / recordbook_file_name
    if not recordbook_path.exists() and not dest_recordbook_path.exists():
        return
    elif not recordbook_path.exists() and dest_recordbook_path.exists():
        error("A record book exists on destination but not on origin")
    elif not dest_recordbook_path.exists():
        shutil.copy(recordbook_path, dest_recordbook_path)
    else:
        check_recordbook(dest_recordbook_path)
        dest_size = dest_recordbook_path.stat().st_size
        source_size = recordbook_path.stat().st_size
        if dest_size < source_size:
            shutil.copy(recordbook_path, dest_recordbook_path)
        elif dest_size > source_size:
            shutil.copy(dest_recordbook_path, recordbook_path)


def main():
    if len(sys.argv) != 3:
        error(f"usage: {sys.argv[0]} <source> <destination>")
        exit(1)

    recordbook_dir.mkdir(parents=True, exist_ok=True)
    record = RECORD_PATH.open('wt')
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
    record.write(f"Source: {source}\n")
    record.write(f"Destination: {blkid}\n")
    record.write(f"Bytes per chunk: {chunksize}\n")
    record.write(f"EC bytes per chunk: {eccsize}\n")
    record.write(f"Timestamp: {datetime.now().isoformat()}\n")
    md5 = ""
    try:
        md5 = get_file_checksum(source)
    except subprocess.SubprocessError as err:
        error(f"Error calculating the md5 of source: {err}")
    file_not_exists(md5)
    record.write(f"Checksum Algorithm: md5\n")
    record.write(f"Checksum: {md5}\n")
    destination_file_path = destination / source.name
    shutil.copyfile(source, destination_file_path)
    # this is probably pointless cause most archiving formats (zip, tar etc) do some form o checksumming
    #  new_md5 = get_file_checksum(destination_file_path)
    #  if new_md5 != md5:
    #      error("The checksum of the source and destination differ. Please retry or test the device for errors.")
    #   os.sync()
    ecc_dir = bkp_dir / ecc_dir_name
    ecc_dir.mkdir(parents=True, exist_ok=True)
    ecc_file_path = ecc_dir / md5
    ecc_file = ecc_file_path.open("wb")
    ecc_bkp_file_path = pathlib.Path("/tmp") / md5
    ecc_bkp_file = ecc_bkp_file_path.open("wb")
    rsc = reedsolo.RSCodec(eccsize)
    source_file = source.open("rb")
    while True:
        ba = source_file.read(64)
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
    check_call(shlex.split(f"md5sum {recordbook_path}"), stdout=recordbook_checksum_file)
    recordbook_checksum_file.close()
    shutil.copy(recordbook_checksum_file_path, bkp_dir)
    os.sync()
    print("All done")


def get_device_uuid(destination):
    fs = check_output(shlex.split(f"df --output=source {destination}"), encoding="utf-8").split("\n")[1].strip()
    for p in pathlib.Path("/dev/disk/by-uuid/").iterdir():
        if pathlib.Path(fs) == (pathlib.Path("/dev") / p.readlink().name):
            return p.name
    raise Exception(f"UUID not found for {destination}")


def get_file_checksum(source: pathlib.Path):
    return subprocess.check_output(shlex.split(f"md5sum {source}"), encoding="utf-8").split()[0]


def file_not_exists(md5: str):
    if not recordbook_path.exists():
        return
    recordbook = recordbook_path.open("r")
    count = 0
    source = ""
    destination = ""
    deleted = False
    for line in recordbook:
        line = line.strip()
        count += 1
        parts = line.split()
        if parts[0] == "Item":
            deleted = False
        if parts[0] == "Deleted:":
            deleted = parts[1] == "true"
        if parts[0] == "Source:":
            source = line
        if parts[0] == "Destination:":
            destination = line
        if parts[0] == "Checksum:" and parts[1] == md5 and not deleted:
            error(f"File was already stored in the record book\n{line}\n{source}\n{destination}")


def error(msg: str):
    print(msg, file=sys.stderr)
    exit(1)


def file_ok(path: pathlib.Path, source=True):
    if not path.exists():
        error(f"File {path} does not exist")
    if source:
        if not path.is_file():
            error(f"Path {path} does not point to a file")
        if not access(path, R_OK):
            error(f"File {path} is not readable")
    else:
        if not path.is_dir():
            error(f"Path {path} does not point to a file")
        if not access(path, W_OK):
            error(f"File {path} is not writable")


if __name__ == '__main__':
    main()
