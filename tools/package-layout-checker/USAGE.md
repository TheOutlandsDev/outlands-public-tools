# Use Package Layout Checker 0.1.0

Download the source ZIP from the
[standalone release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/package-layout-checker-v0.1.0)
and extract it into a fresh folder. Keep `layout_check.py` and
`layout_windows.py` adjacent. Use Python **3.12–3.15**, with 3.15.2 selected
for that minor in qualification. Only standard-library/OS APIs are needed.
No pip packages, network, model, account or installer are required.

## Select an interpreter and private parent

Choose existing trusted fully spelled local paths. A no-pip venv is optional
for ordinary use and required by release qualification. PowerShell, fictional
paths:

```powershell
py -3.12 -m venv --without-pip 'D:\Private\PackageLayout\venv312'
$python = 'D:\Private\PackageLayout\venv312\Scripts\python.exe'
& $python --version
```

Ubuntu:

```sh
python3.12 -m venv --without-pip '/absolute/private/package-layout/venv312'
python='/absolute/private/package-layout/venv312/bin/python'
"$python" --version
```

Choose the intended minor. User-owned interpreters/venvs do not inherently need
administrator access. Respect device policy and OS prerequisites without
bypasses. Use an external [private workspace](docs/PRIVATE-WORKSPACE.md).

## Interface and manifest

From the extracted folder, or with the selected script's explicit path:

```text
python -B layout_check.py --root EXISTING_FICTIONAL_PACKAGE --manifest PRIVATE_LAYOUT_JSON
```

Both options are required. There is no default project or data path, environment
expansion, report/output option, package mutation, installation or code execution.
The CLI prints JSON to stdout. Capturing stdout is a separate caller action;
ordinary shell redirection can overwrite the caller's chosen capture file.

A UTF-8 JSON manifest selects only the relative files to check:

```json
{"schema_version":1,"files":[{"path":"README.md"},{"path":"src/demo.py","python_syntax":true,"forbidden_literals":["FICTIONAL_DO_NOT_SHIP"]}]}
```

`path` is a canonical slash-separated relative name, at most 512 characters.
Optional `python_syntax` is a boolean; optional `forbidden_literals` is a list
of literal strings. Syntax uses the running interpreter's AST parser, without
imports/execution. Literal matching is case-insensitive, not regex or semantic
secret detection. A presence-only entry checks metadata without reading its
body; all selected files still need to satisfy file-size/type/link rules.

Only `schema_version` and `files` are allowed at the top level, and only `path`,
`python_syntax`, `forbidden_literals` per row. Schema version must be integer 1.
Duplicate JSON keys, nonstandard non-finite constants, unknown fields, invalid
rule types, duplicate/case-colliding paths, absolute paths, traversal and unsafe
path characters are rejected. The manifest may be outside the package, as in
this guide; the checker does not make its sensitive rules public or anonymous.

| Outcome | Exit | Meaning |
| --- | ---: | --- |
| `PASS` | 0 | Every declared file/rule passed the selected checks. |
| `FAIL` | 1 | One or more declared rows have fixed finding codes. |
| `REJECTED` | 2 | Invalid control/arguments, unsupported platform or failed root/manifest access. |
| `REJECTED` / `INTERRUPTED` | 130 | Interrupted run; captured stdout may be incomplete. |

Completed file results contain `schema_version`, `status`, `checked_files`,
`failed_files` and ordered `results` rows (`path`, `status`, `codes`). Rejections
contain only `status` and a fixed `code`. Static help is separate. Relative names
are retained, while source text, matched literals, parser excerpts, root/native
paths and raw exceptions are omitted. Library tracebacks/caller logs are separate.

## Fictional declared checks and complete outcomes

Save this as a new `fictional_walkthrough.py` outside source. It creates new
invented packages and outside-package manifests, invokes the selected CLI and
compares complete JSON values. The valid Python fixture would raise if executed;
only syntax is requested. An opaque binary is presence-only, and an invalid
unlisted Python file deliberately remains outside the declared checks.

```python
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

if not __debug__:
    raise RuntimeError('Use normal Python for this verification example')
source, work = map(Path, sys.argv[1:])
assert source.is_absolute() and source.is_dir()
assert work.is_absolute() and not work.exists() and work.parent.is_dir()
assert not work.is_relative_to(source)
runtime = [source / 'layout_check.py', source / 'layout_windows.py']
assert all(path.is_file() for path in runtime)
checksum = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
runtime_before = {path.name: checksum(path) for path in runtime}
work.mkdir(mode=0o700)
clean, findings, controls = work / 'package-clean', work / 'package-findings', work / 'controls'
for folder in (clean, findings, controls):
    folder.mkdir()
for path, data in (
    (clean / 'README.md', b'Fictional package documentation.\n'),
    (clean / 'src/demo.py', b"raise RuntimeError('FICTIONAL_INPUT_WAS_EXECUTED')\n"),
    (clean / 'opaque.bin', b'\x00\xff'),
    (clean / 'not-declared.py', b'def broken(\n'),
    (findings / 'syntax.py', b'def broken(\n'),
    (findings / 'literal.txt', b'Fictional_Do_Not_Ship\n'),
):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as output:
        output.write(data)

def row(path, codes=()):
    return {'path': path, 'status': 'FAIL' if codes else 'PASS', 'codes': list(codes)}

def expected(rows):
    failed = sum(value['status'] == 'FAIL' for value in rows)
    return {'schema_version': 1, 'status': 'FAIL' if failed else 'PASS',
            'checked_files': len(rows), 'failed_files': failed, 'results': rows}

clean_entries = [{'path': 'README.md'},
                 {'path': 'src/demo.py', 'python_syntax': True},
                 {'path': 'opaque.bin'}]
missing = {'path': 'missing.txt'}
syntax = {'path': 'syntax.py', 'python_syntax': True}
literal = {'path': 'literal.txt', 'forbidden_literals': ['fictional_do_not_ship']}
missing_row = row('missing.txt', ['MISSING'])
syntax_row = row('syntax.py', ['PYTHON_SYNTAX'])
literal_row = row('literal.txt', ['FORBIDDEN_LITERAL'])
cases = [
    ('clean', clean, {'schema_version': 1, 'files': clean_entries}, 0,
     expected([row('README.md'), row('src/demo.py'), row('opaque.bin')])),
    ('missing', findings, {'schema_version': 1, 'files': [missing]}, 1, expected([missing_row])),
    ('syntax', findings, {'schema_version': 1, 'files': [syntax]}, 1, expected([syntax_row])),
    ('literal', findings, {'schema_version': 1, 'files': [literal]}, 1, expected([literal_row])),
    ('combined', findings, {'schema_version': 1, 'files': [missing, syntax, literal]}, 1,
     expected([missing_row, syntax_row, literal_row])),
    ('invalid_control', clean, {'schema_version': True, 'files': [{'path': 'README.md'}]}, 2,
     {'status': 'REJECTED', 'code': 'MANIFEST_INVALID'}),
]
selected = []
for name, root, value, code, result in cases:
    manifest = controls / (name + '.json')
    with manifest.open('x', encoding='utf-8', newline='\n') as output:
        output.write(json.dumps(value) + '\n')
    selected.append((name, root, manifest, code, result))
before = {path.relative_to(work).as_posix(): checksum(path)
          for path in work.rglob('*') if path.is_file()}
tree_before = {path.relative_to(work).as_posix() for path in work.rglob('*')}
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
outcomes = []
for name, root, manifest, code, result in selected:
    done = subprocess.run([sys.executable, '-B', str(source / 'layout_check.py'),
                           '--root', str(root), '--manifest', str(manifest)],
                          stdin=subprocess.DEVNULL, capture_output=True, text=True,
                          encoding='utf-8', errors='strict', env=environment, timeout=60)
    assert done.returncode == code and done.stderr == ''
    observed = json.loads(done.stdout)
    assert observed == result and len(done.stdout.splitlines()) == 1
    assert 'fictional_do_not_ship' not in done.stdout.casefold()
    assert 'FICTIONAL_INPUT_WAS_EXECUTED' not in done.stdout
    assert str(work) not in done.stdout.replace('\\\\', '\\')
    assert before == {path.relative_to(work).as_posix(): checksum(path)
                      for path in work.rglob('*') if path.is_file()}
    assert tree_before == {path.relative_to(work).as_posix() for path in work.rglob('*')}
    assert runtime_before == {path.name: checksum(path) for path in runtime}
    outcomes.append({'case': name, 'exit_code': code, 'value': observed})
print(json.dumps({'outcomes': outcomes,
                  'input_manifest_tree_and_runtime_bytes_preserved': True}, sort_keys=True))
```

Invoke with the absolute extracted-source folder and a **new** private folder
whose parent exists. PowerShell:

```powershell
& $python -B 'D:\Private\PackageLayout\fictional_walkthrough.py' 'D:\Source\package-layout-checker-0.1.0' 'D:\Private\PackageLayout\fictional-demo'
```

Ubuntu:

```sh
"$python" -B '/absolute/private/package-layout/fictional_walkthrough.py' '/absolute/source/package-layout-checker-0.1.0' '/absolute/private/package-layout/fictional-demo'
```

Expected driver output has six complete outcomes: one exit-0 PASS, four exit-1
finding results and one exit-2 invalid-control rejection. The combined result
contains all three failed rows in manifest order. The preservation flag is
true, and no package/control/output file is created or changed by the checker.
The driver creates its own fixtures; it captures stdout in memory and prints
only fictional results. No generated report schema or output switch is added.

The driver's 60-second subprocess limit is a caller choice, not a universal I/O
deadline. Runtime hashes check preservation during the demonstration, not every
OS property or future release. Repeat into a new private folder. Hash equality
does not certify access timestamps, ACLs or complete filesystem observations.

## Bounds, privacy and filesystem scope

The manifest is at most **64 KiB**, with **1–100 declared files**. Each file is
at most **256 KiB**, including presence-only selections. Content checks reserve
at most **2 MiB** of observed sizes per run, including reservations for reads
that later fail. Each row permits at most **16 literals**, each **1–256
characters**. These bounds are not complete CPU/memory/AST/deadline quotas.

POSIX uses descriptor-relative directory traversal and available required
no-follow/directory/nonblocking primitives. Windows uses the adjacent native
backend with retained ancestor/file handles, normalized names/identity checks,
read-only sharing and noninheritable binary descriptors. Both require supported
ordinary single-link manifest/selected files and refuse observed unsafe links,
reparse points and special files. Windows additionally rejects unsupported
local-volume/name/alias/stream spellings; use fully spelled stable local paths.
Read [WINDOWS.md](docs/WINDOWS.md) for the preserved historical contract wording
and its standalone review link.

Only declared files are checked. Unlisted entries are not enumerated or opened.
PASS is not an exact-export allowlist, absence-of-extra-files/privacy assertion,
dependency audit, runtime/application correctness, ownership, licensing or
release acceptance. Python syntax compatibility is limited to the interpreter
performing the parse. Presence-only entries establish no text or semantic claim.

The CLI omits source, matched literals, parser excerpts and raw errors, but
relative declared filenames remain identifying. Real manifests may contain
private literals; stdout, caller captures and Python library tracebacks need
separate privacy review. Fixed codes are not anonymization. Keep actual inputs,
controls/results and captures private.

The checker writes no package or report files. Reads can affect OS access
metadata and Python caches are separate; this guide uses `-B`. Interrupted or
failed stdout capture can be partial and must not be treated as complete JSON.
Trusted quiescent local inputs remain required. Sampled checks and sharing are
not atomic snapshots, hostile-filesystem containment, universal I/O deadlines,
mount/drive-rebinding, live/network/virtual-provider or power-loss acceptance.
Streams, ACL privacy, ownership and topology are outside the declared checks.

## Maintainer source packaging and qualification

From the reviewed committed repository module, with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Package outputs must be new with existing parents. Qualification inputs must
exist; workspace/report must be new absolute paths with existing parents,
outside source. Both helpers refuse `-O`, `-OO` and `PYTHONOPTIMIZE`. Consumer
runs can omit the reference and honestly record `identical_zip` and
`identical_build_manifest` false; all eight hosted lanes require both true.
Actual versions/counts/outcomes/skips belong to release `VALIDATION.json`.
See [QUALIFICATION.md](docs/QUALIFICATION.md) and [PROVENANCE.md](docs/PROVENANCE.md).
