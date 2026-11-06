# Install and use the worker and queue review tools

Review selected job-interface, ownership, delivery and result declarations.
Start with the [definitions and method](../../methodology/WORKER-QUEUE.md) and
[machine-readable component guide](components.json). Every independent MIT wheel
provides a CLI, an embedded fictional demo and its actual Python API. Supply
Python 3.12 or 3.13; runtime dependencies are standard library only.

| Tool | When to use it | Fictional input and expected output | What the result establishes |
| --- | --- | --- | --- |
| [Work Item Contract Checker](../../tools/work-item-contract-checker/README.md) | Review a job's declared interface and metadata presence. | One service-summary job references an exact handler and two required labels: PASS. Remove review-scope: REVIEW_REQUIRED with the missing ID. | Exact selected handler binding and declared label presence, not payload/schema/value correctness. |
| [Worker Lease History Checker](../../tools/worker-lease-history-checker/README.md) | Explain ownership, renewals, expiry and takeover at an explicit as-of ordinal. | Alpha owns [10,20); beta acquires at 20 and renews to 50. At as_of 40: PASS, current_owner worker-beta/token 2. | Consistency of the supplied ownership history, not authenticated workers or enforced fencing. |
| [Queue Acknowledgement Reconciler](../../tools/queue-acknowledgement-reconciler/README.md) | Account for selected deliveries and acknowledgement claims. | A current beta delivery/acknowledgement PASS; a late alpha acknowledgement remains a finding alongside it. | Selected declaration accounting, not actual broker delivery or a sent acknowledgement. |
| [Worker Result Commit Checker](../../tools/worker-result-commit-checker/README.md) | Check result/commit bindings and declared ownership at both times. | The beta result at 34 and commit at 35 PASS. A commit at lease end 50 requires review; equal-artifact commit aliases remain ambiguous. | Exact selected record consistency, not artifact bytes, actual persistence or exactly-once processing. |

All inputs are assertions. PASS does not authorize a dispatch, retry, acknowledgement
or result commit. Missing history is not proof an item is unowned. Results can
contain private IDs, hashes and numeric declarations; keep real inputs/reports private.

## Install one tool or all four

Download selected wheels and SHA256SUMS.txt from the immutable
[v1.0.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/worker-queue-wheels-v1.0.0).
Verify SHA-256 values before installation. Create a fresh environment with
`py -3.12 -m venv ENV` on Windows or `python3.12 -m venv ENV` on Ubuntu. Use that
environment's Python and scripts directory. Then choose one install:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_work_item_contract_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-worker-queue-collection==1.0.0
```

For the collection, place all five release wheels in WHEEL_DIRECTORY; exact-version
dependencies resolve offline. `outlands-worker-queue` lists all four commands.
Run `outlands-work-item-contract-checker-demo` for its embedded invented input or
`outlands-work-item-contract-checker --input PRIVATE_JSON` for selected input.
Substitute the individual filename/command from components.json for another tool.
These are downloadable wheels; package-index registration is not implied. Earlier
source downloads remain available through each tool's catalog entry.

## Call a tool from another project

The operations are `items.check`, `leases.check`, `acks.check` and `commits.check`
inside their distinct outlands_TOOL packages. Each takes raw JSON bytes and returns
a report dictionary; no sibling repository imports or network access are required.
This complete example runs the installed lease tool with embedded fictional input:

```python
from importlib.resources import files
from outlands_worker_lease_history_checker.leases import check

raw = files("outlands_worker_lease_history_checker").joinpath("examples", "input.json").read_bytes()
report = check(raw)
assert report["status"] == "PASS"
assert report["assessment"]["items"][0]["current_owner"]["worker"] == "worker-beta"
assert report["ownership_enforced"] is False
```

CLI exits are 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal. Fixed library refusals raise
the package's documented rejection. An overall review result stays unqualified even
if it retains individual consistent rows. Structural findings withhold assessment
and scope pins; logical findings retain diagnostics/pins with no qualified scope.

## Worked workflow

After installing all four, run
`python -B integrations/worker-queue/exercise.py` from the repository root.
The same invented handler/item/lease/delivery snapshots connect the four APIs.
The workflow checks required metadata, expiry-boundary takeover, a current delivery
and acknowledgement, then a separately selected result and commit. Identical
declarations count once. Late old-owner claims, missing metadata and expired commits
remain findings; malformed snapshot links withhold assessment. No actual payload,
worker, queue, artifact or database is accessed and no job is executed.

## Relationship to Data & Services Stack

[Data & Services Stack](../../systems/data-services-stack/README.md) is a useful
related workflow, with different contracts. Its single-operator `.writer-lock`,
immutable journal generations and `COMMITTED` markers are not worker leases,
ownership tokens or these result/commit records. Its notification queue uses one
explicit fake-transport attempt at a supplied monotonic tick; fake acceptance and
caller-reported delivery are not verified broker acknowledgement or actual delivery.
Restart uncertainty remains review-required and does not authorize replay.

A caller-reviewed adapter would need explicit mappings for job/run keys and
revisions; handler and interface contracts; metadata IDs; exact raw versus normalized
hash domains; tick/ordinal units and as-of snapshots; worker identities and complete
lease events; delivery/acknowledgement identities/states; artifact fingerprints;
and independently reviewed commit evidence. The stack does not supply the tools'
worker lease/token protocol, broker history or artifact-evidence records. Do not
invent those from journal locks, attempt counters, fake receipts or status labels.
No adapter or live system integration is included or qualified by this release.
Actual jobs, journals, recipients, credentials, records and reports stay private.

## Build and qualification

Use Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create empty absolute output
directories outside the checkout, then run:

```text
python -B integrations/worker-queue/build_wheels.py --output OUTPUT_DIRECTORY
python -B integrations/worker-queue/verify_wheels.py --wheels OUTPUT_DIRECTORY
```

The build verifies exact public SOURCE-MANIFEST pins for each selected entry,
toolkit.py, native_windows.py, decision_core.py, worker_core.py, fictional examples,
README and MIT license. Relative imports isolate each wheel. Original tool source
is unchanged. ZIP headers use fixed synthetic metadata; standard package/license
metadata remains. SHA256SUMS.txt and release.json pin exact outputs.

Qualification runs the existing 13 standalone/cross-tool acceptance tests, two
byte-identical builds, fresh individual/collection CLI/demo/API/review cases, the
installed worked exercise and the literal API snippet above. Windows/Ubuntu
Python 3.12/3.13 builds compare exact bytes; anonymous public-download installs
repeat after release. This verifies package behavior on invented records, not
live workers, queue enforcement, payload values, artifacts or durable result commits.
