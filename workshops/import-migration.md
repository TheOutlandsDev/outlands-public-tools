# Preview an import and verify a fresh SQLite store

Use the complete Toolkit 0.5.0 source package and Python 3.12/3.13. No runtime is
bundled. All inputs are invented; the application never discovers private folders,
connects to an operational database or upgrades an existing schema.

From the extracted complete-package root, choose a new absolute scratch directory
whose parent already exists, outside the package:

```text
python -B workshops/system_exercises.py --exercise imports --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

The runner uses the original application's CLI throughout. It initializes a new
private instance, previews the supplied CSV/JSONL, attempts an unapproved rejection
policy, then explicitly accepts the rejected rows and imports only the valid records.
It independently opens the resulting SQLite file read-only and checks its contents.
It also attempts an exact repeat and an import with conflicting keys.

| Check | Expected result |
| --- | --- |
| Input rows | 7 |
| Accepted normalized records | 3, with quantities 3, 7 and 0 |
| Identical duplicate rows | 2 |
| Rejected rows | 2 |
| Accepted provenance entries | 5 |
| Import without accepting rejected rows | REJECTED_ROWS_REVIEW_REQUIRED, no store created |
| Exact repeat | EXACT_PLAN_ALREADY_IMPORTED |
| Three-row conflicting-key group | CONFLICTING_KEYS_REQUIRE_NEW_PLAN |
| Existing destination and selected input bytes | Unchanged |

The JSON result and private `exercise-results.json` distinguish the expected
outcomes from what this run actually checked. The instance is under `imports/`;
its `stores/<id>/data.sqlite3` is the verified fresh store. Reopening the original
CLI verifies one registered store. All instance contents remain private.

For the browser workflow, stop CLI activity, then run the application's `serve`
command against that instance. Inspect the preview, rejected-row codes and source
provenance before approving an import. Use Stop local server before CLI maintenance.
See the [pinned application guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/9a1b5641444888e87dd43ec8d1adfd0faf712d71/systems/import-migration-workbench/README.md).

This demonstrates explicit mapping, duplicate/rejection handling and independently
checked new-store construction. It does not demonstrate a live production migration,
schema upgrades, transactional replacement of an existing application, semantic
deduplication across instances or permission to publish an operational dataset.
The source data remains intact, and all rejected/conflicting values remain private.
