# Offline Telemetry Alert Evaluator

Evaluate supplied telemetry snapshots for sustained warning and critical
threshold crossings. The evaluator tracks active alerts, limits repeat
emissions, and clears alerts when readings return to normal. Temperature
evaluation excludes static sensor limits.

The ZIP preserves the original evaluator, configuration, data models, and
all three alert and temperature-filter tests byte-for-byte. The runtime
uses the Python standard library. Qualification covers Windows and Ubuntu
with Python 3.12.16 and 3.15.2, using synthetic snapshots.

- [Download the source ZIP, checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/telemetry-alert-evaluator-v0.1.0)
- [Run the synthetic example and tests](SETUP.md)
