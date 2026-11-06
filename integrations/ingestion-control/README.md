# Install and use the ingestion control tools

Review public intake mapping revisions and explicit batch, receipt and progress
declarations. Start with the [definitions and method](../../methodology/INGESTION-CONTROL.md)
and [machine-readable component guide](components.json). Each independent MIT
wheel provides a CLI, embedded fictional demo and actual documented Python API.
Supply Python 3.12 or 3.13; runtime code uses only the standard library.

| Tool | When to use it | Fictional input and expected output | What the result establishes |
| --- | --- | --- | --- |
| [Intake Mapping Diff](../../tools/intake-mapping-diff/README.md) | Explain field, identity and unknown-column policy changes. | Identical mappings PASS; a units field changing header/type/required flag returns three descriptive changes with REVIEW_REQUIRED. | Differences between valid supported mapping declarations. |
| [Batch Replay Planner](../../tools/batch-replay-planner/README.md) | Review selected candidate batches against receipt snapshots. | Exact declared committed batch-a is skipped; batch-b without a supplied receipt needs manual review. Uncertain selected history withholds the whole plan. | Advisory skip/review decisions; execution_authorized remains false. |
| [Checkpoint Progression Checker](../../tools/checkpoint-progression-checker/README.md) | Review a proposed ordinal progress window. | Previous 0, proposed 2, exact declared committed positions 1 and 2: suggest 2 for explicit review. A gap withholds the whole suggestion. | Contiguous declared coverage for the selected window. |
| [Ingestion Run Coverage Checker](../../tools/ingestion-run-coverage-checker/README.md) | Account for one selected expected cohort and its receipts. | Two matching batches declare six input rows, four accepted and two duplicate rows; a missing receipt withholds all totals. | Complete selected declaration coverage and once-per-batch declared sums. |

Nothing is imported, retried or persisted as a checkpoint. A committed status is
a supplied assertion, not proof of a target transaction. Source/mapping/preview and
evidence bytes are not loaded by the batch checkers; row_counts_recomputed,
receipt_authority_verified and exactly_once_verified remain false.

## Install one tool or the four-tool collection

Download selected wheel(s), MANIFEST.json and SHA256SUMS.txt from the
[versioned release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/ingestion-control-wheels-v1.0.0).
Verify SHA-256. One tool needs only its own wheel; the collection needs all five
wheels in one directory outside source. Create a fresh environment using
`py -3.12 -m venv ENV` on Windows or `python3.12 -m venv ENV` on Ubuntu.
Use that environment's Python:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_intake_mapping_diff-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-ingestion-control-collection==1.0.0
```

On PowerShell substitute `& ./ENV/Scripts/python.exe` for `python`; on Ubuntu use
`./ENV/bin/python`. Commands are in that environment's Scripts or bin directory.
Run `outlands-intake-mapping-diff-demo` for the embedded fictional example or
`outlands-intake-mapping-diff --input PRIVATE_JSON` for selected input.
Use literal wheel/command names in components.json for the other tools.
`outlands-ingestion-control` lists all four commands. These are downloadable
wheels; no package-index registration is implied. Actual mappings and receipts stay private.

## Call a tool from another project or AI workflow

This literal example calls the advisory replay planner on its embedded fixture:

```python
from importlib.resources import files
from outlands_batch_replay_planner.replay import plan
raw = files("outlands_batch_replay_planner").joinpath("examples", "input.json").read_bytes()
report = plan(raw)
assert report["status"] == "PASS"
assert report["execution_authorized"] is False
assert report["retry_performed"] is False
```

Operations are `mapping_diff.compare`, `replay.plan`, `checkpoints.check` and
`coverage.check` under the packages listed in components.json. AI callers can
read exact imports, formats, examples, result fields and boundaries there. Pass
raw JSON bytes and inspect status, issues, row counts and derived fields together.
Mapping Diff retains valid descriptive differences; batch findings withhold the
complete plan, checkpoint suggestion or totals. CLI exits are 0 PASS,
1 REVIEW_REQUIRED and 2 fixed refusal; malformed outer API input raises the refusal.

## Worked workflow and project connection

With the collection installed, run
`python -B integrations/ingestion-control/exercise.py` from the repository root.
It compares an invented mapping and shares two declared batches across replay,
checkpoint and coverage review. It checks skip versus manual review, declared totals,
duplicate declarations, missing receipts, uncertainty in noncandidate selected history,
no-change progress, stale metadata and rejected source counts. A selected cohort can
PASS coverage while the proposed checkpoint across an omitted position requires
review. The exercise performs no source/count recomputation or target import.
Existing source CLI acceptance separately exercises the public intake/reconciler
with invented CSV; its actual generated pins/counts remain declarations to these tools.

The [Import & Migration Workbench](../../systems/import-migration-workbench/README.md)
is a related local application with previews, fresh SQLite stores, durable attempts,
independent readback and interruption review. A caller-owned adapter must map its
outlands-import-contract-v1 to the distinct public outlands-table-map-v1 format,
reviewing identity cardinality, supported types/bounds, required/nullability,
case rules, trimming and empty-string policy explicitly. Map preview/attempt IDs,
source and preview hash domains, count meanings, receipt evidence and any abstract
progress sequence separately. Workbench journal/commit markers and readback evidence
are not interchangeable with caller-declared committed status. Do not flatten attempt
history into a presumed latest safe receipt or retry an uncertain outcome. Its
existing workflow controls and evidence remain necessary. No adapter or live
Workbench integration is implemented or qualified. Source records, schemas,
reviewer information, journals, workspaces and exports stay private. A consistency
report does not authorize import, replay, checkpoint advancement or publication.

## Build and qualification

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create an empty absolute
output directory outside the repository, then run
`python -B integrations/ingestion-control/build_wheels.py --output DIRECTORY` and
`python -B integrations/ingestion-control/verify_wheels.py --wheels DIRECTORY`.
The builder verifies exact public source manifests and isolates package imports.
Only Mapping Diff includes its pinned public intake.py helper, used for mapping
validation by that operation; it does not parse a workbook or records in this path.
Fixed synthetic archive metadata retains public MIT attribution and required package
metadata. Windows/Ubuntu Python 3.12/3.13 checks fresh-install each tool and the
collection, run CLI/demo/API/review cases, the installed workflow and literal API
example, and compare exact bytes. Anonymous public-download checks repeat after
release. Qualification covers fictional inputs and package behavior.
