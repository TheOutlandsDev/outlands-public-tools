# Dataset Review Manager

JSONL import/export now uses checked bounded reads and exclusive, flushed,
readback-verified writes on Windows/POSIX. Windows requires
`review_io_windows.py` beside the script; keep the existing repository layout.
Review/deduplication/holdout rules and SQLite connection/schema behavior remain.
Read the [JSONL I/O contract](docs/JSONL-IO.md) and
[review](../../docs/BATCH-30-DATASET-REVIEW-JSONL-IO.md).

A standalone, single-operator SQLite application implementing a neutral review workflow. Python 3.12+ and the standard library only. It starts with an empty store and has no network, model inference, browser server, shell execution, historical import hook or bundled training corpus.

Choose a private existing parent directory outside the repository, then initialize a new store:

```text
python systems/dataset-review/review_store.py --store NEW_PRIVATE_STORE init
python systems/dataset-review/review_store.py --store PRIVATE_STORE import --input PRIVATE_JSONL
python systems/dataset-review/review_store.py --store PRIVATE_STORE list
```

Each JSONL row needs `text` and a neutral `group` identifier, with optional `split` equal to train, validation or test. Input is limited to 4 MiB and each normalized record to 64 KiB. Imported status/approval fields are ignored; new records are pending. Exact normalized text is deduplicated while source-file hashes and row provenance are retained. Duplicate-linked groups are merged and the strongest holdout assignment wins: test, then validation, then train. This is exact-text deduplication, not semantic near-duplicate or benchmark-answer leakage detection.

Review an exact record ID from `list`:

```text
python systems/dataset-review/review_store.py --store PRIVATE_STORE review --id RECORD_ID --decision approved --actor Reviewer --note "Checked the fictional example" --quality --privacy --rights --context
python systems/dataset-review/review_store.py --store PRIVATE_STORE export --output NEW_PRIVATE_JSONL
```

Approval needs all four review assertions, a reviewer and a note. Obvious credential/key patterns block approval and require a separate redacted record. Review assertions do not establish technical correctness, legal rights or anonymity independently. Reimports do not approve or overwrite previous content. Export includes only approved records satisfying the four assertions and is limited to 16 MiB. Existing stores and export destinations are never replaced by init/export.

All stores, imports, review identities, provenance and exports remain private. Store/export destinations inside this repository and paths crossing symlinks/reparse points are rejected. The 64 MiB store-file check is a pre-operation check, not a hard total storage quota. Failure can leave a new partial store/export for inspection; automatic cleanup does not delete it. Use trusted local storage, one operator and stable inputs. This is not a hostile-database or multi-user authorization boundary, transactional backup service or arbitrary filesystem sandbox. Manually protect the store and its journal with appropriate OS permissions. A public export needs its own release review.

This is a fresh portable implementation of the review/deduplication/group-split methodology, with no original conversation archive, model settings, historical import script, private schema or UI copied. MIT licensed; see [licensing](../../LICENSING.md) and [validation](../../docs/BATCH-6-REVIEW.md).
