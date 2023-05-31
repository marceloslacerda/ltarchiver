# Ltarchiver

Ltarchiver is a backup program for long-term storage of files. Files are
stored as they are into the destination directory (no fancy formats that require decoding).
The difference between ltarchiver and a simple `cp` is that ltarchiver also keeps track of
where you stored what its checksum and also allows you to recover your file if gets corrupted.

## Rationale

Ltarchiver was built to satisfy my desire to have a tool that could not only store files on
old unused media (mainly old hard-drives that I have lying around) without the fear
that the files will suffer [bitrot](https://en.wikipedia.org/wiki/Data_degradation), and on the event that it does, to be able to
restore the data.

## Usage

To archive a file use the `store` command. For restore use the `check_and_restore` command.

### Store usage

```shell
ltarchiver-store [--non-interactive] <source file> <destination_directory>
```


### Restore usage

```shell
ltarchiver-restore <backup_file> <destination_directory>
```

```shell
ltarchiver-refresh <destination_directory>
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

### What about btrfs? 

btrfs comes with error recovery capabilities, but it's
only useful for online-storage setups because btrfs keeps a checksum of each file
and if it detects a corruption on the stored data it will revert the file to a
previous correct version. That means that for the file-system to be able to
use its self-healing capabilities, several versions of the same file must be stored.
That wouldn't occour if the media you are using to store your backup is one that you
keep stowed away and only plugs in when you need to store new files.

But even if you consider btrfs in an online storage scenario you would only be able
to revert to a previous know version of a file. Not the current one.

## Installation instructions

1. Clone this repository.
2. `cd` to the created directory.
3. Install the program with `pip`.

```shell
git clone https://github.com/marceloslacerda/ltarchiver.git
cd ltarchiver
pip install .
```

You might want to install this project inside a 
[virtual environment](https://docs.python.org/3/library/venv.html)
or to force 
[pip to do a user install](https://stackoverflow.com/questions/42988977/what-is-the-purpose-of-pip-install-user).

## License

Licensed under
[GPL 2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).
Check the license of [c-ltarchiver](https://github.com/marceloslacerda/c-ltarchiver)
for more information on [schifra's dependency](https://github.com/ArashPartow/schifra).