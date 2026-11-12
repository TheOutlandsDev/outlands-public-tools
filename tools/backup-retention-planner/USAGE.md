# Fictional retention-policy walkthrough

Extract the [0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/backup-retention-planner-v0.1.0)
into a fresh folder and select normal Python **3.12–3.15**, with 3.15.2 selected
for that minor in qualification. The CLI needs only `retention_plan.py` and the
standard library. Supply Python separately; no pip distribution, backup product,
account, model or network connection is needed by the planner.

The exact interface is `python -B retention_plan.py --plan CONTROL_JSON`.
`--plan` is required; `--help` and `--version` are static. There is no output-file,
scan, copy, restore or delete option. JSON goes to stdout. A caller's shell
redirection is separate and can overwrite that caller's chosen capture file.

`KEEP` means protected by a supplied rule or uncertainty. `REVIEW` means outside
those declared protections. **Neither decision authorizes deletion.** The tool
does not verify that a snapshot exists, is independent, contains intact data or
can be restored. Keep real plans, identifying IDs and results private.

## Run the complete fictional exercise

Create an existing user-owned private parent outside source. Save the single
Python block below as `fictional_walkthrough.py` there and run it unchanged
with two absolute arguments: extracted script and existing private parent.
PowerShell, with fictional paths:

```powershell
python -B 'D:\Private\retention\fictional_walkthrough.py' 'D:\Source\backup-retention-planner-0.1.0\retention_plan.py' 'D:\Private\retention'
```

Ubuntu:

```sh
python3.12 -B '/absolute/private/retention/fictional_walkthrough.py' '/absolute/source/backup-retention-planner-0.1.0/retention_plan.py' '/absolute/private/retention'
```

The driver creates a **new** `fictional-demo` child and refuses to reuse it.
It retains its invented controls and prior capture for inspection. All **2030
UTC timestamps are fixed fictional policy inputs**, not real capture dates or
the local clock. No backup body, storage directory or operational record is used.

| Case | Exit | Complete JSON status | Observation |
| --- | ---: | --- | --- |
| `keep_only` | 0 | `KEEP_ONLY_PLAN` | One nonfuture declaration is latest-protected. |
| `review` | 1 | `REVIEW_REQUIRED` | An older unpinned declaration needs review. |
| `future_review` | 1 | `REVIEW_REQUIRED` | Both rows are KEEP, with future/count-shortfall issues. |
| `tie_boundary_pin` | 0 | `KEEP_ONLY_PLAN` | Cutoff ties, exact age boundary and old pin are protected. |
| `age_disabled` | 1 | `REVIEW_REQUIRED` | Age zero removes age protection from the boundary row. |
| `invalid_timestamp` | 2 | `ERROR` / `TIMESTAMP_INVALID` | Canonical clock syntax refuses `24:00:00`. |

The block constructs every complete expected JSON value, checks actual exit
codes/stderr and verifies all input, extra, prior-capture, tree and runtime bytes
after every process. Its 60-second child timeout is a driver choice, not a CLI
filesystem deadline. It prints fictional JSON; it creates no captured result file.

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

# Fixed fictional UTC metadata only; no current time is requested.
AS_OF = "2030-04-10T12:00:00Z"
FLAGS = dict.fromkeys((
    "filesystem_scanned", "backup_contents_verified", "metadata_verified",
    "deletion_performed", "deletion_authorized", "network_probed",
), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def snapshot(identifier, created=AS_OF, pinned=False):
    return dict(id=identifier, created_at=created, pinned=pinned)


def plan(rows, latest=1, days=0, as_of=AS_OF):
    return dict(schema_version=1, snapshot_kind="independent_full", as_of=as_of,
                policy=dict(keep_latest=latest, keep_days=days), snapshots=rows)


def expected(rows, *, keep, review, future, nonfuture, latest, issues=()):
    return dict(
        schema_version=1,
        status="REVIEW_REQUIRED" if review or issues else "KEEP_ONLY_PLAN",
        scope="DECLARED_INDEPENDENT_FULL_METADATA_ONLY", **FLAGS,
        counts=dict(keep=keep, review=review, future=future,
                    nonfuture=nonfuture, latest_protected=latest),
        snapshots=[dict(id=name, decision=decision, reasons=reasons)
                   for name, decision, reasons in rows], issues=list(issues),
    )


now = snapshot("sample_now")
old = snapshot("sample_old", "2030-04-01T12:00:00Z")
future = snapshot("sample_future", "2030-04-11T12:00:00Z")
tied = [snapshot("sample_new"),
        snapshot("sample_tie_a", "2030-04-09T12:00:00Z"),
        snapshot("sample_tie_b", "2030-04-09T12:00:00Z"),
        snapshot("sample_boundary", "2030-04-03T12:00:00Z"),
        snapshot("sample_pinned", "2030-04-01T12:00:00Z", True)]

cases = [
    ("keep_only", plan([now]), 0, expected(
        [("sample_now", "KEEP", ["LATEST_COUNT"])],
        keep=1, review=0, future=0, nonfuture=1, latest=1)),
    ("review", plan([now, old]), 1, expected(
        [("sample_now", "KEEP", ["LATEST_COUNT"]),
         ("sample_old", "REVIEW", ["OUTSIDE_DECLARED_PROTECTIONS"])],
        keep=1, review=1, future=0, nonfuture=2, latest=1)),
    ("future_review", plan([now, future], latest=2, days=7), 1, expected(
        [("sample_now", "KEEP", ["LATEST_COUNT", "WITHIN_AGE_WINDOW"]),
         ("sample_future", "KEEP", ["FUTURE_TIMESTAMP_UNVERIFIED"])],
        keep=2, review=0, future=1, nonfuture=1, latest=1,
        issues=["FUTURE_TIMESTAMPS_PRESENT", "LATEST_COUNT_NOT_MET"])),
    ("tie_boundary_pin", plan(tied, latest=2, days=7), 0, expected(
        [("sample_new", "KEEP", ["LATEST_COUNT", "WITHIN_AGE_WINDOW"]),
         ("sample_tie_a", "KEEP", ["LATEST_COUNT", "WITHIN_AGE_WINDOW"]),
         ("sample_tie_b", "KEEP", ["LATEST_COUNT", "WITHIN_AGE_WINDOW"]),
         ("sample_boundary", "KEEP", ["WITHIN_AGE_WINDOW"]),
         ("sample_pinned", "KEEP", ["PINNED"])],
        keep=5, review=0, future=0, nonfuture=5, latest=3)),
    ("age_disabled", plan(tied, latest=2, days=0), 1, expected(
        [("sample_new", "KEEP", ["LATEST_COUNT"]),
         ("sample_tie_a", "KEEP", ["LATEST_COUNT"]),
         ("sample_tie_b", "KEEP", ["LATEST_COUNT"]),
         ("sample_boundary", "REVIEW", ["OUTSIDE_DECLARED_PROTECTIONS"]),
         ("sample_pinned", "KEEP", ["PINNED"])],
        keep=4, review=1, future=0, nonfuture=5, latest=3)),
    ("invalid_timestamp", plan([now], as_of="2030-04-10T24:00:00Z"), 2,
     dict(status="ERROR", code="TIMESTAMP_INVALID", **FLAGS)),
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
    assert "2030-" not in completed.stdout, (name, "INPUT_DATE_DISCLOSED")
    assert "FICTIONAL_EXTRA_NOT_A_SELECTED_PLAN" not in completed.stdout
    assert snapshot_tree() == original, (name, "INPUT_TREE_OR_PRIOR_CAPTURE_CHANGED")
    assert sha(SCRIPT.read_bytes()) == runtime_hash, (name, "RUNTIME_CHANGED")
    results.append(dict(case=name, exit_code=completed.returncode, report=actual))

print(json.dumps(dict(
    cases=results, input_plans_tree_prior_output_and_runtime_bytes_preserved=True,
), ensure_ascii=True, sort_keys=True, indent=2))
```

The driver verifies sampled byte/tree preservation, not access times, every OS
property or ACL privacy. Its requested private file modes are subject to the
actual OS, Python and inherited permissions. There is no automatic cleanup or
rollback. Inspect the retained invented work before removing it yourself.

## Interpret the rules and limits

Protections are a union. Pins protect declarations; future dates protect for
review but are excluded from the nonfuture count ranking and age calculation.
The Nth latest nonfuture instant defines a cutoff, protecting every timestamp
tie. A count shortfall protects all nonfuture declarations but requires review.
Age zero disables age protection; a positive age uses inclusive rolling 24-hour
UTC periods. Reasons retain their fixed order; rows retain declaration order.
Neither a pin nor supplied `independent_full` metadata is independently verified.

Input is at most **64 KiB**, with **1–256** snapshots, IDs of at most **40**
neutral ASCII characters, `keep_latest` **1–256** and `keep_days` **0–36500**.
Field sets and types are exact. Duplicate keys/IDs, nonstandard numbers,
unsupported kinds, invalid dates and noncanonical UTC syntax are refused.
Canonical timestamps use `YYYY-MM-DDTHH:MM:SSZ`, hours 00–23 and valid calendar
dates. Offsets, fractional seconds, leap seconds and `24:00:00` are unsupported.
The planner never replaces the supplied `as_of` with the machine clock.

Completed results retain IDs, counts, fixed reasons and issues. Dates, policy
values, raw fields, selected paths and native errors are omitted. IDs and their
relationships can still disclose an operational pattern. Fixed CLI errors do
not anonymize library tracebacks, caller captures, real plans or future results.

Use fully spelled **canonical paths** and trusted quiescent local files. The
reader requires an ordinary single-link input and ordinary ancestors, samples
path/descriptor identities around a bounded read, and refuses observed unsafe
links/reparse or special-file forms. It does not retain a filesystem snapshot,
deny concurrent writers, enforce a hostile-filesystem sandbox or prove safety
on remote, mounted, virtual or live-changing storage.

Windows absolute normalization can erase a trailing dot or space before the
retained validator examines components. A local fictional fixture returned the
same exit-0 plan for canonical `.json`, `.json.` and `.json` plus a space.
That measured acceptance is **not a suffix-refusal safeguard**. Supply canonical
spellings; no new lexical guard is claimed. Named-stream arguments, unsupported
device/UNC forms, traversal and observed links remain outside supported inputs.

The planner creates no backup or report files, but reads can affect access
metadata and Python caches are separate; this guide uses `-B`. Exit 130 means
interruption, and failed/partial caller captures are not complete results.
Byte bounds cannot interrupt blocked OS I/O. No declaration, decision or test
establishes backup existence, independence, integrity, restorability, available
space, ownership, licensing or permission to delete or publish real records.

Read the preserved [contract](README.md), [private workspace guide](docs/PRIVATE-WORKSPACE.md),
[qualification boundary](docs/QUALIFICATION.md) and [provenance](docs/PROVENANCE.md).
