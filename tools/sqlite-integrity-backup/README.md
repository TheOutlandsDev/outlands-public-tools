# Offline SQLite Integrity and Backup Tool

Run SQLite integrity and foreign-key checks on a file you select. Create
a consistent backup, validate the copy, and calculate its SHA-256 checksum.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/sqlite-integrity-backup-v0.1.0)
- [Usage guide and fictional example](SETUP.md)

The source edition preserves Portable OpsKit's SQLite API and both original
tests. The default backup uses atomic publication to protect existing destination
files. The CLI uses the Python standard library. The qualification workflow
targets Windows and Ubuntu with Python 3.12.16 and 3.15.2.
