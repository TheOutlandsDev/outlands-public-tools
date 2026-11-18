# Offline SQLite Telemetry Store

Write supplied telemetry snapshots, alerts, and hardware events to a local
SQLite database. The store uses write-ahead logging (WAL) and reports when
the preceding store session ended without a clean close. The runtime uses
the Python standard library.

- [Download the source ZIP, checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/sqlite-telemetry-store-v0.1.0)
- [Run a fictional snapshot in a temporary database](SETUP.md)

Qualification covers Windows and Ubuntu with Python 3.12.16 and 3.15.2.
The storage code and supporting models are byte-for-byte copies of the
originals. Both original test cases are preserved with fictional fixture
details.

Use a dedicated local database. The store saves metadata supplied in
snapshots and alerts and prunes expired records. The package contains
source and tests with fictional inputs.
