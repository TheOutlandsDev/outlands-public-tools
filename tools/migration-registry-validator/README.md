# Offline Database Migration Registry Validator

Check local PostgreSQL and ClickHouse migration files against a SHA-256
registry. The validator checks inventory coverage and sequence order,
rejects a registry that authorizes execution, and returns a fingerprint
for the validated set.

- [Download the source ZIP, SHA-256 checksums, and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/migration-registry-validator-v0.1.0)
- [Run the 26-migration example](SETUP.md)

The source package includes the original validator, all six original test
cases, and a fictional fixture tree with 26 registered files and one
deliberately excluded example. It uses the Python standard library and
works with local files. Qualification covers Windows and Ubuntu with
Python 3.12.16 and 3.15.2.
