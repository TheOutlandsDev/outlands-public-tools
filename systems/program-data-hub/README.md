# Program Data Hub

Program Data Hub is a local SQLite application for cataloging files and keeping
their provenance. It indexes text documents with FTS5, imports tabular datasets
and already-exported SQL results, records typed metrics, and makes consistent
SQLite backups. It also checks local query contracts and their evidence as text.

Use the [setup guide](SETUP.md) to run the fictional example on Windows or Ubuntu.
Download the [source ZIP and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/program-data-hub-v0.1.0).

The release uses the Python standard library and an interpreter with SQLite FTS5.
Qualification runs on Python 3.12.16 and 3.15.2. The included original suite has
22 cases covering migrations, read-only SQLite access, backup, ingestion,
deduplication, rollback, SQL export lineage, metric conflicts and static policy.
It runs with `python -B -m unittest discover -s tests -v` from this directory.

This source edition uses fictional fixture data and neutral database identifiers.
See [source provenance](ORIGINS.md) for the changes made for publication.
