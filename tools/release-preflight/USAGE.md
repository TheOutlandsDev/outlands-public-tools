# Fictional local release preflight

Extract the [0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/release-preflight-v0.1.0)
into a fresh folder and select normal Python **3.12–3.15**, with 3.15.2 selected
for that minor in qualification. Keep `preflight.py` and `preflight_windows.py`
adjacent. The portable runtime pair needs only the standard library and OS APIs.
Supply Python separately; no pip distribution, account, service or network is
needed. POSIX retains its original ability to work without loading the Windows
backend; this walkthrough keeps both files for the portable layout.

The commands are `verify`, `plan` and `launcher-check`, with explicitly selected
candidate/manifest/pin arguments. `plan` also selects current files;
`launcher-check` also selects a specification and its independent pin.
`--help` is static. There is **no `--version` option**. Console output is a compact
JSON summary. Optional `--report` writes a new private full JSON report; it
requires an existing parent outside protected source and input roots.

A verified manifest means byte agreement with its supplied pin, not trusted
authorship, licensing, malware absence or safe application behavior. Obtain real
pins through a separately trusted review or release channel. Hashing an unchecked
download does not authenticate it. The driver below computes hashes only from
its newly authored fixture bytes.

The tool does not download, install, apply, copy, delete, start, stop or execute
an input. A plan is an observation, not a reservation or deployment transaction.
Launcher acceptance means listed bytes and configuration structure passed;
executable format, permissions, arguments, dependencies and runtime behavior
remain untested. Every console and report value states `execution_performed:
false`. Keep actual inventories, paths, hashes, arguments and reports private.

## Run the complete fictional exercise

Create an existing user-owned private parent outside extracted source. Save the
single Python block below as `fictional_walkthrough.py` there and run it unchanged
with two absolute arguments: extracted script and existing private parent.
PowerShell, with fictional paths:

```powershell
python -B 'D:\Private\preflight-review\fictional_walkthrough.py' 'D:\Source\release-preflight-0.1.0\preflight.py' 'D:\Private\preflight-review'
```

Ubuntu:

```sh
python3.12 -B '/absolute/private/preflight-review/fictional_walkthrough.py' '/absolute/source/release-preflight-0.1.0/preflight.py' '/absolute/private/preflight-review'
```

The driver creates a **new** `fictional-demo` child and refuses to reuse it.
It writes eleven initial fictional files: three candidate files, two selected
current files, one unselected current file, four metadata controls and one prior
capture. Three successful commands create separate new reports, leaving fourteen
retained files. All bytes, names, arguments and pins are authored examples.
The candidate script deliberately raises if executed; it is only hashed.

| Case | Exit | Complete JSON summary | Private report |
| --- | ---: | --- | --- |
| `verify` | 0 | `VERIFIED`, three listed files verified | New full verify report |
| `plan` | 0 | `VERIFIED`, one `REPLACE`, one `ADD`, one `UNCHANGED` | New full plan, hashes and recovery guidance |
| `launcher` | 0 | `VERIFIED`, two arguments, runtime `NOT_TESTED` | New full launcher report; no argument values |
| `wrong_pin` | 2 | `ERROR` / `PIN_MISMATCH` | None |
| `existing_report` | 2 | `ERROR` / `PREFLIGHT_REFUSED_OR_FAILED` | Prior capture preserved |
| `invalid_manifest` | 2 | `ERROR` / `INVALID_MANIFEST` | None |
| `invalid_launcher` | 2 | `ERROR` / `INVALID_LAUNCH_SPEC` | None |

The block checks the **entire** JSON summary and report, exact report bytes,
actual exits/stderr and input/current/candidate/control/prior-output/runtime
preservation after every process. The driver does not apply a plan or run a
payload. Its 90-second timeout is a driver choice, not a tool I/O deadline.

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
BACKEND = SCRIPT.with_name("preflight_windows.py")
if not BACKEND.is_file():
    raise RuntimeError("SELECT_ADJACENT_PORTABLE_RUNTIME_PAIR")
if PRIVATE_PARENT.is_relative_to(SCRIPT.parent):
    raise RuntimeError("PRIVATE_PARENT_MUST_BE_OUTSIDE_SOURCE")
WORK = PRIVATE_PARENT / "fictional-demo"
WORK.mkdir(mode=0o700, exist_ok=False)
CANDIDATE, CURRENT, CONTROLS, REPORTS = [WORK / name for name in
                                       ("candidate", "current", "controls", "reports")]
for folder in (CANDIDATE, CURRENT, CONTROLS, REPORTS):
    folder.mkdir()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def metadata(data):
    return dict(size=len(data), sha256=sha(data))


def encoded(value):
    return (json.dumps(value, ensure_ascii=True) + "\n").encode("utf-8")


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


payloads = {
    "docs/readme.txt": b"Fictional release notes\n",
    "bin/component.py": b"raise RuntimeError('FICTIONAL_PAYLOAD_EXECUTED')\n",
    "data/empty.bin": b"",
}
current_bytes = {
    "docs/readme.txt": payloads["docs/readme.txt"],
    "bin/component.py": b"Fictional previous component\n",
    "unselected/private.py": b"raise RuntimeError('FICTIONAL_UNSELECTED_EXECUTED')\n",
}
for root, values in ((CANDIDATE, payloads), (CURRENT, current_bytes)):
    for name, data in values.items():
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_new(destination, data)
manifest_value = dict(schema_version=1, inventory=[
    dict(path=name, **metadata(data)) for name, data in payloads.items()
])
launcher_value = dict(schema_version=1, executable="bin/component.py",
                      working_directory=".", arguments=["--fictional", "FICTIONAL_PRIVATE_ARGUMENT"])
MANIFEST, SPEC = CONTROLS / "manifest.json", CONTROLS / "launcher.json"
INVALID_MANIFEST, INVALID_SPEC = CONTROLS / "invalid-manifest.json", CONTROLS / "invalid-launcher.json"
for path, value in ((MANIFEST, manifest_value), (SPEC, launcher_value),
                    (INVALID_MANIFEST, dict(manifest_value, schema_version=True)),
                    (INVALID_SPEC, dict(launcher_value, environment={}))):
    write_new(path, encoded(value))
PIN, SPEC_PIN = sha(MANIFEST.read_bytes()), sha(SPEC.read_bytes())
PRIOR = REPORTS / "prior-capture.json"
write_new(PRIOR, b"Fictional previous capture must stay unchanged\n")

verify_report = dict(schema_version=1, operation="verify", execution_performed=False,
                     manifest_sha256=PIN, files_verified=3)
plan_report = dict(
    schema_version=1, operation="plan", execution_performed=False, manifest_sha256=PIN,
    counts=dict(REPLACE=1, ADD=1, UNCHANGED=1), files=[
        dict(path="bin/component.py", action="REPLACE", expected=metadata(payloads["bin/component.py"]),
             current=metadata(current_bytes["bin/component.py"])),
        dict(path="data/empty.bin", action="ADD", expected=metadata(payloads["data/empty.bin"]), current=None),
        dict(path="docs/readme.txt", action="UNCHANGED", expected=metadata(payloads["docs/readme.txt"]),
             current=metadata(current_bytes["docs/readme.txt"])),
    ], unlisted_current_files="NOT_INSPECTED_OR_SELECTED", recovery=[
        "Confirm a maintenance window and application-consistent stopped state independently.",
        "Make and verify a private backup; retain its manifest digest separately.",
        "Review this plan and recheck both trees before applying changes with another tool.",
        "Verify the resulting candidate version before starting the application.",
        "If recovery is needed, restore the verified backup to a new directory and review it before switching.",
    ],
)
launcher_report = dict(schema_version=1, operation="launcher-check", execution_performed=False,
                       manifest_sha256=PIN, launch_spec_sha256=SPEC_PIN, argument_count=2,
                       executable_listed_and_verified=True, working_directory_exists=True,
                       runtime_acceptance="NOT_TESTED")


def summary(report):
    return dict(status="VERIFIED", **{key: value for key, value in report.items()
                                      if key not in ("files", "recovery")})


def error(code):
    return dict(status="ERROR", code=code, execution_performed=False)


def selected(operation, manifest=MANIFEST, pin=PIN):
    return [operation, "--candidate", str(CANDIDATE), "--manifest", str(manifest), "--manifest-sha", pin]


cases = [
    ("verify", selected("verify") + ["--report", str(REPORTS / "verify.json")], 0,
     summary(verify_report), REPORTS / "verify.json", verify_report),
    ("plan", selected("plan") + ["--current", str(CURRENT), "--report", str(REPORTS / "plan.json")], 0,
     summary(plan_report), REPORTS / "plan.json", plan_report),
    ("launcher", selected("launcher-check") + ["--spec", str(SPEC), "--spec-sha", SPEC_PIN,
                                                "--report", str(REPORTS / "launcher.json")], 0,
     summary(launcher_report), REPORTS / "launcher.json", launcher_report),
    ("wrong_pin", selected("verify", pin="0" * 64), 2, error("PIN_MISMATCH"), None, None),
    ("existing_report", selected("verify") + ["--report", str(PRIOR)], 2,
     error("PREFLIGHT_REFUSED_OR_FAILED"), None, None),
    ("invalid_manifest", selected("verify", INVALID_MANIFEST, sha(INVALID_MANIFEST.read_bytes())), 2,
     error("INVALID_MANIFEST"), None, None),
    ("invalid_launcher", selected("launcher-check") + ["--spec", str(INVALID_SPEC), "--spec-sha", sha(INVALID_SPEC.read_bytes())], 2,
     error("INVALID_LAUNCH_SPEC"), None, None),
]


def snapshot_tree():
    entries = sorted(WORK.rglob("*"))
    tree = {path.relative_to(WORK).as_posix() for path in entries}
    hashes = {path.relative_to(WORK).as_posix(): sha(path.read_bytes())
              for path in entries if path.is_file()}
    return tree, hashes


runtime_bytes = {SCRIPT: SCRIPT.read_bytes(), BACKEND: BACKEND.read_bytes()}
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
results = []
for name, arguments, exit_code, complete_summary, report_path, complete_report in cases:
    tree_before, hashes_before = snapshot_tree()
    completed = subprocess.run(
        [sys.executable, "-B", "-s", "-X", "utf8", str(SCRIPT), *arguments],
        cwd=WORK, env=environment, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=90,
    )
    assert completed.returncode == exit_code, (name, "EXIT_MISMATCH")
    assert completed.stderr == "", (name, "UNEXPECTED_STDERR")
    assert completed.stdout.endswith("\n") and len(completed.stdout.splitlines()) == 1
    actual = json.loads(completed.stdout)
    assert actual == complete_summary, (name, "FULL_SUMMARY_MISMATCH")
    assert str(WORK) not in completed.stdout.replace("\\\\", "\\")
    assert "component.py" not in completed.stdout and "FICTIONAL_PRIVATE_ARGUMENT" not in completed.stdout
    tree_after, hashes_after = snapshot_tree()
    expected_new = {report_path.relative_to(WORK).as_posix()} if report_path is not None else set()
    assert tree_after == tree_before | expected_new, (name, "UNEXPECTED_TREE_CHANGE")
    assert all(hashes_after[key] == value for key, value in hashes_before.items()), (name, "PRIOR_BYTES_CHANGED")
    if report_path is not None:
        assert report_path.relative_to(WORK).as_posix() not in tree_before
        assert report_path.read_bytes() == (json.dumps(complete_report, indent=2, ensure_ascii=True) + "\n").encode()
        assert json.loads(report_path.read_bytes()) == complete_report
    assert all(path.read_bytes() == data for path, data in runtime_bytes.items()), (name, "RUNTIME_CHANGED")
    assert not list(WORK.rglob("*.pyc"))
    results.append(dict(case=name, exit_code=completed.returncode, summary=actual, report=complete_report))

print(json.dumps(dict(
    cases=results, input_candidate_current_controls_prior_outputs_and_runtime_bytes_preserved=True,
), ensure_ascii=True, sort_keys=True, indent=2))
```

The pins above are computed from the driver's own newly authored data, solely to
exercise exact matching. They are not independent authentication of an external
candidate. All three new reports are retained privately. The prior capture is
neither replaced nor treated as a successful new report.

## Source boundary and checked scope

In a standalone layout the source directory containing `preflight.py` is
protected from report writes. In the literal collection layout
`tools/release-preflight/preflight.py`, the entire containing collection is
protected. This is a structural directory-name rule, not Git-root discovery.
Choose private outputs outside both source and input roots; do not rely on an
ancestor of a standalone extraction becoming implicitly protected. Candidate
and current roots must be separate and nonnested. The manifest and launcher
specification must be external to the candidate.

The candidate must exactly match listed files and their parent directories.
Extra files or empty directories, missing or changed bytes, case collisions,
file/directory collisions, links, reparse points and hardlinks are refused.
Only listed current paths are read and considered for `ADD`, `REPLACE` or
`UNCHANGED`; unlisted current data is not enumerated or selected for removal.
Plans contain expected/current hashes, not prior contents, and cannot undo an
update. Read the full [manifest and launcher contract](README.md) and preserved
[I/O behavior](IO-SAFETY.md).

Metadata is at most 1 MiB per input; manifests allow 4096 files, each at most
256 MiB and 1 GiB combined. Enumeration allows 8192 entries; relative paths
allow 240 characters and 32 parts. Selected current files have the same byte
limits. Reads can repeat; limits apply per pass. Launcher arguments allow 64
strings, 2048 characters each and 8192 total. These are not complete CPU, memory,
storage or blocked-I/O deadlines. No shell, environment expansion, executable
search, service management or process control is supported.

## Privacy and remaining limits

Console summaries omit filenames, absolute roots and launcher argument values.
Full reports retain relative filenames, content hashes, classifications and
recovery guidance. Neither pins nor fixed errors anonymize operator data or
library tracebacks. Requested file modes depend on OS/Python/inherited
permissions; they do not establish ACL privacy or encryption.

Reports require a new file and existing parent, with no overwrite or automatic
parent creation. Short writes are completed and reports are flushed/read back.
A failed write, flush, readback or final guard can leave a partial or complete
**unconfirmed new** report. Existence, parseability or a success-looking report
body does not prove a successful command. Retain failed outputs privately;
retrying never replaces an existing report. The driver checks byte/tree
preservation rather than access times, every OS property or confidentiality.

Windows uses checked native ancestors and file identities, rejects observed
reparse/stream/short-name aliases and restricts selected path forms. Actual
fictional probes on Python 3.12.7 and 3.15.2 refused leaf and parent trailing
dot/space spellings for candidate, current, manifest, specification and report
selections before creating those aliased reports. Canonical selections and
external new reports succeeded. These observations do not establish a universal
alias, remote-storage or hostile-filesystem guarantee. POSIX retains its
no-follow/nonblocking facilities and sampled ancestry/descriptor checks.

Use stable quiescent trusted local trees and one operator. Handles and sampled
checks are not an atomic multi-file snapshot, application-consistent backup or
race-free deployment. Remote/cloud/live storage, arbitrary mounts, rebinding,
blocked I/O, all-stream inspection, ACL privacy, power loss and live integration
remain unverified. Windows handled interruption is exit 130 with
`PREFLIGHT_INTERRUPTED`; POSIX interruption propagation remains separate.
Require complete JSON and actual exits before accepting any output.

No input, output or test authorizes an update, execution or publication of an
actual package. Establish a maintenance window and consistent stopped state,
verify a private backup and independently authorize another tool before applying
changes. This guide performs none of those actions. See the [private workspace
guide](docs/PRIVATE-WORKSPACE.md), [qualification boundary](docs/QUALIFICATION.md)
and [provenance](docs/PROVENANCE.md).
