# Offline Host Readiness Report Builder

Turn a saved JSON snapshot into a `doctor` report with pass, warn, or fail
checks for OS and Python support, workspace access, disk space, memory,
temporary directory access, and hostname resolution.

- [Source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/host-readiness-report-builder-v0.1.0)
- [Usage guide and fictional snapshots](SETUP.md)

The checker reads only supplied observations and uses the Python standard
library. It retains the original Portable OpsKit decision rules and the
`doctor --json` CLI test. The report can serve as the saved doctor input to the
[Offline Incident Evidence Bundle Builder](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/incident-evidence-bundle-builder).
Qualification covers Windows and Ubuntu with Python 3.12.16 and 3.15.2.
