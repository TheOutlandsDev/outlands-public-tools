# Fictional prerequisite-presence walkthrough

Extract the [0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/environment-contract-checker-v0.1.0)
into a fresh folder and select normal Python **3.12–3.15**, with 3.15.2 selected
for that minor in qualification. Keep `environment_check.py` and
`environment_windows.py` adjacent and the generator at `examples/make_fixture.py`.
The checker pair and separate generator need only the standard library and OS
APIs. Supply Python separately; no pip distribution, account or service is
required. POSIX retains its original ability to use the checker without loading
the Windows backend; the walkthrough keeps the portable source layout.

The checker accepts `--contract`, optional `--root`, repeated explicit
`--program-dir`, optional `--observations` and optional new `--report`. Its
`--help` and `--version` are static. The generator accepts `--destination` and
`--help`; it has **no `--version` option**. Generator output is a newly created
fictional fixture, not installation or configuration of another application.

`ALL_PRESENT` means only that the selected metadata-presence requirements were
present. It does not establish a runnable executable, usable permissions,
compatible version or ready environment. The checker reads selected controls
and its new report readback, never target/program bodies. It runs no programs,
imports no selected module, installs nothing, changes no PATH/PATHEXT and probes
no service. A supplied operator `true` or `false` stays `UNKNOWN` and unverified.
Keep actual prerequisites, IDs, selections and captures private.

## Run the complete fictional exercise

Create an existing user-owned private parent outside extracted source. Save the
single Python block below as `fictional_walkthrough.py` there and run it unchanged
with two absolute arguments: checker script and existing private parent.
PowerShell, with fictional paths:

```powershell
python -B 'D:\Private\environment-review\fictional_walkthrough.py' 'D:\Source\environment-contract-checker-0.1.0\environment_check.py' 'D:\Private\environment-review'
```

Ubuntu:

```sh
python3.12 -B '/absolute/private/environment-review/fictional_walkthrough.py' '/absolute/source/environment-contract-checker-0.1.0/environment_check.py' '/absolute/private/environment-review'
```

The driver creates a **new** `fictional-demo` child and refuses to reuse it.
It authors four controls and one prior capture, then calls the actual generator
once to create its two known fictional files and three child directories. The
generated program would exit 73 if deliberately run; **do not run it**. Four
checker calls create separate new reports. Eleven files remain for private
inspection: five initial files, two generated files and four reports.

| Case | Tool | Exit | Complete JSON outcome |
| --- | --- | ---: | --- |
| `generator_create` | Generator | 0 | `CREATED`, two files/three child directories, fixture not executed |
| `all_present` | Checker | 0 | Three `PRESENT` metadata checks, versions unverified |
| `missing_program` | Checker | 1 | Two present checks; the explicitly selected empty program directory yields `MISSING` |
| `reported_true` | Checker | 1 | Three present checks; operator true remains `UNKNOWN` |
| `reported_false` | Checker | 1 | Three present checks; operator false remains `UNKNOWN` |
| `existing_report` | Checker | 2 | `INPUT_OR_REPORT_FAILED`; prior capture preserved |
| `existing_fixture` | Generator | 2 | `FIXTURE_REFUSED_OR_FAILED`; generated fixture preserved |

Every checker report below is the entire checker JSON value, with exact byte
encoding checked. The driver reads its own authored/generated fixture bytes to
verify preservation; the checker remains metadata-only. Complete stdout JSON,
actual exits/stderr, each prior tree/file and all three runtime sources are
checked after every process. The 90-second timeout belongs to the driver, not
to a checker guarantee that can interrupt blocked OS I/O.

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
SCRIPT, PRIVATE_PARENT = SCRIPT.resolve(), PRIVATE_PARENT.resolve()
SOURCE = SCRIPT.parent
BACKEND = SOURCE / "environment_windows.py"
GENERATOR = SOURCE / "examples" / "make_fixture.py"
if not BACKEND.is_file() or not GENERATOR.is_file():
    raise RuntimeError("SELECT_CHECKER_PAIR_AND_ADJACENT_EXAMPLE_GENERATOR")
BOUNDARY = SOURCE.parent.parent if SOURCE.name == "environment-contract-checker" and SOURCE.parent.name == "tools" else SOURCE
if PRIVATE_PARENT.is_relative_to(BOUNDARY):
    raise RuntimeError("PRIVATE_PARENT_MUST_BE_OUTSIDE_PROTECTED_SOURCE")
WORK = PRIVATE_PARENT / "fictional-demo"
WORK.mkdir(mode=0o700, exist_ok=False)
CONTROLS, REPORTS = WORK / "controls", WORK / "reports"
CONTROLS.mkdir()
REPORTS.mkdir()
FIXTURE = WORK / "generated-fixture"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=True) + "\n").encode("utf-8")


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


base = dict(schema_version=1, requirements=[
    dict(id="sample_file", kind="file", path="inputs/fictional.txt"),
    dict(id="sample_directory", kind="directory", path="workspace"),
    dict(id="sample_program", kind="program", name="fictional-tool"),
])
observed = dict(schema_version=1, requirements=base["requirements"] + [
    dict(id="platform_review", kind="observation")
])
BASE, OBSERVED = CONTROLS / "contract.json", CONTROLS / "observed-contract.json"
TRUE, FALSE = CONTROLS / "reported-true.json", CONTROLS / "reported-false.json"
for path, value in ((BASE, base), (OBSERVED, observed),
                    (TRUE, dict(schema_version=1, observations=[dict(id="platform_review", satisfied=True)])),
                    (FALSE, dict(schema_version=1, observations=[dict(id="platform_review", satisfied=False)]))):
    write_new(path, encoded(value))
PRIOR = REPORTS / "prior-capture.json"
write_new(PRIOR, b"Fictional previous capture must stay unchanged\n")


def checked(identifier, kind, status, evidence):
    return dict(id=identifier, kind=kind, status=status, evidence=evidence)


def expected(rows):
    counts = {key: sum(row["status"].lower() == key for row in rows)
              for key in ("present", "missing", "unknown", "unsafe")}
    return dict(schema_version=1,
                status="ALL_PRESENT" if counts["present"] == len(rows) else "REVIEW_REQUIRED",
                scope="DECLARED_REQUIREMENTS_ONLY", target_contents_read=False,
                programs_executed=False, versions_verified=False, counts=counts, checks=rows)


present = [checked("sample_file", "file", "PRESENT", "REGULAR_FILE_METADATA"),
           checked("sample_directory", "directory", "PRESENT", "DIRECTORY_METADATA"),
           checked("sample_program", "program", "PRESENT", "PROGRAM_CANDIDATE_METADATA")]
ALL = expected(present)
MISSING = expected(present[:2] + [checked("sample_program", "program", "MISSING", "PROGRAM_NOT_FOUND")])
REPORTED_TRUE = expected(present + [checked("platform_review", "observation", "UNKNOWN", "OPERATOR_REPORTED_TRUE_UNVERIFIED")])
REPORTED_FALSE = expected(present + [checked("platform_review", "observation", "UNKNOWN", "OPERATOR_REPORTED_FALSE_UNVERIFIED")])
CREATED = dict(status="CREATED", files_created=2, child_directories_created=3, fixture_executed=False)

if os.name == "nt":
    program_name = "fictional-tool.cmd"
    program_bytes = b"@echo off\r\nrem Fictional presence fixture; do not execute.\r\nexit /b 73\r\n"
else:
    program_name = "fictional-tool"
    program_bytes = b"#!/bin/sh\n# Fictional presence fixture; do not execute.\nexit 73\n"
fixture_files = {"inputs/fictional.txt": b"Fictional prerequisite input. No user records.\n",
                 "programs/" + program_name: program_bytes}
fixture_tree = {"generated-fixture", "generated-fixture/inputs", "generated-fixture/programs",
                "generated-fixture/workspace", *("generated-fixture/" + name for name in fixture_files)}


def selected(control=BASE, programs=FIXTURE / "programs"):
    return ["--contract", str(control), "--root", str(FIXTURE), "--program-dir", str(programs)]


cases = [
    ("generator_create", "generator", GENERATOR, ["--destination", str(FIXTURE)], 0, CREATED, None),
    ("all_present", "checker", SCRIPT, selected() + ["--report", str(REPORTS / "present.json")], 0, ALL, REPORTS / "present.json"),
    ("missing_program", "checker", SCRIPT, selected(programs=FIXTURE / "workspace") + ["--report", str(REPORTS / "missing.json")], 1, MISSING, REPORTS / "missing.json"),
    ("reported_true", "checker", SCRIPT, selected(OBSERVED) + ["--observations", str(TRUE), "--report", str(REPORTS / "true.json")], 1, REPORTED_TRUE, REPORTS / "true.json"),
    ("reported_false", "checker", SCRIPT, selected(OBSERVED) + ["--observations", str(FALSE), "--report", str(REPORTS / "false.json")], 1, REPORTED_FALSE, REPORTS / "false.json"),
    ("existing_report", "checker", SCRIPT, selected() + ["--report", str(PRIOR)], 2,
     dict(status="ERROR", code="INPUT_OR_REPORT_FAILED", target_contents_read=False, programs_executed=False), None),
    ("existing_fixture", "generator", GENERATOR, ["--destination", str(FIXTURE)], 2,
     dict(status="ERROR", code="FIXTURE_REFUSED_OR_FAILED", fixture_executed=False), None),
]


def snapshot_tree():
    entries = sorted(WORK.rglob("*"))
    return ({path.relative_to(WORK).as_posix() for path in entries},
            {path.relative_to(WORK).as_posix(): sha(path.read_bytes())
             for path in entries if path.is_file()})


runtime_bytes = {path: path.read_bytes() for path in (SCRIPT, BACKEND, GENERATOR)}
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
results = []
for name, tool, script, arguments, exit_code, complete_expected, report_path in cases:
    before_tree, before_hashes = snapshot_tree()
    completed = subprocess.run(
        [sys.executable, "-B", "-s", "-X", "utf8", str(script), *arguments],
        cwd=WORK, env=environment, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=90,
    )
    assert completed.returncode == exit_code, (name, "EXIT_MISMATCH")
    assert completed.stderr == "", (name, "UNEXPECTED_STDERR")
    assert completed.stdout.endswith("\n") and len(completed.stdout.splitlines()) == 1
    actual = json.loads(completed.stdout)
    assert actual == complete_expected, (name, "FULL_JSON_MISMATCH")
    assert str(WORK) not in completed.stdout.replace("\\\\", "\\")
    assert "fictional-tool" not in completed.stdout and "inputs/fictional.txt" not in completed.stdout
    after_tree, after_hashes = snapshot_tree()
    created = fixture_tree if name == "generator_create" else {report_path.relative_to(WORK).as_posix()} if report_path is not None else set()
    assert after_tree == before_tree | created, (name, "UNEXPECTED_TREE_CHANGE")
    assert all(after_hashes[key] == value for key, value in before_hashes.items()), (name, "PRIOR_BYTES_CHANGED")
    if name == "generator_create":
        assert all((FIXTURE / filename).read_bytes() == data for filename, data in fixture_files.items())
        assert all((FIXTURE / directory).is_dir() for directory in ("inputs", "programs", "workspace"))
        if os.name != "nt":
            assert (FIXTURE / "programs" / program_name).stat().st_mode & 0o777 == 0o700
    if report_path is not None:
        assert report_path.relative_to(WORK).as_posix() not in before_tree
        assert report_path.read_bytes() == (json.dumps(complete_expected, indent=2, ensure_ascii=True) + "\n").encode()
        assert json.loads(report_path.read_bytes()) == complete_expected
    assert all(path.read_bytes() == data for path, data in runtime_bytes.items()), (name, "RUNTIME_CHANGED")
    assert not list(WORK.rglob("*.pyc"))
    results.append(dict(case=name, tool=tool, exit_code=completed.returncode,
                        value=actual, report=actual if report_path is not None else None))

print(json.dumps(dict(
    cases=results, controls_targets_programs_prior_outputs_and_runtime_bytes_preserved=True,
), ensure_ascii=True, sort_keys=True, indent=2))
```

The known generated files are inspected only by this driver for byte checks;
none is executed. Reports preserve the checker value, without target paths,
program names or file contents. The prior capture and entire generated fixture
survive both rejected retries. Requested file modes depend on OS/Python/inherited
permissions; they do not prove ACL privacy or encryption. The driver checks
sampled byte/tree preservation, not access times or every OS property. Retained
fictional work is not cleaned up automatically.

## Interpret the prerequisite contract

The contract has exactly integer `schema_version: 1` and **1–128 requirements**.
Supported kinds are `file`, `directory`, `program` and `observation`. IDs match
`[a-z][a-z0-9_-]{0,39}`. File/directory paths are canonical relative forward-slash
names, at most 240 characters/32 parts. Program names are simple bounded
basenames. Unknown fields, duplicate keys/IDs, unsupported kinds, wrong types
and unsafe relative paths are errors. Selected JSON controls may include a BOM;
each is at most **64 KiB**. Observation rows contain only a declared observation
ID and actual Boolean `satisfied`, not raw host/version/account strings.

No root selected means file/directory checks are `UNKNOWN` / `ROOT_NOT_SELECTED`.
No program directories selected means `UNKNOWN` / `PROGRAM_SEARCH_NOT_SELECTED`.
An explicitly selected root must exist as an ordinary directory; an unavailable
root is an error. Missing selected program directories can yield `MISSING`, and
remain excluded report destinations without being silently created. Missing
targets are distinguished from type mismatches, unsafe nodes or uncertain
metadata. Requirement order is preserved in checks.

Only up to **16 explicit program directories** are searched. PATH, PATHEXT,
implicit current-directory search, environment/home expansion and recursive
inventory are absent. Windows uses its fixed `.exe`, `.com`, `.bat`, `.cmd`
suffix rules; POSIX additionally observes execute access. Neither establishes
executable format, permissions sufficient for startup, working dependencies or
correct version. The checker exposes three false flags on results and two on
fixed errors; the generator exposes `fixture_executed: false`.

Operator true/false observations always remain `UNKNOWN`, with distinct fixed
unverified evidence. `ALL_PRESENT` is presence only. Any missing/unknown/unsafe
check produces `REVIEW_REQUIRED`, exit 1; invalid inputs or refused output
produce exit 2. Target probing is capped at 2048 metadata probes with a
five-second budget checked **between** probes. These are not complete CPU,
memory, JSON-depth or blocked-I/O deadlines. See [README.md](README.md) and the
preserved [I/O contract](IO-SAFETY.md) for complete schema and remaining limits.

## Source, path and output boundaries

Both checker reports and generator destinations protect the enclosing module
in a standalone layout. The literal `tools/environment-contract-checker`
collection layout protects the entire containing collection. This is structural
directory-name selection, not Git-root discovery. Checker reports must also
stay outside every selected root and program directory, including missing
selected program scopes. Use new canonical private paths outside protected
source and inputs, with existing ordinary parents.

Windows path behavior is not uniform across interfaces. Actual fictional
Python 3.12.7/3.15.2 probes in both source layouts found:

| Selection | Observed trailing dot/space behavior |
| --- | --- |
| Contract/observation control | Leaf dot/space and parent dot/space were refused. |
| Root/program directory | Leaf dot/space and parent dot were normalized and accepted; parent space was refused. |
| External checker report | Leaf dot/space and parent dot were normalized and created the canonical new report; parent space was refused. |
| External generator fixture | All four tested suffix forms were refused. |
| Source-protected report/fixture | Every tested form stayed refused in both layouts. |

Use fully spelled canonical paths; these observations establish no universal
alias or hostile-filesystem guarantee. Control/report I/O uses native checks
where applicable, while target probing remains metadata-only. The reviewed
Windows report-leaf guard refuses any observed existing leaf before CRT create,
including dangling links. A controlled reparse observation verifies refusal
before `os.open`; real link checks require native fixture capability. Local
symlink privilege absence is not proof that the prior Windows CRT behavior was
reproduced or that every race is prevented.

Reports are new-file-only, without replacement or automatic parent creation.
Write loops, flush and readback checks do not guarantee cleanup: a partial or
complete **unconfirmed new** report can remain after failure. The generator
likewise retains partial new output after failure. Existence, parseability or
success-looking content is not successful completion. Preserve failed output
privately and use a new name after review; retries never replace it.

Use one operator and stable quiescent trusted local paths. Sampled checks and
held handles are not an atomic snapshot, content freeze, race-free sandbox or
live setup validation. Arbitrary mounts, drive rebinding, remote/cloud storage,
all-stream inspection, blocked I/O, ACL privacy and power loss remain outside
qualification. Metadata calls on network-backed storage can involve the OS
network stack without a socket/service probe. Checker Windows handled
interruption is exit 130; POSIX interruption propagation is separate. The
generator handles interruption separately on either platform. Require complete
stdout JSON and the actual exit before accepting any output.

IDs and statuses can identify a project or reveal an environment even though
raw paths and values are omitted. Fixed errors do not anonymize library
tracebacks or captures. No input, output or fixture authorizes setup, program
execution or publication of actual environment records. Read the [private
workspace guide](docs/PRIVATE-WORKSPACE.md), [qualification](docs/QUALIFICATION.md)
and [provenance](docs/PROVENANCE.md) before using your own private declarations.
