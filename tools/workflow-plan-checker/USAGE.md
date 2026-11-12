# Fictional workflow-declaration walkthrough

Extract the [0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/workflow-plan-checker-v0.1.0)
into a fresh folder and select normal Python **3.12–3.15**, with 3.15.2 selected
for that minor in qualification. The CLI needs only `workflow_check.py` and
the standard library. Supply Python separately; no pip distribution, worker,
account, model or network connection is required by the checker.

The interface is `python -B workflow_check.py --plan CONTROL_JSON`. `--plan` is
required; `--help` and `--version` are static. There is no task runner, state
update, scheduling or output-file option. JSON goes to stdout. A caller's shell
redirection is separate and can overwrite that caller's chosen capture file.

`DECLARED_PLAN_CONSISTENT` describes supported declarations. It does not prove
that a task ran, succeeded, was authorized or can safely execute now. Eligibility
is static consistency information, **not execution authorization**. Keep real
plans, identifying IDs, dependency relationships and captures private.

## Run the complete fictional exercise

Create an existing user-owned private parent outside source. Save the single
Python block below as `fictional_walkthrough.py` there and run it unchanged
with two absolute arguments: extracted script and existing private parent.
PowerShell, with fictional paths:

```powershell
python -B 'D:\Private\workflow-review\fictional_walkthrough.py' 'D:\Source\workflow-plan-checker-0.1.0\workflow_check.py' 'D:\Private\workflow-review'
```

Ubuntu:

```sh
python3.12 -B '/absolute/private/workflow-review/fictional_walkthrough.py' '/absolute/source/workflow-plan-checker-0.1.0/workflow_check.py' '/absolute/private/workflow-review'
```

The driver creates a **new** `fictional-demo` child and refuses to reuse it.
It retains invented controls, an unrelated file and a prior capture for private
inspection. All IDs, dependencies and states are authored examples. No actual
tasks, commands, timestamps, worker configurations or operational records are used.

| Case | Exit | Complete JSON status | Observation |
| --- | ---: | --- | --- |
| `valid_plan` | 0 | `DECLARED_PLAN_CONSISTENT` | One pending task is eligible; another waits. |
| `active_plan` | 0 | `DECLARED_PLAN_CONSISTENT` | An in-progress task is not eligible again. |
| `missing_prerequisite` | 1 | `REVIEW_REQUIRED` | A referenced ID is absent; all three lists are empty. |
| `cycle` | 1 | `REVIEW_REQUIRED` | Both cycle members are flagged; all lists are empty. |
| `invalid_completion` | 1 | `REVIEW_REQUIRED` | A completed claim has an incomplete prerequisite. |
| `unrelated_broken` | 1 | `REVIEW_REQUIRED` | Even clean branches receive no order or next-step list. |
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
    "filesystem_scanned", "states_verified", "execution_performed",
    "execution_authorized", "commands_generated", "plan_changed", "network_probed",
), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def task(identifier, requires=(), state="pending"):
    return dict(id=identifier, requires=list(requires), state=state)


def plan(rows, version=1):
    return dict(schema_version=version, tasks=rows)


def expected(rows, *, edges, pending, active, completed, cycles=0,
             order=(), eligible=(), waiting=()):
    local_failures = sum(bool(issues) for name, issues in rows)
    if local_failures:
        assert not order and not eligible and not waiting
    return dict(
        schema_version=1,
        status="REVIEW_REQUIRED" if local_failures else "DECLARED_PLAN_CONSISTENT",
        scope="DECLARED_TASK_DEPENDENCIES_AND_STATES_ONLY", **FLAGS,
        counts=dict(tasks=len(rows), dependency_edges=edges, pending=pending,
                    in_progress=active, completed=completed,
                    tasks_with_issues=local_failures, cycle_members=cycles),
        tasks=[dict(id=name, issues=issues) for name, issues in sorted(rows)],
        declared_order=list(order), eligible_next_ids=list(eligible), waiting_ids=list(waiting),
    )


valid = [task("sample_prepare", state="completed"),
         task("sample_check", ["sample_prepare"]),
         task("sample_package", ["sample_check", "sample_prepare"])]
active = [task("sample_prepare", state="completed"),
          task("sample_check", ["sample_prepare"], "in_progress"),
          task("sample_package", ["sample_check"])]
missing = [task("sample_check", ["sample_missing"])]
cyclic = [task("sample_a", ["sample_b"]), task("sample_b", ["sample_a"])]
invalid_completion = [task("sample_prepare"),
                      task("sample_check", ["sample_prepare"], "completed")]
unrelated = valid + [task("other_task", ["other_missing"])]
clean_rows = [(value["id"], []) for value in valid]
clean_order = ["sample_prepare", "sample_check", "sample_package"]
cases = [
    ("valid_plan", plan(valid), 0, expected(
        clean_rows, edges=3, pending=2, active=0, completed=1, order=clean_order,
        eligible=["sample_check"], waiting=["sample_package"])),
    ("active_plan", plan(active), 0, expected(
        clean_rows, edges=2, pending=1, active=1, completed=1, order=clean_order,
        waiting=["sample_package"])),
    ("missing_prerequisite", plan(missing), 1, expected(
        [("sample_check", ["PREREQUISITE_NOT_FOUND"])],
        edges=1, pending=1, active=0, completed=0)),
    ("cycle", plan(cyclic), 1, expected(
        [("sample_a", ["DEPENDENCY_CYCLE"]), ("sample_b", ["DEPENDENCY_CYCLE"])],
        edges=2, pending=2, active=0, completed=0, cycles=2)),
    ("invalid_completion", plan(invalid_completion), 1, expected(
        [("sample_prepare", []), ("sample_check", ["COMPLETED_PREREQUISITES_UNSATISFIED"])],
        edges=1, pending=1, active=0, completed=1)),
    ("unrelated_broken", plan(unrelated), 1, expected(
        clean_rows + [("other_task", ["PREREQUISITE_NOT_FOUND"])],
        edges=4, pending=3, active=0, completed=1)),
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
    if exit_code == 1:
        assert all(actual[key] == [] for key in
                   ("declared_order", "eligible_next_ids", "waiting_ids"))
    assert str(WORK) not in completed.stdout.replace("\\\\", "\\")
    assert '"requires"' not in completed.stdout and '"state"' not in completed.stdout
    assert "FICTIONAL_EXTRA_NOT_A_SELECTED_PLAN" not in completed.stdout
    assert snapshot_tree() == original, (name, "INPUT_TREE_OR_PRIOR_CAPTURE_CHANGED")
    assert sha(SCRIPT.read_bytes()) == runtime_hash, (name, "RUNTIME_CHANGED")
    results.append(dict(case=name, exit_code=completed.returncode, report=actual))

print(json.dumps(dict(
    cases=results, input_plans_tree_prior_output_and_runtime_bytes_preserved=True,
), ensure_ascii=True, sort_keys=True, indent=2))
```

The driver checks sampled byte/tree preservation, not access times, every OS
property or ACL privacy. Its requested private file modes remain subject to the
actual OS, Python and inherited permissions. There is no automatic cleanup or
rollback. Inspect the retained invented work before removing it yourself.

## Interpret the workflow contract

The root has exactly `schema_version` and `tasks`. Each row has exactly `id`,
`requires` and `state`. Version is integer 1. IDs are unique neutral ASCII
tokens matching `[a-z][a-z0-9_-]{0,39}`. The selected JSON is at most **64 KiB**,
with **1–128 tasks** and **0–32 distinct prerequisite IDs per task**. Unknown
fields, duplicate keys/IDs/prerequisites, wrong types, unsupported states and
nonstandard numbers are input errors. These are not complete CPU/memory/I/O quotas.

States are exactly `pending`, `in_progress` or `completed`. Root tasks can have
any state. Pending tasks can wait normally. Active/completed claims require
every direct prerequisite to be declared completed. Every missing reference,
self dependency and actual cycle member requires review; descendants are not
automatically labeled cycle members. No state is repaired, advanced or verified.

**Any issue anywhere withholds all three lists**: `declared_order`,
`eligible_next_ids` and `waiting_ids`. No partial next-step list is returned,
even for an unrelated clean branch. For a consistent plan, order includes all
tasks and selects the lexicographically smallest currently available ID at each
step. It is not a direction to rerun completed tasks or restart active tasks.
Only pending tasks with completed direct prerequisites are eligible; the other
pending tasks wait. Both pending-ID lists are sorted.

## Privacy, paths and remaining limits

Results retain IDs, counts, issues and derived ordering relationships. Raw
per-task state and prerequisite fields, selected paths and native errors are
omitted. IDs and relationships can still identify an operational design.
Fixed CLI errors do not anonymize library tracebacks or caller captures.

Use fully spelled canonical paths and stable trusted local inputs. The reader
requires an ordinary single-link file and ordinary ancestors, checks original
path components before absolute normalization, and samples descriptor/path
identity around a bounded read. Local Windows fictional probes on Python 3.12.7
and 3.15.2 rejected trailing dot/space spellings on both the leaf and its parent.
Those observations do not establish a universal filesystem or alias guarantee.
Observed links/reparse points, special files, stream/device/UNC forms, traversal,
reserved names and ambiguous trailing components are unsupported inputs.

The reader does not hold an atomic snapshot, deny concurrent writers or enforce
a hostile-filesystem sandbox. Remote/mounted/virtual/live-changing storage,
mount rebinding and blocked OS I/O remain outside the qualification. Reads can
affect access metadata, and Python caches are separate; this guide uses `-B`.
Exit 130 means interruption; a partial or failed stdout capture is not a
completed report. There is no task execution, state-write or rollback transaction.

The model does not verify actual task completion, authorization, resource
conflicts, concurrency, time windows, containment or operational safety. It is
not an importer for worker contracts, scripts or CI YAML, and does not generate
commands or schedule work. No input, output or test authorizes execution or
publication of real plans. Read the preserved [contract](README.md),
[private workspace guide](docs/PRIVATE-WORKSPACE.md), [qualification boundary](docs/QUALIFICATION.md)
and [provenance](docs/PROVENANCE.md) before using your own private declarations.
