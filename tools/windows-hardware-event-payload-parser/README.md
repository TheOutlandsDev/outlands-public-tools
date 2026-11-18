# Offline Windows Hardware Event Payload Parser

Convert saved Windows hardware event JSON into structured event records.
The parser keeps input order, assigns categories and severities, and cleans
message formatting. It uses the Python standard library and runs on Windows
and Ubuntu with saved files.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/windows-hardware-event-payload-parser-v0.1.0)
- [Usage guide and fictional example](SETUP.md)

The two original tests use fictional event details. The original parser's
classification rules are preserved. Records with unrepresentable numeric IDs
are skipped along with other malformed records.
