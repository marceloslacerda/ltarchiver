import os
import shlex
import shutil
import subprocess
import pathlib
import datetime
import optparse

import yesno

from ltarchiver import common


def store(source: pathlib.Path, destination: pathlib.Path, non_interactive: bool):
    common.recordbook_dir.mkdir(parents=True, exist_ok=True)
    if source == destination:
        raise common.LTAError("Source and destination are the same.")
    dest_uuid, dest_root = common.get_device_uuid_and_root_from_path(destination)
    if not common.DEBUG:
        destination = dest_root
    metadata_dir = destination / common.METADATA_DIR_NAME
    common.file_ok(destination, False)
    sync_recordbooks(metadata_dir)
    try:
        common.file_ok(source)
        original_source = source
    except common.LTAError as err:
        if err.args[1] == common.FileValidation.IS_DIRECTORY:
            print(f"{source} is a directory.")
            if non_interactive or yesno.input_until_bool(
                "Do you want it turned into a tar file before archiving?"
            ):
                original_source = source
                source = tar_directory(source)
            else:
                raise common.LTAError("Cannot archive an uncompressed directory.")
        else:
            raise

    source_file_name = source.name
    print(f"Backup of: {source}\nTo: ", destination)
    if not non_interactive:
        input("Press ENTER to continue. Press Ctrl+C to abort.")
    if not destination.is_dir():
        print(destination, "is not a directory! Aborting.")
        exit(1)
    try:
        print("Calculating checksum", datetime.datetime.now())
        md5 = common.get_file_checksum(source)
        print("Checksum calculated", datetime.datetime.now())
    except subprocess.SubprocessError as err:
        raise common.LTAError(f"Error calculating the md5 of source: {err}") from err
    destination_file_path = destination / source_file_name
    try:
        file_not_exists_in_recordbook(md5, source_file_name, destination_file_path)
    except FileNotFoundError:
        pass
        # Triggered when the recordbook is not found. This usually means that it's the
        # first time that ltarchiver is running if file were to exist on destination's
        # recordbook it would have been already copied during sync
    if destination_file_path.exists():
        raise common.LTAError(
            f"{source_file_name} is not in the recordbook but {destination_file_path} already exists. Aborting!"
        )
    ecc_dir = metadata_dir / common.ecc_dir_name
    ecc_dir.mkdir(parents=True, exist_ok=True)
    ecc_file_path = ecc_dir / md5

    print("Encoding and storing file", datetime.datetime.now())
    subprocess.check_call(
        [
            "c-ltarchiver/out/ltarchiver_store",
            str(source),
            str(destination_file_path),
            str(ecc_file_path),
        ]
    )
    os.sync()
    record = common.Record(
        timestamp=datetime.datetime.now(),
        file_name=source_file_name,
        source=source,
        destination=dest_uuid,
        checksum=md5,
        ecc_checksum=common.get_file_checksum(ecc_file_path),
    )
    record.write(common.RECORD_PATH)
    try:
        old_text = common.recordbook_path.read_text() + "\n"
    except FileNotFoundError:
        old_text = ""
    recordbook = common.recordbook_path.open("wt")
    recordbook.write(old_text + common.RECORD_PATH.read_text())
    recordbook.close()
    shutil.copy(common.recordbook_path, metadata_dir)
    recordbook_checksum_file = common.recordbook_checksum_file_path.open("wt")
    out = subprocess.check_output(
        shlex.split(f"md5sum {common.recordbook_path}"), encoding="utf-8"
    )
    recordbook_checksum_file.write(out)
    recordbook_checksum_file.close()
    pathlib.Path(metadata_dir / "checksum.txt").write_text(
        out.split(" ", 1)[0] + " " + str(metadata_dir / "recordbook.txt")
    )
    os.sync()
    if original_source != source:
        # the original and the new source are different when a directory was tarred
        # so the source (the tarred file) can (and should!) be safely removed
        common.remove_file(source)
        source = original_source
    if non_interactive or yesno.input_until_bool(
        f"Do you want to remove the source?\n{source}"
    ):
        common.remove_file(source)
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
    raise common.LTAError(f"UUID not found for {destination}")


def file_not_exists_in_recordbook(
    md5: str, file_name: str, destination_path: pathlib.Path
):
    """The function fails if the file is in the recordbook and it's not deleted"""
    if not common.recordbook_path.exists():
        raise FileNotFoundError("The recordbook doesn't exist")
    record_no = 0
    for record in common.get_records(common.recordbook_path):
        if record.checksum == md5 and not record.deleted:
            if destination_path.exists():
                raise common.LTAError(
                    f"File was already stored in the record book\n{record.source=}\n{record.destination=}"
                )
            else:
                common.mark_record_as_deleted(record_no - 1)
        if record.file_name == file_name and not record.deleted:
            raise common.LTAError(
                f"Another file was already stored with that name{record.source=}\n{record.destination=}\n{record.file_name=}"
            )
        record_no += 1


def sync_recordbooks(bkp_dir: pathlib.Path):
    bkp_dir.mkdir(exist_ok=True, parents=True)
    dest_recordbook_path = bkp_dir / common.recordbook_file_name
    dest_recordbook_checksum_path = bkp_dir / "checksum.txt"
    if not common.recordbook_path.exists() and not dest_recordbook_path.exists():
        return  # Nothing to sync since neither exists
    elif not common.recordbook_path.exists() and dest_recordbook_path.exists():
        print("A record book exists on destination but not on origin")
        menu = common.TerminalMenu(
            "What would you like to be done?",
            {
                f"Copy the definition on {dest_recordbook_path} back to {common.recordbook_path}?": (
                    common.copy_recordbook_from_to(
                        dest_recordbook_path,
                        dest_recordbook_checksum_path,
                        common.recordbook_path,
                        common.recordbook_checksum_file_path,
                    )
                )
            },
        )
        menu.show()
    elif not dest_recordbook_path.exists():
        common.check_recordbook_md5(common.recordbook_checksum_file_path)
        shutil.copy(common.recordbook_path, dest_recordbook_path)
    else:
        if (
            dest_recordbook_checksum_path.read_text().split()[0]
            != common.recordbook_checksum_file_path.read_text().split()[0]
        ):
            print("Recordbooks checksum on source and destination differ.")
            common.decide_recordbooks(
                dest_recordbook_path, dest_recordbook_checksum_path
            )


def tar_directory(path: pathlib.Path) -> pathlib.Path:
    """Tar a directory and return the path to the tarred file."""
    parent = path.parent
    tarred = path.with_suffix(".tar")
    subprocess.check_call(["tar", "-C", parent, "-cvf", tarred, path.name])
    return tarred


def get_option_parser():
    parser = optparse.OptionParser(
        "usage: %prog [options] <source_file>... <destination_directory>"
    )
    parser.add_option(
        "--non-interactive",
        action="store_true",
        help="disable most confirmation dialogs",
    )
    return parser


def run():
    parser = get_option_parser()
    (options, args) = parser.parse_args()
    if len(args) < 2:
        parser.print_help()
        common.error("Either the source or the destination was not provided. Aborting.")
    destination = pathlib.Path(args[-1]).resolve()
    sources = {pathlib.Path(source).resolve() for source in args[:-1]}
    for source in sources:
        try:
            store(source, destination, options.non_interactive or common.DEBUG)
        except common.LTAError as err_:
            common.error(err_.args[0])


if __name__ == "__main__":
    run()
