# Offline Player Telemetry Snapshot Normalizer

Convert a saved portal or collector JSON snapshot into point records with
a server ID, state, population, capacity, and metric kind. A caller-supplied
mapping chooses which source IDs to keep and how to label their counts.
The CLI uses the Python standard library and reads local files.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/player-telemetry-snapshot-normalizer-v0.1.0)
- [Usage guide and fictional snapshots](SETUP.md)

The tests preserve the original availability-only and player-versus-connection
cases. The qualification workflow targets Windows and Ubuntu with Python
3.12.16 and 3.15.2.
