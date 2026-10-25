# Contributing

Suggestions and small reproducible improvements are welcome through the
[bug form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=vpd_reference_bug.yml)
or [suggestion form](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new?template=vpd_reference_suggestion.yml).
Include OS, Python version, source revision, command, expected documented result
and a tiny invented JSON fixture. Share only material you have rights to contribute.

Do not attach actual projects, private embedded/mapped paths, UUIDs, logs,
recordings, `.userdata`, credentials, editor binaries or proprietary code. If a
new editor shape needs discussion, provide a minimal synthetic structure and
clearly distinguish observed evidence from an inferred schema. Keep the initial
tool metadata-only: no automatic relinking, native deserialization, media reads,
file opening links, device operations or silent fallback after unsupported input.

Run `python -B -m unittest discover -s tests -v` and `python -B source_check.py`.
Changes should add meaningful boundary/behavior fixtures and update format,
coverage, privacy and validation documentation. Do not weaken byte/hash/path
checks to make a test pass. Contributions to this original module are offered
under its MIT license; third-party rights and notices remain applicable.
