# Offline Scheduled Task Preview

Read saved task records and preview warning times, expected restarts,
running tasks, and maintenance status. The CLI prints JSON and uses the
Python standard library. Supply a fixed UTC display offset to reproduce
the same preview across machines.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/scheduled-task-preview-v0.1.0)
- [Usage guide and fictional task records](SETUP.md)

The two original cases are preserved with fictional task labels. The
release adds checks for disabled tasks, malformed timestamps, and date
rollover. Qualification covers Windows and Ubuntu with Python 3.12.16
and 3.15.2.
