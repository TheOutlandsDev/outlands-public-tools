# Offline Availability Evidence Exporter

Create a short safety summary and deterministic SHA-256 digests from
saved availability telemetry. The summary reports disk free space, peak
CPU and GPU temperatures, a recorded quarantine state, and selected
hardware-event categories. The exporter uses Python's standard library.

- [Source ZIP, checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/availability-evidence-exporter-v0.1.0)
- [Usage guide and fictional snapshot](SETUP.md)

Both original cases are preserved with fictional input. Qualification covers
Windows and Ubuntu with Python 3.12.16 and 3.15.2.
