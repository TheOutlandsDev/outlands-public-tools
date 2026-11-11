# Fictional saved-report walkthrough

Extract the [0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/source-inventory-diff-v0.1.0)
into a fresh directory. Select normal Python 3.12–3.15; qualification selects
3.15.2 for that minor. Only `inventory_diff.py` is needed by the CLI. No pip
distribution, producer module, interpreter installation, network, model or
account is required by this script.

Create an existing user-owned private parent outside source. Save the single
Python block below as `fictional_walkthrough.py` there, then run it unchanged
with two absolute arguments: the extracted runtime and existing private parent.
For example, in PowerShell:

```powershell
python -B "D:\Private\inventory-diff\fictional_walkthrough.py" "D:\Private\source-inventory-diff-0.1.0\inventory_diff.py" "D:\Private\inventory-diff"
```

The driver creates a **new** `fictional-demo` child, refuses to reuse it and
keeps it for inspection. It invents CSV/summary metadata without creating or
opening the reported source bodies. All reported hashes are derived from
invented text; **2030 is a fixed fictional timestamp**, not capture evidence.
Original bundled examples are not rewritten or normalized. Choose trusted
quiescent paths and respect device policy; no administrator access is inherently
required for a user-owned Python environment or private directory.

| Case | Exit | Complete JSON status | Meaning |
| --- | ---: | --- | --- |
| `matching` | 0 | `MATCHING_SELECTED_RECORDS` | One identical selected record, no review issue. |
| `differences` | 1 | `DIFFERENCES_REPORTED` | Same path with different declared content hash. |
| `coverage_review` | 1 | `REVIEW_REQUIRED` | Same record, changed directory exclusions and a declared skip. |
| `hash_hint` | 1 | `REVIEW_REQUIRED` | Different names share one declared hash/size; no verified rename. |
| `invalid_control` | 2 | `ERROR` / `JSON_FIELDS_INVALID` | Required summary fields are missing. |

The block independently constructs each entire expected JSON value, checks
stderr/exit codes, and compares every control/extra/prior-capture byte, tree
entry and runtime hash after each process. Its 60-second child timeout is a
driver deadline, not a CLI I/O deadline. It prints fictional structured results
to stdout; any captured file is your caller's responsibility.

```python
import csv
import hashlib
import io
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

STAMP = "2030-01-01T00:00:00+00:00"  # Fixed fictional metadata only.
HEADERS = ["path", "path_escaped", "bytes", "modified_utc", "sha256", "status"]
FLAGS = dict.fromkeys((
    "roots_scanned", "inventoried_files_opened", "files_modified",
    "files_deleted", "renames_verified", "canonical_copy_selected",
    "authenticity_verified", "scope_equivalence_verified",
    "tree_metadata_compared", "network_probed",
), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def fictional_record(path, text):
    data = text.encode("utf-8")
    return dict(path=path, bytes=len(data), sha256=sha(data), modified_utc=STAMP)


def create_run(name, records, *, coverage_change=False, invalid=False):
    directory = WORK / name
    directory.mkdir(mode=0o700)
    text = io.StringIO(newline="")
    writer = csv.writer(text, lineterminator="\r\n")
    writer.writerow(HEADERS)
    for record in records:
        writer.writerow([
            record["path"], "false", record["bytes"], STAMP,
            record["sha256"], "ok",
        ])
    raw_csv = text.getvalue().encode("utf-8")
    top = {}
    for record in records:
        first = record["path"].split("/", 1)[0]
        top[first] = top.get(first, 0) + 1
    summary = dict(
        schema_version="outlands.source_inventory.v1",
        label="fictional", created_at_utc=STAMP,
        coverage="selected_regular_files_only",
        file_count=len(records), hashed_file_count=len(records),
        total_bytes=sum(record["bytes"] for record in records),
        top_level_counts=top,
        skipped=dict(directories=int(coverage_change), files=0, links=0, nonregular=0),
        files_csv_sha256=sha(raw_csv),
        path_encoding="Remove one leading apostrophe only when path_escaped is true.",
        limits=dict(max_files=10000, max_file_bytes=67108864,
                    max_total_bytes=268435456, max_entries=10000),
        default_excluded_directories=[".git"],
        default_excluded_suffixes=[".log"],
    )
    if coverage_change:
        summary["additional_excluded_directories"] = ["fictional-cache"]
    if invalid:
        summary = {}
    raw_summary = (json.dumps(summary, ensure_ascii=True, sort_keys=True) + "\n").encode()
    write_new(directory / "files.csv", raw_csv)
    write_new(directory / "summary.json", raw_summary)
    # Extras are intentionally outside the comparator's four-file input scope.
    write_new(directory / "tree.txt", b"FICTIONAL_EXTRA_TREE_NOT_A_COMPARISON_INPUT\n")
    return directory


old = fictional_record("docs/note.txt", "Fictional note A\n")
changed = fictional_record("docs/note.txt", "Fictional note B\n")
renamed = fictional_record("docs/renamed-note.txt", "Fictional note A\n")
before = create_run("before", [old])
after = create_run("after", [changed])
coverage = create_run("coverage", [old], coverage_change=True)
hint = create_run("hint", [renamed])
invalid = create_run("invalid", [old], invalid=True)
write_new(WORK / "prior-capture.txt", b"Fictional previous output must stay unchanged\n")


def snapshot():
    entries = sorted(WORK.rglob("*"))
    tree = [(path.relative_to(WORK).as_posix(), path.is_dir()) for path in entries]
    hashes = {path.relative_to(WORK).as_posix(): sha(path.read_bytes())
              for path in entries if path.is_file()}
    return tree, hashes


def input_hashes(directory):
    return dict(files_csv_sha256=sha((directory / "files.csv").read_bytes()),
                summary_json_sha256=sha((directory / "summary.json").read_bytes()))


def metadata(record):
    return {key: record[key] for key in ("bytes", "sha256", "modified_utc")}


def row(path, classification, left, right):
    return dict(path=path, classification=classification,
                before=None if left is None else metadata(left),
                after=None if right is None else metadata(right))


def expected(right, *, status, counts, rows, coverage_changed=False, hints=None):
    coverage_issues = ["DIRECTORY_EXCLUSIONS_DIFFER"] if coverage_changed else []
    issues = coverage_issues + (["SKIPPED_ENTRIES_PRESENT"] if coverage_changed else [])
    if hints:
        issues.append("HASH_SIZE_GROUP_HINTS_PRESENT")
    return dict(
        schema_version="outlands.inventory_diff.v1", status=status,
        scope="SUPPLIED_SELECTED_REGULAR_FILE_RECORDS_ONLY", **FLAGS,
        counts=dict(before=1, after=1, **counts), issues=issues,
        coverage=dict(
            declarations_match=not coverage_changed, issues=coverage_issues,
            skipped_before=dict(directories=0, files=0, links=0, nonregular=0),
            skipped_after=dict(directories=int(coverage_changed), files=0,
                               links=0, nonregular=0),
        ),
        input_hashes=dict(before=input_hashes(before), after=input_hashes(right)),
        rows=rows, casefold_ambiguities=[], hash_size_groups=hints or [],
        digest_size_conflicts=[],
    )


matching_counts = dict(only_in_before=0, only_in_after=0,
                       hash_or_size_changed=0, mtime_only_changed=0, unchanged=1)
matching_rows = [row(old["path"], "UNCHANGED", old, old)]
cases = [
    ("matching", before, 0, expected(before, status="MATCHING_SELECTED_RECORDS",
                                     counts=matching_counts, rows=matching_rows)),
    ("differences", after, 1, expected(
        after, status="DIFFERENCES_REPORTED",
        counts=dict(only_in_before=0, only_in_after=0, hash_or_size_changed=1,
                    mtime_only_changed=0, unchanged=0),
        rows=[row(old["path"], "HASH_OR_SIZE_CHANGED", old, changed)],
    )),
    ("coverage_review", coverage, 1, expected(
        coverage, status="REVIEW_REQUIRED", counts=matching_counts,
        rows=matching_rows, coverage_changed=True,
    )),
    ("hash_hint", hint, 1, expected(
        hint, status="REVIEW_REQUIRED",
        counts=dict(only_in_before=1, only_in_after=1, hash_or_size_changed=0,
                    mtime_only_changed=0, unchanged=0),
        rows=[row(old["path"], "ONLY_IN_BEFORE", old, None),
              row(renamed["path"], "ONLY_IN_AFTER", None, renamed)],
        hints=[dict(sha256=old["sha256"], bytes=old["bytes"],
                    before_paths=[old["path"]], after_paths=[renamed["path"]])],
    )),
    ("invalid_control", invalid, 2,
     dict(status="ERROR", code="JSON_FIELDS_INVALID", **FLAGS)),
]

original = snapshot()
runtime_hash = sha(SCRIPT.read_bytes())
environment = os.environ.copy()
environment["PYTHONDONTWRITEBYTECODE"] = "1"
results = []
for name, right, exit_code, complete_expected in cases:
    completed = subprocess.run(
        [sys.executable, "-B", str(SCRIPT), "--before", str(before), "--after", str(right)],
        cwd=WORK, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="strict", timeout=60,
    )
    assert completed.returncode == exit_code, (name, "EXIT_MISMATCH")
    assert completed.stderr == "", (name, "UNEXPECTED_STDERR")
    assert completed.stdout.endswith("\n"), (name, "INCOMPLETE_STDOUT")
    actual = json.loads(completed.stdout)
    assert actual == complete_expected, (name, "FULL_JSON_MISMATCH")
    assert str(WORK) not in completed.stdout, (name, "LOCAL_ROOT_DISCLOSED")
    assert "FICTIONAL_EXTRA_TREE_NOT_A_COMPARISON_INPUT" not in completed.stdout
    assert snapshot() == original, (name, "CONTROL_TREE_OR_PRIOR_OUTPUT_CHANGED")
    assert sha(SCRIPT.read_bytes()) == runtime_hash, (name, "RUNTIME_CHANGED")
    results.append(dict(case=name, exit_code=completed.returncode, report=actual))

print(json.dumps(dict(
    cases=results, input_controls_tree_prior_output_and_runtime_bytes_preserved=True,
), ensure_ascii=True, sort_keys=True, indent=2))
```

The driver checks sampled byte/tree preservation, not access times, every OS
property, ACL privacy or concurrent writers. Its file modes request private
POSIX permissions where supported; Windows/Python/ACL behavior determines the
actual access policy. The code is for a new trusted owned directory, without a
hostile-filesystem or race guarantee. It has no cleanup/rollback; inspect its
retained fictional work before removing it yourself.

A matching result concerns selected records only. A CSV plus its summary hash
can be replaced consistently. Coverage declarations and reported content hashes
are not independently verified, and a shared hash/size is only a grouping hint.
Nothing here establishes equivalent roots, complete capture, a verified rename,
a canonical/original copy, permission to delete, privacy, licensing or release
readiness. Real names/digests/times/results remain private.

Exit 130 means interruption; output capture may be partial. Require complete
JSON and the actual exit/status. Caller redirection can overwrite captures even
though the comparator has no output writer. See the bounds and filesystem limits
in [README.md](README.md), [private workspace](docs/PRIVATE-WORKSPACE.md),
[qualification](docs/QUALIFICATION.md) and [provenance](docs/PROVENANCE.md).
