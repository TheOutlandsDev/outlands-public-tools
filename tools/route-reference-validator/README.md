# Offline Route Reference Dataset Validator

Validate a route CSV and its metadata before using it in an offline workflow.
The Python API checks the exact headers, declared SHA-256, route and revision
counts, identifier prefixes and step positions. It preserves separate
occurrences of a repeated step.

- [Download the source ZIP, SHA-256 sums and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/route-reference-validator-v0.1.0)
- [Follow the usage guide](SETUP.md)

The included CSV has 239 fictional rows across five route revisions. The
validator implements a fixed revision 3 contract for this example. It runs
with the Python standard library and reads only the local files you pass in.
The release validation covers Windows and Ubuntu with CPython 3.12.16 and
3.15.2.

The seven original test cases use the fictional dataset. The release checks
also import the API from a fresh extraction and exercise both acceptance and
refusal cases.
