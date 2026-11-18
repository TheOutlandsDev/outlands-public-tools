# Offline Production Workflow Contract Validator

Validate a saved workflow contract and calculate its SHA-256 checksum. The
validator checks the product mappings, workflow states and transitions, event
identity fields, historical dates, and development permission flags.

- [Download the source ZIP, checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/production-workflow-contract-validator-v0.1.0)
- [Run the fictional example](SETUP.md)

The package preserves the validation logic and all 15 original test cases,
with fictional product mappings and historical baseline data. Qualification
covers Windows and Ubuntu with CPython 3.12.16 and 3.15.2 and pinned
Pydantic 2.14.3. The validator reads local JSON. Permission flags are checked
as data and have no effect on a database or running workflow.
