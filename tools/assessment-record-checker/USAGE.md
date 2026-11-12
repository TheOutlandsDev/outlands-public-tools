# Fictional assessment-record walkthrough

Extract the [0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/assessment-record-checker-v0.1.0)
into a fresh folder and select normal Python **3.12–3.15**, with 3.15.2 selected
for that minor in qualification. The CLI needs only `assessment_check.py` and
the standard library. Supply Python separately; no pip distribution, target,
service, account, model or network connection is required by the checker.

The interface is `python -B assessment_check.py --records RECORDS_JSON`.
`--records` is required; `--help` and `--version` are static. JSON goes to stdout.
There is no output-file option. A caller's shell redirection is separate and
can overwrite that caller's chosen capture file.

`DECLARED_RECORDS_CONSISTENT` describes supplied references and workflow claims.
It does not establish an assessment, successful fix, performed retest, target
isolation, authorization or security. An open finding can be consistent.
The checker tests no targets, executes no programs, collects no evidence,
verifies no outcome and changes no records. Keep actual ledgers, identifying
IDs and captures private. No record or result grants authorization to test.

## Run the complete fictional exercise

Create an existing user-owned private parent outside source. Save the single
Python block below as `fictional_walkthrough.py` there and run it unchanged
with two absolute arguments: extracted script and existing private parent.
PowerShell, with fictional paths:

```powershell
python -B 'D:\Private\record-review\fictional_walkthrough.py' 'D:\Source\assessment-record-checker-0.1.0\assessment_check.py' 'D:\Private\record-review'
```

Ubuntu:

```sh
python3.12 -B '/absolute/private/record-review/fictional_walkthrough.py' '/absolute/source/assessment-record-checker-0.1.0/assessment_check.py' '/absolute/private/record-review'
```

The driver creates a **new** `fictional-demo` child and refuses to reuse it.
It retains seven invented ledgers, an unrelated file and a prior capture for
private inspection. All IDs, series, revisions, states and outcomes are authored
examples. No actual assessment, target, finding, reviewer, source build,
timestamp, attachment or operational record is used.

| Case | Exit | Complete JSON status | Observation |
| --- | ---: | --- | --- |
| `consistent_open` | 0 | `DECLARED_RECORDS_CONSISTENT` | Open/null selection stays consistent despite a historical `still_present` outcome. |
| `closure_claim` | 0 | `DECLARED_RECORDS_CONSISTENT` | The selected latest-in-series retest declares `not_observed`; another series has a higher number. |
| `pending_claim` | 0 | `DECLARED_RECORDS_CONSISTENT` | Pending selection declares `not_run`, without claiming execution. |
| `stale_selection` | 1 | `REVIEW_REQUIRED` | A newer declared submission makes the selection stale even without its own retest. |
| `blocked_relationship` | 1 | `REVIEW_REQUIRED` | Cross-series replacement fails, blocking selection before latest/outcome checks. |
| `bad_history` | 1 | `REVIEW_REQUIRED` | The current closure claim passes, but an unselected nonlater historical retest still fails. |
| `invalid_schema` | 2 | `ERROR` / `RECORDS_SCHEMA_INVALID` | A Boolean is not schema version 1. |

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
    "execution_performed", "network_probed", "records_modified",
    "authorization_verified", "isolation_verified", "outcomes_verified",
), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def submission(identifier, revision, series="sample_series"):
    return dict(id=identifier, series_id=series, revision=revision)


def finding(state="closure_claimed", selected="sample_retest"):
    return dict(id="sample_finding", submission_id="sample_original",
                state=state, selected_retest_id=selected)


def retest(identifier="sample_retest", replacement="sample_replacement", outcome="not_observed"):
    return dict(id=identifier, finding_id="sample_finding",
                submission_id=replacement, outcome=outcome)


def ledger(submissions, findings, retests):
    return dict(schema_version=1, submissions=submissions, findings=findings, retests=retests)


def checked(identifier, kind, status="PASS", evidence=None):
    defaults = dict(submission="SUBMISSION_DECLARATION_VALID",
                    finding="CLOSURE_CLAIM_CONSISTENT", retest="RETEST_RELATIONSHIPS_CONSISTENT")
    return dict(id=identifier, kind=kind, status=status, evidence=evidence or defaults[kind])


def expected(rows):
    counts = {key: sum(row["status"] == status for row in rows)
              for key, status in (("passed", "PASS"), ("failed", "FAIL"), ("blocked", "BLOCKED"))}
    counts.update({plural: sum(row["kind"] == kind for row in rows)
                   for plural, kind in (("submissions", "submission"),
                                        ("findings", "finding"), ("retests", "retest"))})
    return dict(schema_version=1,
                status="REVIEW_REQUIRED" if counts["failed"] or counts["blocked"]
                else "DECLARED_RECORDS_CONSISTENT",
                scope="DECLARED_ASSESSMENT_RECORDS_ONLY", **FLAGS, counts=counts, checks=rows)


base = [submission("sample_original", 2), submission("sample_replacement", 10)]
base_rows = [checked("sample_original", "submission"), checked("sample_replacement", "submission")]
other = submission("other_submission", 999, series="other_series")
newer = submission("newest_submission", 20)
cross = [submission("sample_original", 2),
         submission("sample_replacement", 10, series="other_series"), newer]
old = submission("old_submission", 1)
consistent = ledger(base + [other], [finding()], [retest()])
cases = [
    ("consistent_open", ledger(base, [finding("open", None)], [retest(outcome="still_present")]), 0,
     expected(base_rows + [checked("sample_finding", "finding", evidence="OPEN_RECORD_CONSISTENT"),
                           checked("sample_retest", "retest")])),
    ("closure_claim", consistent, 0,
     expected(base_rows + [checked("other_submission", "submission"),
                           checked("sample_finding", "finding"), checked("sample_retest", "retest")])),
    ("pending_claim", ledger(base, [finding("retest_pending")], [retest(outcome="not_run")]), 0,
     expected(base_rows + [checked("sample_finding", "finding", evidence="PENDING_RECORD_CONSISTENT"),
                           checked("sample_retest", "retest")])),
    ("stale_selection", ledger(base + [newer], [finding()], [retest(outcome="inconclusive")]), 1,
     expected(base_rows + [checked("newest_submission", "submission"),
                           checked("sample_finding", "finding", "FAIL", "SELECTED_SUBMISSION_NOT_LATEST_DECLARED"),
                           checked("sample_retest", "retest")])),
    ("blocked_relationship", ledger(cross, [finding()], [retest(outcome="still_present")]), 1,
     expected(base_rows + [checked("newest_submission", "submission"),
                           checked("sample_finding", "finding", "BLOCKED", "SELECTED_RETEST_INVALID"),
                           checked("sample_retest", "retest", "FAIL", "SERIES_MISMATCH")])),
    ("bad_history", ledger(base + [old], [finding()],
                           [retest(), retest("history_retest", "old_submission", "not_run")]), 1,
     expected(base_rows + [checked("old_submission", "submission"),
                           checked("sample_finding", "finding"), checked("sample_retest", "retest"),
                           checked("history_retest", "retest", "FAIL", "REPLACEMENT_NOT_LATER")])),
    ("invalid_schema", dict(consistent, schema_version=True), 2,
     dict(status="ERROR", code="RECORDS_SCHEMA_INVALID", **FLAGS)),
]
selected = []
for name, value, exit_code, result in cases:
    control = WORK / (name + ".json")
    write_new(control, (json.dumps(value, ensure_ascii=True, sort_keys=True) + "\n").encode())
    selected.append((name, control, exit_code, result))
write_new(WORK / "unrelated.txt", b"FICTIONAL_EXTRA_NOT_A_SELECTED_LEDGER\n")
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
        [sys.executable, "-B", "-s", "-X", "utf8", str(SCRIPT), "--records", str(control)],
        cwd=WORK, env=environment, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=60,
    )
    assert completed.returncode == exit_code, (name, "EXIT_MISMATCH")
    assert completed.stderr == "", (name, "UNEXPECTED_STDERR")
    assert completed.stdout.endswith("\n") and len(completed.stdout.splitlines()) == 1
    actual = json.loads(completed.stdout)
    assert actual == complete_expected, (name, "FULL_JSON_MISMATCH")
    assert str(WORK) not in completed.stdout.replace("\\\\", "\\")
    assert all('"' + key + '"' not in completed.stdout for key in (
        "series_id", "revision", "submission_id", "state", "selected_retest_id", "finding_id", "outcome"))
    assert "FICTIONAL_EXTRA_NOT_A_SELECTED_LEDGER" not in completed.stdout
    assert snapshot_tree() == original, (name, "INPUT_TREE_OR_PRIOR_CAPTURE_CHANGED")
    assert sha(SCRIPT.read_bytes()) == runtime_hash, (name, "RUNTIME_CHANGED")
    results.append(dict(case=name, exit_code=completed.returncode, report=actual))

print(json.dumps(dict(
    cases=results, input_records_tree_prior_output_and_runtime_bytes_preserved=True,
), ensure_ascii=True, sort_keys=True, indent=2))
```

The driver checks sampled byte/tree preservation, not access times, every OS
property or ACL privacy. Its requested private file modes remain subject to the
actual OS, Python and inherited permissions. There is no automatic cleanup or
rollback. Inspect the retained invented work before removing it yourself.

## Interpret the declared records

The root has exactly `schema_version`, `submissions`, `findings` and `retests`.
Version is integer 1. Declare **1–128 submissions**, **0–128 findings** and
**0–128 retests**, at most **256 records combined**. The selected UTF-8 JSON may
include a BOM and is at most **64 KiB**. Revisions are actual integers from
**1 through 1000000000**. Entity IDs share one unique namespace; series labels
use a separate namespace. IDs, references and series labels match
`[a-z][a-z0-9_-]{0,39}`. Unknown fields, duplicate keys/IDs, duplicate
series/revision or finding/submission retest-summary pairs and wrong types are
input errors. These are not complete CPU/memory/I/O quotas. See the [exact
schema](README.md) for all fields.

Finding states are exactly `open`, `retest_pending` and `closure_claimed`.
Outcomes are exactly `not_run`, `still_present`, `not_observed` and `inconclusive`.
Original and replacement submissions must exist, share the same series and
have strictly increasing declared revisions. References are typed: a finding
ID does not stand in for a submission. Every historical retest is checked,
including summaries that are not selected.

Open findings require null selection; historical outcomes do not force closure.
Pending and closure claims require explicit retests belonging to that finding.
An invalid selected relationship blocks before latest-revision or outcome
checks. Otherwise selection must target the highest **declared integer
revision in the original series**, even if that newest submission has no
retest. Array order and higher numbers in other series do not change this.
Pending then requires `not_run`; closure requires `not_observed`. This is record
consistency, not an execution history or proof that a defect is absent.

Missing references and invalid dependencies produce `BLOCKED`; direct semantic
mismatches produce `FAIL`. Retest relationship checks use the original
submission reference rather than depending recursively on the finding's final
workflow result. Output follows submissions, then findings, then retests,
preserving each collection's declaration order.

## Privacy, paths and remaining limits

Results retain each checked record's own ID, kind, status, fixed evidence and
counts. Referenced IDs, series, revisions, states/outcomes, selected paths and
native errors are omitted as result fields. IDs and evidence can still reveal
a project or workflow. Fixed CLI errors do not anonymize library tracebacks or
caller captures. All six verification/action flags remain false on every path.

Use fully spelled canonical paths and stable trusted local inputs. The reader
requires an ordinary single-link file and ordinary ancestors, and samples
descriptor/path identity around a bounded read. Component checks happen after
absolute-path normalization. Local Windows fictional probes on Python 3.12.7
and 3.15.2 accepted leaf trailing-dot, leaf trailing-space and parent
trailing-dot spellings, while refusing the parent trailing-space spelling.
This is retained normalization behavior, not a blanket suffix-refusal or
alias-safety guarantee. Do not rely on those aliases. Observed links/reparse
points, special files, stream/device/UNC forms, traversal and reserved names
are unsupported inputs.

The reader does not hold an atomic snapshot, deny concurrent writers or enforce
a hostile-filesystem sandbox. Remote/mounted/virtual/live-changing storage,
mount rebinding and blocked OS I/O remain outside the qualification. Reads can
affect access metadata, and Python caches are separate; this guide uses `-B`.
Exit 130 means interruption; a partial or failed stdout capture is not a
completed report. No target, narrative, evidence, person, timestamp, source
build, command or scoring field is supported, and no attachment is opened.
No input, output or test authorizes an assessment, application change or
publication of real records. Read the [private workspace guide](docs/PRIVATE-WORKSPACE.md),
[qualification boundary](docs/QUALIFICATION.md) and [provenance](docs/PROVENANCE.md)
before using your own private declarations.
