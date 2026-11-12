# Fictional declared-chain walkthrough

Extract the [0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/backup-chain-checker-v0.1.0)
into a fresh folder and select normal Python **3.12–3.15**, with 3.15.2 selected
for that minor in qualification. The CLI needs only `chain_check.py` and the
standard library. Supply Python separately; no pip distribution, backup product,
account, model or network connection is required by the checker.

The interface is `python -B chain_check.py --plan CONTROL_JSON`. `--plan` is
required; `--help` and `--version` are static. There is no backup-content, scan,
restore, delete or output-file option. JSON goes to stdout. Shell redirection is
a separate caller action and can overwrite that caller's chosen capture file.

`DECLARED_CHAIN_CONSISTENT` describes supported **declarations only**. It does
not prove that backups exist, are complete or intact, match their parents, or
can be restored. No decision authorizes deletion. Keep real plans, identifying
IDs, dependency relationships and captures private.

## Run the complete fictional exercise

Create an existing user-owned private parent outside source. Save the single
Python block below as `fictional_walkthrough.py` there and run it unchanged
with two absolute arguments: extracted script and existing private parent.
PowerShell, with fictional paths:

```powershell
python -B 'D:\Private\chain-review\fictional_walkthrough.py' 'D:\Source\backup-chain-checker-0.1.0\chain_check.py' 'D:\Private\chain-review'
```

Ubuntu:

```sh
python3.12 -B '/absolute/private/chain-review/fictional_walkthrough.py' '/absolute/source/backup-chain-checker-0.1.0/chain_check.py' '/absolute/private/chain-review'
```

The driver creates a **new** `fictional-demo` child and refuses to reuse it.
It retains invented controls, an unrelated file and a prior capture for private
inspection. All IDs, series and sequences are authored examples. No timestamps,
backup files, real inventory, operational records or storage application are used.

| Case | Exit | Overall status | Selected target |
| --- | ---: | --- | --- |
| `valid_chain` | 0 | `DECLARED_CHAIN_CONSISTENT` | Full root through two incrementals. |
| `missing_parent` | 1 | `REVIEW_REQUIRED` | Blocked; no partial order. |
| `cycle` | 1 | `REVIEW_REQUIRED` | Both cycle members flagged; no order. |
| `unrelated_broken` | 1 | `REVIEW_REQUIRED` | Clean selected order retained despite another broken branch. |
| `missing_target` | 1 | `REVIEW_REQUIRED` | Selected ID is absent; no order. |
| `invalid_schema` | 2 | `ERROR` / `PLAN_SCHEMA_INVALID` | Boolean schema version is refused. |

The block constructs every complete expected JSON value, checks actual exit
codes/stderr and verifies all input, extra, prior-capture, tree and runtime bytes
after every process. Its 60-second child timeout is a driver choice, not a CLI
filesystem deadline. It prints fictional JSON and creates no captured result file.

```python
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

if not __debug__ or sys.flags.optimize or os.environ.get("PYTHONOPTIMIZE"):
    raise RuntimeError("NORMAL_PYTHON_REQUIRED")
if len(sys.argv) != 3:
    raise RuntimeError("SELECT_SCRIPT_AND_PRIVATE_PARENT_ARGUMENTS")
SCRIPT, PRIVATE_PARENT = map(Path, sys.argv[1:])
if (not SCRIPT.is_absolute() or not PRIVATE_PARENT.is_absolute()
        or not SCRIPT.is_file() or not PRIVATE_PARENT.is_dir()):
    raise RuntimeError("SELECT_ABSOLUTE_EXISTING_SCRIPT_AND_PRIVATE_PARENT")
SCRIPT = SCRIPT.resolve()
PRIVATE_PARENT = PRIVATE_PARENT.resolve()
if PRIVATE_PARENT.is_relative_to(SCRIPT.parent):
    raise RuntimeError("PRIVATE_PARENT_MUST_BE_OUTSIDE_SOURCE")
WORK = PRIVATE_PARENT / "fictional-demo"
WORK.mkdir(mode=0o700, exist_ok=False)

FLAGS = dict.fromkeys((
    "filesystem_scanned", "backup_contents_read", "metadata_verified",
    "restore_performed", "deletion_performed", "deletion_authorized",
    "commands_generated", "network_probed",
), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def snapshot(identifier, *, kind="full", parent=None, sequence=0,
             series="sample_series"):
    return dict(id=identifier, series_id=series, kind=kind,
                parent_id=parent, sequence=sequence)


def plan(rows, target="sample_second", version=1):
    return dict(schema_version=version, restore_point_id=target, snapshots=rows)


def expected(rows, *, target="sample_second", series=1, cycles=0,
             target_issues=(), order=()):
    local_failures = sum(bool(issues) for name, issues in rows)
    return dict(
        schema_version=1,
        status="REVIEW_REQUIRED" if local_failures or target_issues else "DECLARED_CHAIN_CONSISTENT",
        scope="DECLARED_FULL_INCREMENTAL_METADATA_ONLY", **FLAGS,
        counts=dict(snapshots=len(rows), series=series,
                    snapshots_with_issues=local_failures, cycle_members=cycles),
        snapshots=[dict(id=name, issues=issues) for name, issues in sorted(rows)],
        target=dict(id=target,
                    status="REVIEW_REQUIRED" if target_issues else "DECLARED_CHAIN_CONSISTENT",
                    issues=list(target_issues), declared_order=list(order)),
    )


valid = [snapshot("sample_full"),
         snapshot("sample_first", kind="incremental", parent="sample_full", sequence=1),
         snapshot("sample_second", kind="incremental", parent="sample_first", sequence=2)]
clean_rows = [(value["id"], []) for value in valid]
clean_order = ["sample_full", "sample_first", "sample_second"]
missing = [snapshot("sample_child", kind="incremental", parent="sample_missing", sequence=1)]
cyclic = [snapshot("sample_a", kind="incremental", parent="sample_b", sequence=1),
          snapshot("sample_b", kind="incremental", parent="sample_a", sequence=2)]
unrelated = valid + [snapshot("other_child", kind="incremental", parent="other_missing",
                             sequence=1, series="other_series")]
cases = [
    ("valid_chain", plan(valid), 0, expected(clean_rows, order=clean_order)),
    ("missing_parent", plan(missing, target="sample_child"), 1, expected(
        [("sample_child", ["PARENT_NOT_FOUND"])], target="sample_child",
        target_issues=["TARGET_CHAIN_BLOCKED"])),
    ("cycle", plan(cyclic, target="sample_b"), 1, expected(
        [("sample_a", ["PARENT_SEQUENCE_NOT_EARLIER", "DEPENDENCY_CYCLE"]),
         ("sample_b", ["DEPENDENCY_CYCLE"])], target="sample_b", cycles=2,
        target_issues=["TARGET_CHAIN_BLOCKED"])),
    ("unrelated_broken", plan(unrelated), 1, expected(
        clean_rows + [("other_child", ["PARENT_NOT_FOUND"])], series=2, order=clean_order)),
    ("missing_target", plan(valid, target="sample_absent"), 1, expected(
        clean_rows, target="sample_absent", target_issues=["RESTORE_POINT_NOT_FOUND"])),
    ("invalid_schema", plan(valid, version=True), 2,
     dict(status="ERROR", code="PLAN_SCHEMA_INVALID", **FLAGS)),
]
selected = []
for name, value, exit_code, result in cases:
    control = WORK / (name + ".json")
    write_new(control, (json.dumps(value, ensure_ascii=True, sort_keys=True) + "\n").encode())
    selected.append((name, control, exit_code, result))
write_new(WORK / "unrelated.txt", b"FICTIONAL_EXTRA_NOT_A_SELECTED_PLAN\n")
write_new(WORK / "prior-capture.txt", b"Fictional previous capture must stay unchanged\n")


def snapshot_tree():
    entries = sorted(WORK.rglob("*"))
    tree = [(path.relative_to(WORK).as_posix(), path.is_dir()) for path in entries]
    hashes = {path.relative_to(WORK).as_posix(): sha(path.read_bytes())
              for path in entries if path.is_file()}
    return tree, hashes


original = snapshot_tree()
runtime_hash = sha(SCRIPT.read_bytes())
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
results = []
for name, control, exit_code, complete_expected in selected:
    completed = subprocess.run(
        [sys.executable, "-B", str(SCRIPT), "--plan", str(control)],
        cwd=WORK, env=environment, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=60,
    )
    assert completed.returncode == exit_code, (name, "EXIT_MISMATCH")
    assert completed.stderr == "", (name, "UNEXPECTED_STDERR")
    assert completed.stdout.endswith("\n") and len(completed.stdout.splitlines()) == 1
    actual = json.loads(completed.stdout)
    assert actual == complete_expected, (name, "FULL_JSON_MISMATCH")
    assert str(WORK) not in completed.stdout.replace("\\\\", "\\")
    assert "sample_series" not in completed.stdout
    assert "other_series" not in completed.stdout
    assert "FICTIONAL_EXTRA_NOT_A_SELECTED_PLAN" not in completed.stdout
    assert snapshot_tree() == original, (name, "INPUT_TREE_OR_PRIOR_CAPTURE_CHANGED")
    assert sha(SCRIPT.read_bytes()) == runtime_hash, (name, "RUNTIME_CHANGED")
    results.append(dict(case=name, exit_code=completed.returncode, report=actual))

print(json.dumps(dict(
    cases=results, input_plans_tree_prior_output_and_runtime_bytes_preserved=True,
), ensure_ascii=True, sort_keys=True, indent=2))
```

The driver verifies sampled byte/tree preservation, not access times, every OS
property or ACL privacy. Its requested private file modes remain subject to the
actual OS, Python and inherited permissions. There is no automatic cleanup or
rollback. Inspect the retained invented work before removing it yourself.

## Interpret the declaration contract

The schema has exactly `schema_version`, `restore_point_id` and `snapshots`.
Every row has exactly `id`, `series_id`, `kind`, `parent_id` and `sequence`.
Version is integer 1; IDs are globally unique neutral ASCII tokens matching
`[a-z][a-z0-9_-]{0,39}`. Sequence is a non-boolean integer **0–1000000** and is
unique within each series. The selected JSON is at most **64 KiB**, with
**1–256** snapshots. Duplicate keys, unknown fields, wrong types and nonstandard
numbers are refused. These bounds are not complete CPU/memory/I/O deadlines.

A full snapshot has no parent and can start at any allowed sequence. An
incremental has one existing parent in the same series with a strictly smaller
sequence. Gaps, branches and multiple full roots with distinct sequences are
allowed. Every parent-reference cycle is flagged, including self references and
incorrect parent edges on full declarations. A descendant of a cycle is not a
cycle member, but its selected ancestry is blocked. No unsupported edge is repaired.

All snapshots are checked, including those outside selected ancestry. Local
issues do not describe complete ancestry. A missing target or any bad ancestor
gives no partial selected order. A clean selected chain can retain its order
while an unrelated bad branch makes the overall result `REVIEW_REQUIRED`.
Snapshot rows are sorted by ID; issue order is fixed. See [README.md](README.md)
for the complete code table and preserved field semantics.

The format is a neutral single-parent declaration model, not a vendor backup
adapter. Differential, deduplicated and multi-parent storage are outside its
scope. Do not feed dependent chains into the separate independent-full Backup
Retention Planner or interpret a consistent chain as safe removal advice.

## Privacy, paths and remaining limits

Results retain snapshot IDs, counts, local issues and the selected dependency
order. They omit series labels, sequences, raw parent fields, selected paths and
native errors. IDs and their relationships can still identify an operational
design. Fixed CLI errors do not anonymize library tracebacks or caller captures.

Use fully spelled canonical paths and stable, trusted local inputs. The reader
requires an ordinary single-link input and ordinary ancestors, checks original
path components before absolute normalization, and samples descriptor/path
identity around a bounded read. Local Windows fictional probes on Python 3.12.7
and 3.15.2 rejected dot/space suffixes on both the input leaf and its parent.
Those observations do not establish a universal alias or filesystem guarantee.
Observed links/reparse points, special files, stream/device/UNC forms, traversal,
reserved names and ambiguous trailing components are unsupported inputs.

The reader does not hold an atomic snapshot, deny concurrent writers or enforce
a hostile-filesystem sandbox. Remote/mounted/virtual/live-changing storage,
mount rebinding and blocked OS I/O remain outside the qualification. Reads can
affect access metadata, and Python caches are separate; this guide uses `-B`.
Exit 130 means interruption, and a partial or failed stdout capture is not a
completed report. There is no backup, restore, deletion or rollback transaction.

No input, output or test verifies backup contents, parent compatibility,
independence, completeness, application consistency, ownership, licensing,
restorability or permission to delete or publish real records. Read the
[private workspace guide](docs/PRIVATE-WORKSPACE.md), [qualification boundary](docs/QUALIFICATION.md)
and [provenance](docs/PROVENANCE.md) before using your own private plans.
