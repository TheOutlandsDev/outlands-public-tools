# Use Public Release Audit 0.1.0

Download the source ZIP from the
[standalone release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/public-release-audit-v0.1.0)
and extract into a fresh folder. Keep `release_audit.py` and `audit_windows.py`
adjacent. Use Python **3.12–3.15**, with 3.15.2 selected for that minor in
qualification. Only the standard library is needed. No pip packages, network,
model or account are required; Python/OS prerequisites are separately supplied.

## Select an interpreter and private parent

Use existing trusted fully spelled local paths. A no-pip venv is optional for
ordinary use and required for release qualification. PowerShell, fictional paths:

```powershell
py -3.12 -m venv --without-pip 'D:\Private\ReleaseAudit\venv312'
$python = 'D:\Private\ReleaseAudit\venv312\Scripts\python.exe'
& $python --version
```

Ubuntu:

```sh
python3.12 -m venv --without-pip '/absolute/private/release-audit/venv312'
python='/absolute/private/release-audit/venv312/bin/python'
"$python" --version
```

Choose the intended minor. User-owned interpreters/venvs do not inherently need
administrator access. Respect device policy and OS support without bypasses.
Read [PRIVATE-WORKSPACE.md](docs/PRIVATE-WORKSPACE.md).

## Exact interface and meanings

From the extracted folder, or with its script selected by explicit path:

```text
python -B release_audit.py --root STABLE_FICTIONAL_EXPORT --report NEW_PRIVATE_REPORT_JSON
python -B release_audit.py --root STABLE_FICTIONAL_EXPORT --deny-file PRIVATE_MARKERS_JSON --report NEW_PRIVATE_REPORT_JSON
python -B release_audit.py --root STABLE_FICTIONAL_EXPORT --write-manifest NEW_PRIVATE_MANIFEST_JSON
python -B release_audit.py --root STABLE_FICTIONAL_EXPORT --manifest REVIEWED_PRIVATE_MANIFEST_JSON
```

`--root` selects an existing stable text export. Reports/manifests must use new
files under existing private parents **outside** that root. `--deny-file` is a
private JSON array of at most 1,000 literal strings, each 3–1,024 characters.
Matching is case-insensitive and literal in content and relative names, without
semantic interpretation. Keep actual organization/project markers private.

| Result | Exit | Meaning |
| --- | ---: | --- |
| `NO_PATTERN_FINDINGS` | 0 | No findings/errors in this selected scan and optional inventory comparison. |
| `REVIEW_REQUIRED` | 1 | Findings, incomplete observations or manifest mismatch require review. |
| `ERROR` / `AUDIT_INPUT_OR_OUTPUT_ERROR` | 2 | Handled input/configuration/I/O failure; new output can remain unconfirmed. |
| `ERROR` / `AUDIT_INTERRUPTED` | 130 | Handled Windows interruption; new output can remain unconfirmed. |

Normal stdout is one JSON summary with `status`, inventoried `files`, per-rule
`findings` counts and `errors`. Fixed error output contains only `status` and
`code`. POSIX interruption behavior remains preserved. Static help is separate.
Reports contain schema version, status, inventory, findings, errors, exclusions
and bounded-scan scope. Findings omit snippets, **not** identifying filenames.

Create a manifest only after independently reviewing the exact tree. The tool
refuses `--write-manifest` when the scan requires review. Comparison checks
selected paths, sizes and SHA-256. A generated manifest is not approval, a
signature or independent authenticity evidence: someone able to replace both
content and manifest can make them agree.

## Fictional clean → finding → manifest → compare → drift

Save this as a new `fictional_walkthrough.py` in your external private workspace.
It makes new invented exports/controls, compares complete CLI/JSON outcomes and
preserves existing files during every auditor call. Only its last deliberate
fixture step adds a new file to demonstrate drift; no original is overwritten.
Actual exports, markers, reports and captures stay private.

```python
from collections import Counter
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
runtime = [source / 'release_audit.py', source / 'audit_windows.py']
assert all(path.is_file() for path in runtime)
checksum = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
runtime_before = {path.name: checksum(path) for path in runtime}
work.mkdir(mode=0o700)
clean, held = work / 'export-clean', work / 'export-findings'
clean.mkdir()
held.mkdir()
plain = b'Fictional public example.\n'
marked = b'Fictional-Hold-Marker\n'
for path, data in ((clean / 'example.txt', plain), (held / 'note.txt', marked)):
    with path.open('xb') as output:
        output.write(data)
markers = work / 'private-markers.json'
with markers.open('x', encoding='utf-8', newline='\n') as output:
    output.write('["fictional-hold-marker"]\n')
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
outcomes = []

def report(files, findings=(), errors=()):
    return {'schema_version': 1,
            'status': 'REVIEW_REQUIRED' if findings or errors else 'NO_PATTERN_FINDINGS',
            'inventory': [{'path': name, 'size': len(data),
                           'sha256': hashlib.sha256(data).hexdigest()}
                          for name, data in sorted(files.items())],
            'findings': list(findings), 'errors': list(errors), 'excluded': [],
            'scope': {'max_entries': 20000, 'max_file_bytes': 2*1024*1024,
                      'max_total_bytes': 64*1024*1024,
                      'bytes_read': sum(map(len, files.values())),
                      'git_history_scanned': False, 'semantic_ip_review': False}}

def summary(value):
    return {'status': value['status'], 'files': len(value['inventory']),
            'findings': dict(Counter(row['rule'] for row in value['findings'])),
            'errors': value['errors']}

def call(label, root, options, code, expected):
    retained = {path: checksum(path) for path in work.rglob('*') if path.is_file()}
    tree = {path.relative_to(root).as_posix() for path in root.rglob('*')}
    command = [sys.executable, '-B', str(source / 'release_audit.py'),
               '--root', str(root), *map(str, options)]
    done = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, encoding='utf-8', errors='strict',
                          env=environment, timeout=60)
    assert done.returncode == code and done.stderr == ''
    value = json.loads(done.stdout)
    assert value == expected and len(done.stdout.splitlines()) == 1
    assert retained == {path: checksum(path) for path in retained}
    assert tree == {path.relative_to(root).as_posix() for path in root.rglob('*')}
    outcomes.append({'case': label, 'exit_code': code, 'value': value})

clean_result = report({'example.txt': plain})
clean_report = work / 'clean-report.json'
call('clean', clean, ['--report', clean_report], 0, summary(clean_result))
assert json.loads(clean_report.read_text(encoding='utf-8')) == clean_result
held_result = report({'note.txt': marked},
                     [{'path': 'note.txt', 'rule': 'PRIVATE_LITERAL', 'line': 1}])
held_report = work / 'findings-report.json'
call('private_marker', held, ['--deny-file', markers, '--report', held_report],
     1, summary(held_result))
assert json.loads(held_report.read_text(encoding='utf-8')) == held_result
assert 'fictional-hold-marker' not in held_report.read_text(encoding='utf-8').casefold()
denied_manifest = work / 'denied-manifest.json'
fixed_error = {'status': 'ERROR', 'code': 'AUDIT_INPUT_OR_OUTPUT_ERROR'}
call('findings_block_manifest', held,
     ['--deny-file', markers, '--write-manifest', denied_manifest], 2, fixed_error)
assert not denied_manifest.exists()
manifest = work / 'reviewed-manifest.json'
call('create_manifest', clean, ['--write-manifest', manifest], 0, summary(clean_result))
assert json.loads(manifest.read_text(encoding='utf-8')) == {
    'schema_version': 1, 'inventory': clean_result['inventory']}
compared_report = work / 'compared-report.json'
call('compare_manifest', clean, ['--manifest', manifest, '--report', compared_report],
     0, summary(clean_result))
assert json.loads(compared_report.read_text(encoding='utf-8')) == clean_result
call('refuse_existing_report', clean, ['--report', clean_report], 2, fixed_error)
added = b'Fictional newly added public example.\n'
with (clean / 'added.txt').open('xb') as output:
    output.write(added)
drift_result = report({'example.txt': plain, 'added.txt': added},
                      errors=['MANIFEST_MISMATCH'])
drift_report = work / 'drift-report.json'
call('detect_added_file', clean, ['--manifest', manifest, '--report', drift_report],
     1, summary(drift_result))
assert json.loads(drift_report.read_text(encoding='utf-8')) == drift_result
assert (clean / 'example.txt').read_bytes() == plain
assert (held / 'note.txt').read_bytes() == marked
assert runtime_before == {path.name: checksum(path) for path in runtime}
print(json.dumps({'outcomes': outcomes,
                  'existing_input_control_report_and_runtime_bytes_preserved': True},
                 sort_keys=True))
```

Invoke with the absolute extracted-source folder and a **new** private output
folder whose parent exists. PowerShell:

```powershell
& $python -B 'D:\Private\ReleaseAudit\fictional_walkthrough.py' 'D:\Source\public-release-audit-0.1.0' 'D:\Private\ReleaseAudit\fictional-demo'
```

Ubuntu:

```sh
"$python" -B '/absolute/private/release-audit/fictional_walkthrough.py' '/absolute/source/public-release-audit-0.1.0' '/absolute/private/release-audit/fictional-demo'
```

Expected output has seven complete caller outcomes: three exit-0 results, two
exit-1 review results and two fixed exit-2 refusals, with the preservation flag
true. The driver chooses a 60-second subprocess limit; this is not a universal
tool I/O deadline. Runtime hashes check the selected release during this run,
not equality with an earlier baseline. Repeat into another new private folder.
Hash equality does not certify timestamps, ACLs or every OS observation.

## Scope, privacy and filesystem limits

Rules cover selected credential/key/assignment shapes, non-example addresses,
internal hosts, URL credentials, user-home/UNC/rooted paths and private literals.
Loopback, documentation addresses and listed example-email domains are allowed
for fictional data. False positives and missed identifying material remain
possible. No-pattern output is not confidentiality, ownership, IP or behavior
clearance. Findings omit snippets; relative filenames, line numbers and hashes
can still identify private content. Reports/manifests/markers are not anonymized.

Limits are 20,000 encountered entries, 2 MiB per selected text file and 64 MiB
total bytes. Marker/manifest JSON controls are capped at 16 MiB. Windows encoded
outputs have a 64 MiB per-output ceiling. These are not total CPU/memory/regex/
deadline quotas. Only unnamed selected text data is inspected. Root `.git` is
explicitly excluded; nested/private/runtime directories, linked/reparse entries,
unknown/binary/archive/non-UTF-8 content and sensitive names require review.
Git history, branches/tags/assets, document/image metadata, archive interiors,
external links, software behavior, streams, ACLs and topology are outside scope.

Use stable ordinary files and trusted quiescent local parents. Native Windows
guards check supported local fixed/removable paths and identities; use fully
spelled paths. UNC/device/ADS, traversal, drive/root-relative, reserved/invalid
names and observed aliases/reparse paths are unsupported. Inputs are not
imported/launched or modified; reads may affect access metadata and Python
caches are separate. Keep the Windows backend adjacent; the example uses `-B`.

Output can be partial or complete-looking but unconfirmed after failure or
interruption. A parsed report with clear-looking status does not prove command
success. Require the actual result and inspect retained output privately.
There is no automatic cleanup/rollback or atomic multi-output transaction.
Parent ACLs and OS/Python govern permissions; confidentiality is not audited.
Sampled checks have pathname/open/create race windows, not a hostile-filesystem
sandbox, universal deadline, live/cloud/remote-provider or power-loss guarantee.
Read the preserved historical [WINDOWS.md](docs/WINDOWS.md) contract.

## Maintainer source packaging and qualification

From the reviewed committed repository module with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Both package outputs must be new with existing parents. Qualification package/
reference directories must exist; workspace/report must be new absolute paths
with existing parents. Both helpers refuse `-O`, `-OO` and `PYTHONOPTIMIZE`.
Consumer runs may omit the reference and honestly record both `identical_*`
flags false. All eight hosted lanes require independent ZIP/build-manifest
identity true. Actual discovered/passed/skipped results belong to release
`VALIDATION.json`, separate from historical evidence. See
[QUALIFICATION.md](docs/QUALIFICATION.md) and [PROVENANCE.md](docs/PROVENANCE.md).
