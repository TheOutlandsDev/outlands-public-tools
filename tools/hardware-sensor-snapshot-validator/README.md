# Offline Hardware Sensor Snapshot Validator

Check the freshness and shape of a saved sensor snapshot, then return valid
temperature readings when the snapshot contains at least two CPU
temperature entries. The validator uses the Python standard library.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/hardware-sensor-snapshot-validator-v0.1.0)
- [Usage guide and fictional snapshot](SETUP.md)

The release preserves all three original cases and the temperature
filtering rules. The administrator flag is a declaration in the supplied
file. Qualification covers Windows and Ubuntu with Python 3.12.16 and 3.15.2.
