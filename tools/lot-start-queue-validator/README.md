# Offline Lot-Start Queue Validator

Check saved manufacturing planning rows and summarize remaining demand,
work-in-progress coverage and recommended lot starts. The validator checks
duplicate identifiers, consistency of the snapshot reference, and the
uncovered demand, lot count and status on each row before adding the totals.

- [Download the source ZIP, checksums and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/lot-start-queue-validator-v0.1.0)
- [Run the two-product example](SETUP.md)

The package includes the original validator and eight test cases with
fictional product names and quantities. Run the Python API offline using
Pydantic 2.14.3 after installing the pinned dependencies. The qualification
covers Windows and Ubuntu with CPython 3.12.16 and 3.15.2.
