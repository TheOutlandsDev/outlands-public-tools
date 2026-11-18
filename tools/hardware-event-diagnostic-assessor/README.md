# Offline Hardware Event Diagnostic Assessor

Assess supplied hardware events and telemetry snapshots. The engine
classifies active and historical findings, observes GPU PCIe replay counter
changes, and tracks recovery across successive samples.

The ZIP preserves the original diagnostic engine and data models byte-for-byte.
The five original test cases use fictional device details and timestamps.
The assessor uses Python's standard library and works with caller-supplied
data. Qualification covers Windows and Ubuntu with Python 3.12.16 and 3.15.2.

- [Download the source ZIP, checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/hardware-event-diagnostic-assessor-v0.1.0)
- [Run the fictional example and tests](SETUP.md)
