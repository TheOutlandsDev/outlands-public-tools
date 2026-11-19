# Offline Socket Table Parser

Read saved Windows netstat output and Linux socket tables. The CLI normalizes
TCP and UDP records to JSON and reads only the file you supply.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/socket-table-parser-v0.1.0)
- [Usage guide and fictional input tables](SETUP.md)

The source edition keeps all three original Portable OpsKit parser cases, using
documentation addresses for tested endpoints. It adds checks for IPv6, UDP, and
malformed rows. The runtime uses the Python standard library. Qualification
covers Windows and Ubuntu with Python 3.12.16 and 3.15.2.
