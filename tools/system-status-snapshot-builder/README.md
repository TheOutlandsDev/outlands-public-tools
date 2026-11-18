# Offline System Status Snapshot Builder

Build a status snapshot from an application version, environment, server time,
and optional last-ingestion timestamp. The builder formats timestamps in
America/New_York and marks missing ingestion data as unavailable.

- [Download the source ZIP, checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/system-status-snapshot-builder-v0.1.0)
- [Run the fictional example](SETUP.md)

The source ZIP preserves the original Python implementation and all three
original tests byte-for-byte. Qualification covers Windows and Ubuntu with
CPython 3.12.16 and 3.15.2 using the pinned tzdata 2026.6 wheel. The builder
uses supplied values and runs locally.
