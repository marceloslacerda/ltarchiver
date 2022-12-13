import pathlib

recordbook_file_name = "recordbook.txt"
recordbook_dir = pathlib.Path.home() / ".ltarchiver"
recordbook_path = recordbook_dir / recordbook_file_name
recordbook_checksum_file_path = recordbook_dir / "checksum.txt"
RECORD_PATH = (recordbook_dir / "new_transaction.txt")
ecc_dir_name = "ecc"
chunksize = 128  # bytes
eccsize = 8  # bytes
