# Component provenance and licensing

The reference imports no historical application bodies. The following first-party
MIT source snapshots come from the already public collection at revision
`15990170980ad2f16459276f494846bfebd9efb7`:

| Public source | Package copy | Original SHA-256 |
| --- | --- | --- |
| `tools/record-ingestion/ingestion.py` | `components/ingestion.py` | `d687e10ea4abb2c6cc35c63294df48ebcc6889b37658217f54e09c95e36b7c4b` |
| `tools/forecast-baseline-evaluator/evaluator.py` | `components/evaluator.py` | `9d0acd6979c01fff64f346dd45926280537b773da4c4a549f7f5b24c294fe224` |
| `tools/notification-outbox/outbox.py` | `components/outbox.py` | `d38e7c86fe53dda5da7df12aebfaf4525726f00c2f234b78548c2ee678716f78` |
| `tools/verified-transfers/transfer.py` | `vendor/transfer.py` | `9fcf98d54cb1218485de8371bd2b9e565aae744e935ccf68671083571fb50b45` |
| `tools/verified-transfers/transfer_windows.py` | `vendor/transfer_windows.py` | `7aa8507dfcfcdba008642d53c9ba6453fd171a3e15327e7f1af7e8d8efc84537` |

Paths in the second column are relative to `data_services`. All are byte-identical
except the evaluator's single `from ingestion` to `from .ingestion` import change.
Its algorithms, validation and result types are preserved. `files.py` sets the
I/O snapshot's trusted `REPOSITORY` boundary to the installed source/checkout;
the snapshot files themselves remain unchanged. These helpers are used only for
the documented checked reads, directory scopes and exclusive verified writes.

New configuration, state/journal, orchestration, CLI, packaging, documentation,
tests and fictional fixtures are fresh original MIT work. Existing first-party
MIT notices remain. Python, its standard library and native OS APIs are separately
supplied under their own applicable terms; no interpreter, third-party library,
binary, game asset, trained model or provider implementation is distributed.
Actual caller inputs, private integrations and records retain their own rights.

The source manifest binds the package bytes. The private publication gate also
checks these copies against exact public Git blobs and limits the evaluator
adaptation to that one import. Original historical business/source families
remain held independently; this reuse does not clear them for redistribution.
