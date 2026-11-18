# Offline Crash Telemetry Report

Summarize the latest row in a saved SQLite telemetry export alongside
saved sensor, thermal guard, and quarantine JSON. The report includes
sample age, peak temperatures, and the state recorded in those files.
The tool uses the Python standard library and prints to stdout.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/crash-telemetry-report-v0.1.0)
- [Usage guide and fictional example](SETUP.md)

The original end-to-end test is preserved with fictional data. SQLite input
is a closed rollback-journal export. Qualification covers Windows and Ubuntu
with Python 3.12.16 and 3.15.2.
