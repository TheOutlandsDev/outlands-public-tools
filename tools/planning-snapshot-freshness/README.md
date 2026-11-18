# Offline Planning Snapshot Freshness Reporter

Classify planning timestamps as current, fresh, aging, stale, historical,
frozen, pending, or unavailable. The Python API returns source dates and
warning flags for a report. The package includes a fictional five-source
example and all four original test cases.

- [Download the source ZIP, checksums and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/planning-snapshot-freshness-v0.1.0)
- [Run the fictional example](SETUP.md)

Qualification covers Windows and Ubuntu with CPython 3.12.16 and 3.15.2.
The runtime pins Pydantic 2.14.3 and tzdata 2026.6. Timestamps render in
America/New_York using the installed timezone package on both platforms.
