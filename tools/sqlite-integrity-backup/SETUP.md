# Use the Offline SQLite Integrity and Backup Tool

## Verify and extract the download

Get the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/sqlite-integrity-backup-v0.1.0).
Compare the calculated ZIP hash with its entry in `SHA256SUMS.txt`
before extracting into a fresh directory.

PowerShell

```powershell
Get-FileHash .\sqlite-integrity-backup-0.1.0.zip -Algorithm SHA256
Expand-Archive .\sqlite-integrity-backup-0.1.0.zip .\sqlite-demo
Set-Location .\sqlite-demo\sqlite-integrity-backup-0.1.0
```

Ubuntu shell

```sh
sha256sum sqlite-integrity-backup-0.1.0.zip
unzip sqlite-integrity-backup-0.1.0.zip -d sqlite-demo
cd sqlite-demo/sqlite-integrity-backup-0.1.0
```

Use Python 3.12 or 3.15 from the extracted directory. Substitute `python3`
if that is the name of your interpreter.

## Run the fictional example

```text
python -B examples/create_sample.py ../fictional-source.sqlite
python -B -m opskit sqlite check ../fictional-source.sqlite
python -B -m opskit sqlite check ../fictional-source.sqlite --full
python -B -m opskit sqlite backup ../fictional-source.sqlite ../fictional-backup.sqlite
python -B -m opskit sqlite check ../fictional-backup.sqlite --full
```

The first check uses `quick_check`. Use `--full` for `integrity_check`.
Both commands also report foreign-key violations. On a successful backup,
the report gives the destination, byte count, SHA-256, and validation result.

## Use a local database

Pass a database file to `check`. For `backup`, also specify a destination
in an existing local directory. Choose a new destination by default.
The backup uses SQLite's backup API, validates the staged copy, and publishes
the file only after validation. The copy uses rollback journaling so it can
be opened as a single database file. Default publication needs a destination
filesystem that supports hard links. An existing destination or one that appears
during backup is preserved.

Use `--force` only when you intend to replace an existing destination.
Close applications using that destination before replacing it.

The source connection uses SQLite's read-only, query-only mode. The backup
includes committed changes in a write-ahead log. The WAL fixture verifies
that the main database and its existing WAL keep identical bytes. SQLite
can update the shared-memory file or create coordination files when a
WAL-mode database lacks them.

| Exit code | Result |
| --- | --- |
| `0` | Integrity check passed or the verified backup was published |
| `1` | The integrity or foreign-key check reported findings |
| `2` | The command could not be completed |

## Verify the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The release includes fresh-extraction validation records for Windows
and Ubuntu with Python 3.12.16 and 3.15.2.
