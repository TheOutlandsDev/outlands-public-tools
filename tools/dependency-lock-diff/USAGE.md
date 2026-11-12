# Fictional lock comparison walkthrough

Extract the [0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/dependency-lock-diff-v0.1.0)
into a fresh directory. Select normal Python 3.12–3.15; qualification selects
3.15.2 for that minor. The CLI needs only `lock_diff.py`, without pip packages,
validator modules, network, model, account or package installation.

Create an existing user-owned private parent outside source. Save the single
Python block below as `fictional_walkthrough.py` there and run it unchanged
with two absolute arguments: extracted script and existing private parent.
For example, in PowerShell:

```powershell
python -B "D:\Private\lock-diff\fictional_walkthrough.py" "D:\Private\dependency-lock-diff-0.1.0\lock_diff.py" "D:\Private\lock-diff"
```

The driver creates a **new** `fictional-demo` child, refuses to reuse it and
retains it for inspection. Names, versions, comments and artifact hashes are
invented declarations. No actual package is downloaded, installed, imported,
resolved or verified; these locks are not installation recommendations.
Original bundled examples are not rewritten or normalized. Use trusted
quiescent paths and respect device policy; user-owned Python/private directories
do not inherently require administrator access.

| Case | Exit | Complete JSON status | Meaning |
| --- | ---: | --- | --- |
| `matching` | 0 | `MATCHING_LOCK_RECORDS` | Four selected declarations match. |
| `text_equivalent` | 0 | `MATCHING_LOCK_RECORDS` | Comments/BOM/CRLF/hash case change raw bytes only. |
| `version_text` | 1 | `LOCK_DIFFERENCES_REPORTED` | `1.0` versus `1.0.0`, with the same declared hash. |
| `hash_only` | 1 | `LOCK_DIFFERENCES_REPORTED` | Same version, different declared hash. |
| `mixed_changes` | 1 | `LOCK_DIFFERENCES_REPORTED` | All five classifications, including a version/hash change. |
| `invalid_lock` | 2 | `ERROR` / `LOCK_LINE_INVALID` | Unsupported active requirement syntax. |

The block constructs each complete expected JSON value independently and
checks stderr/exit codes, all lock/extra/prior-capture bytes, tree entries and
the runtime hash after each child process. Its 60-second child timeout is a
driver deadline, not a CLI I/O deadline. It prints fictional structured results
to stdout; any saved capture is a separate caller operation.

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
    "filesystem_scanned", "packages_downloaded", "packages_installed",
    "environment_inspected", "artifacts_verified", "dependencies_resolved",
    "advisories_checked", "upgrade_direction_inferred", "locks_modified",
    "network_probed",
), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


FAKE_A = sha(b"Fictional declared artifact A; no artifact exists")
FAKE_B = sha(b"Fictional declared artifact B; no artifact exists")
before_records = {
    "sample-alpha": dict(version="1.0", sha256=FAKE_A),
    "sample-beta": dict(version="2.0", sha256=FAKE_B),
    "sample-gone": dict(version="1.0", sha256=FAKE_A),
    "sample-stable": dict(version="1.0", sha256=FAKE_B),
}
version_records = {name: dict(value) for name, value in before_records.items()}
version_records["sample-alpha"]["version"] = "1.0.0"
hash_records = {name: dict(value) for name, value in before_records.items()}
hash_records["sample-beta"]["sha256"] = FAKE_A
mixed_records = {
    "sample-alpha": dict(version="1.1", sha256=FAKE_B),
    "sample-beta": dict(version="2.0", sha256=FAKE_A),
    "sample-new": dict(version="0.1", sha256=FAKE_A),
    "sample-stable": dict(version="1.0", sha256=FAKE_B),
}


def lock_bytes(records, *, equivalent=False):
    lines = ["# FICTIONAL_COMMENT_OMITTED_FROM_RESULT", ""]
    for name, value in sorted(records.items()):
        digest = value["sha256"].upper() if equivalent else value["sha256"]
        lines.extend([name + "==" + value["version"] + " " + chr(92),
                      "    --hash=sha256:" + digest])
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    if equivalent:
        raw = b"\xef\xbb\xbf# Another invented comment\r\n" + raw.replace(b"\n", b"\r\n")
    return raw


paths = {}
for name, raw in (
    ("before", lock_bytes(before_records)),
    ("text-equivalent", lock_bytes(before_records, equivalent=True)),
    ("version-text", lock_bytes(version_records)),
    ("hash-only", lock_bytes(hash_records)),
    ("mixed", lock_bytes(mixed_records)),
    ("invalid", b"sample-alpha>=1.0\n"),
):
    paths[name] = WORK / (name + ".lock")
    write_new(paths[name], raw)
write_new(WORK / "unrelated.txt", b"FICTIONAL_EXTRA_NOT_A_SELECTED_LOCK\n")
write_new(WORK / "prior-capture.txt", b"Fictional previous output must stay unchanged\n")


def snapshot():
    entries = sorted(WORK.rglob("*"))
    tree = [(path.relative_to(WORK).as_posix(), path.is_dir()) for path in entries]
    hashes = {path.relative_to(WORK).as_posix(): sha(path.read_bytes())
              for path in entries if path.is_file()}
    return tree, hashes


def row(name, kind, left, right, version_changed=False, hash_changed=False):
    return dict(name=name, classification=kind, before=left, after=right,
                version_text_changed=version_changed, hash_changed=hash_changed)


def counts(*, only_before=0, only_after=0, versions=0, hashes=0, unchanged=0):
    return dict(before=4, after=4, only_in_before=only_before,
                only_in_after=only_after, version_text_changed=versions,
                hash_only_changed=hashes, unchanged=unchanged)


def expected(right_path, status, count_values, rows):
    return dict(
        schema_version="outlands.lock_diff.v1", status=status,
        scope="SUPPORTED_LOCK_DECLARATIONS_ONLY", **FLAGS,
        counts=count_values, rows=rows,
        input_sha256=dict(before=sha(paths["before"].read_bytes()),
                          after=sha(right_path.read_bytes())),
    )


matching_rows = [row(name, "UNCHANGED", value, value)
                 for name, value in sorted(before_records.items())]
version_rows = [
    row("sample-alpha", "VERSION_TEXT_CHANGED", before_records["sample-alpha"],
        version_records["sample-alpha"], True, False),
    *[row(name, "UNCHANGED", before_records[name], version_records[name])
      for name in ("sample-beta", "sample-gone", "sample-stable")],
]
hash_rows = [
    row("sample-alpha", "UNCHANGED", before_records["sample-alpha"], hash_records["sample-alpha"]),
    row("sample-beta", "HASH_ONLY_CHANGED", before_records["sample-beta"],
        hash_records["sample-beta"], False, True),
    *[row(name, "UNCHANGED", before_records[name], hash_records[name])
      for name in ("sample-gone", "sample-stable")],
]
mixed_rows = [
    row("sample-alpha", "VERSION_TEXT_CHANGED", before_records["sample-alpha"],
        mixed_records["sample-alpha"], True, True),
    row("sample-beta", "HASH_ONLY_CHANGED", before_records["sample-beta"],
        mixed_records["sample-beta"], False, True),
    row("sample-gone", "ONLY_IN_BEFORE", before_records["sample-gone"], None, None, None),
    row("sample-new", "ONLY_IN_AFTER", None, mixed_records["sample-new"], None, None),
    row("sample-stable", "UNCHANGED", before_records["sample-stable"], mixed_records["sample-stable"]),
]
cases = [
    ("matching", paths["before"], 0, expected(
        paths["before"], "MATCHING_LOCK_RECORDS", counts(unchanged=4), matching_rows)),
    ("text_equivalent", paths["text-equivalent"], 0, expected(
        paths["text-equivalent"], "MATCHING_LOCK_RECORDS", counts(unchanged=4), matching_rows)),
    ("version_text", paths["version-text"], 1, expected(
        paths["version-text"], "LOCK_DIFFERENCES_REPORTED", counts(versions=1, unchanged=3), version_rows)),
    ("hash_only", paths["hash-only"], 1, expected(
        paths["hash-only"], "LOCK_DIFFERENCES_REPORTED", counts(hashes=1, unchanged=3), hash_rows)),
    ("mixed_changes", paths["mixed"], 1, expected(
        paths["mixed"], "LOCK_DIFFERENCES_REPORTED",
        counts(only_before=1, only_after=1, versions=1, hashes=1, unchanged=1), mixed_rows)),
    ("invalid_lock", paths["invalid"], 2, dict(status="ERROR", code="LOCK_LINE_INVALID", **FLAGS)),
]

original = snapshot()
runtime_hash = sha(SCRIPT.read_bytes())
environment = os.environ.copy()
environment["PYTHONDONTWRITEBYTECODE"] = "1"
results = []
for name, right, exit_code, complete_expected in cases:
    completed = subprocess.run(
        [sys.executable, "-B", str(SCRIPT), "--before", str(paths["before"]), "--after", str(right)],
        cwd=WORK, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="strict", timeout=60,
    )
    assert completed.returncode == exit_code, (name, "EXIT_MISMATCH")
    assert completed.stderr == "", (name, "UNEXPECTED_STDERR")
    assert completed.stdout.endswith("\n"), (name, "INCOMPLETE_STDOUT")
    actual = json.loads(completed.stdout)
    assert actual == complete_expected, (name, "FULL_JSON_MISMATCH")
    assert str(WORK) not in completed.stdout, (name, "LOCAL_ROOT_DISCLOSED")
    assert "FICTIONAL_COMMENT_OMITTED_FROM_RESULT" not in completed.stdout
    assert "FICTIONAL_EXTRA_NOT_A_SELECTED_LOCK" not in completed.stdout
    assert snapshot() == original, (name, "INPUT_TREE_OR_PRIOR_OUTPUT_CHANGED")
    assert sha(SCRIPT.read_bytes()) == runtime_hash, (name, "RUNTIME_CHANGED")
    results.append(dict(case=name, exit_code=completed.returncode, report=actual))

assert results[0]["report"]["input_sha256"]["before"] != results[1]["report"]["input_sha256"]["after"]
print(json.dumps(dict(
    cases=results, input_locks_tree_prior_output_and_runtime_bytes_preserved=True,
), ensure_ascii=True, sort_keys=True, indent=2))
```

The driver checks sampled byte/tree preservation, not access times, every OS
property, ACL privacy or concurrent writers. Modes request private POSIX
permissions where supported; actual Windows/Python/ACL behavior determines
access policy. This is new trusted owned work, without a hostile-filesystem or
race guarantee. There is no cleanup/rollback; inspect retained fictional work
before removing it yourself.

`1.0` and `1.0.0` are text differences here, without a claim of upgrade,
downgrade, chronology or compatibility. Hash-only changes describe declarations,
without malware/advisory judgments or artifact verification. Matching records
do not establish installed state, authentic artifacts, availability, licensing,
platform coverage, reproducibility, safe installation or permission to publish.
Real names/versions/hashes/comments/results remain private.

Exit 130 means interruption; captured output may be partial. Require complete
JSON and the actual exit/status. Caller redirection can overwrite captures even
though the comparator has no output writer. See bounds and filesystem limits
in [README.md](README.md), [private workspace](docs/PRIVATE-WORKSPACE.md),
[qualification](docs/QUALIFICATION.md) and [provenance](docs/PROVENANCE.md).
