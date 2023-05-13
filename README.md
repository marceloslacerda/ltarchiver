# Ltarchiver

Ltarchiver is a backup program for long-term storage of files. Files are
stored as they are into the destination directory (no fancy formats that require decoding).
The difference between ltarchiver and a simple `cp` is that ltarchiver also keeps track of
where you stored what its checksum and also allows you to recover your file if it's corrupted.

## Rationale

Ltarchiver was built to satisfy my desire to have a tool that could not only store files on
old unused media (mainly old hard-drives that I have lying around) without the fear
that the files will suffer bitrot, and on the event that it does, to be able to
restore the data.

## Usage

To archive a file use the `store` command. For restore use the `check_and_restore` command.

### Store usage

```shell
python3 -m ltarchiver.store <source file> <destination_directory>
```

### Restore usage

```shell
python3 -m ltarchiver.check_and_restore <backup_file> <destination_directory>
```

## How does it work?

Whenever you use the `store` command ltarchiver creates an entry in its book record to
know the checksum of the file, and where it was stored. When writing the file to
the destination ltarchiver also writes an ECC file that, if required by
the `check_and_restore` command, will be used to restore the file to its original
contents.

Currently the ECC file is about 1% of the size of original file.
That allows for about 0.5% of the file (the ECC and the original files are added
in this count) to be corrupted, assuming that the corruption is evenly spread across the backup media.

Of course not all corruptions can be expected to happen evenly, a disk scratch in a CD would likely
corrupt several bytes that are close together while leaving many others completely unscathed.
For this reason ltarchiver is not recommended for optical media. Not that it matters
since optical media already employs some method of error recovery on damage.

Another problem that ltarchiver can't deal with is critical failures. For that reason
ltarchiver should not be used with solid state media as those devices often
fail completely. If critical failure is a concern for one reason or the other
the user should opt for some kind of RAID setup.


## Installation instructions

TBA

## License

Licensed under [GPL 2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).