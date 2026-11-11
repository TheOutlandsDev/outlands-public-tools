# Use Project Workspace 0.1.0

Download the source ZIP from the
[standalone release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/project-workspace-v0.1.0)
and extract it into a fresh folder. Keep `workspace.py` and
`workspace_windows.py` adjacent. Use Python **3.12–3.15**, with 3.15.2 selected
for that minor in qualification. No pip packages, network, model or account
are needed; Python/OS prerequisites are separate.

## Select a private interpreter and parent

Use existing trusted, fully spelled local source/private paths. A new no-pip
venv is optional for ordinary use and required for release qualification.
PowerShell, with fictional paths:

```powershell
py -3.12 -m venv --without-pip 'D:\Private\ProjectWorkspace\venv312'
$python = 'D:\Private\ProjectWorkspace\venv312\Scripts\python.exe'
& $python --version
```

Ubuntu equivalent:

```sh
python3.12 -m venv --without-pip '/absolute/private/project-workspace/venv312'
python='/absolute/private/project-workspace/venv312/bin/python'
"$python" --version
```

Choose the intended minor for your system. User-owned Python/venvs do not
inherently need administrator access. Respect device/software policy and
required OS support without bypasses. Read [PRIVATE-WORKSPACE.md](docs/PRIVATE-WORKSPACE.md).

## Exact CLI and outcomes

Run from the extracted folder, or select its script by explicit path:

```text
python -B workspace.py --root EXISTING_PRIVATE_PARENT --name fictional-project
python -B workspace.py --root EXISTING_PRIVATE_PARENT --name fictional-project --source FICTIONAL_INPUT
python -B workspace.py --root EXISTING_PRIVATE_PARENT --name fictional-project --source FICTIONAL_INPUT --create
```

`--root` must already exist. `--name` matches `[a-z0-9][a-z0-9_-]{0,63}`;
reserved device names are refused. `--source` is optional and limited to
16 MiB of ordinary unnamed file data. The default validates without creation,
including **reading** a selected source. It does not reserve the destination.
`--create` performs creation. An existing destination is refused.

Successful operation prints one JSON object and exits 0. A plan contains
`status: PLAN_ONLY`, the seven configured folder entries and `source_selected`.
Creation contains `status: WORKSPACE_CREATED` and `source_verified`; without a
source that boolean is false and no intake copies/metadata are created.
With a source it is true after applicable byte verification.

Handled argument/input/I/O failures print fixed JSON
`{"status":"ERROR","code":"WORKSPACE_INPUT_OR_OUTPUT_ERROR"}` and exit 2.
Windows handled interruption prints
`{"status":"ERROR","code":"WORKSPACE_INTERRUPTED"}` and exits 130.
POSIX interruption behavior is preserved. Help is static argparse output,
separate from operation JSON. A plan or successful copy is not a privacy,
rights or security clearance.

## Fictional plan → create → verify → refuse overwrite

Save the following as a new `fictional_walkthrough.py` in your external private
workspace. It creates its own **new** fictional input/project parent, calls the
selected CLI and compares complete JSON/exit outcomes. The driver prints only
authored demonstration outcomes. Actual inputs, generated workspaces, stdout
captures and paths must stay private.

```python
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

if not __debug__:
    raise RuntimeError('Use normal Python for this verification example')
source = Path(sys.argv[1])
work = Path(sys.argv[2])
assert source.is_absolute() and source.is_dir()
assert work.is_absolute() and not work.exists() and work.parent.is_dir()
assert not work.is_relative_to(source)
runtime = [source / 'workspace.py', source / 'workspace_windows.py']
assert all(path.is_file() for path in runtime)
checksum = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
runtime_before = {path.name: checksum(path) for path in runtime}
work.mkdir(mode=0o700)
selected = work / 'fictional-input.bin'
with selected.open('xb') as output:
    output.write(b'Fictional opaque intake bytes.\x00\xff\n')
input_before = selected.read_bytes()
input_hash = checksum(selected)
parent = work / 'projects'
parent.mkdir()
destination = parent / 'fictional-project'
folders = ['original', 'working', 'evidence/screenshots',
           'evidence/test-output', 'deliverables', 'logs', 'rollback']
command = [sys.executable, '-B', str(source / 'workspace.py'),
           '--root', str(parent), '--name', 'fictional-project',
           '--source', str(selected)]
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')

def call(arguments, expected_code, expected_value):
    done = subprocess.run(arguments, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, encoding='utf-8',
                          errors='strict', env=environment, timeout=60)
    assert done.returncode == expected_code and done.stderr == ''
    value = json.loads(done.stdout)
    assert value == expected_value and len(done.stdout.splitlines()) == 1
    return {'exit_code': done.returncode, 'value': value}

plan = call(command, 0, {'status': 'PLAN_ONLY', 'folders': folders,
                         'source_selected': True})
assert not destination.exists() and list(parent.iterdir()) == []
created = call(command + ['--create'], 0,
               {'status': 'WORKSPACE_CREATED', 'source_verified': True})
expected_directories = set(folders) | {'evidence'}
expected_files = {'.gitignore', 'CONTROL.md', 'original/SOURCE.json',
                  'original/intake.bin', 'working/intake.bin'}
assert {path.relative_to(destination).as_posix() for path in destination.rglob('*')
        if path.is_dir()} == expected_directories
assert {path.relative_to(destination).as_posix() for path in destination.rglob('*')
        if path.is_file()} == expected_files
for name in ('original/intake.bin', 'working/intake.bin'):
    assert (destination / name).read_bytes() == input_before
    assert checksum(destination / name) == input_hash
metadata = json.loads((destination / 'original/SOURCE.json').read_text(encoding='utf-8'))
assert metadata == {'sha256': input_hash, 'size': len(input_before)}
assert (destination / '.gitignore').read_text(encoding='utf-8') == '*\n'
assert (destination / 'CONTROL.md').read_text(encoding='utf-8').startswith(
    '# Private project control record\n\nStatus: INTAKE\n')
before = {name: checksum(destination / name) for name in expected_files}
refused = call(command + ['--create'], 2,
               {'status': 'ERROR', 'code': 'WORKSPACE_INPUT_OR_OUTPUT_ERROR'})
assert before == {name: checksum(destination / name) for name in expected_files}
assert expected_files == {path.relative_to(destination).as_posix()
                          for path in destination.rglob('*') if path.is_file()}
assert selected.read_bytes() == input_before and checksum(selected) == input_hash
assert runtime_before == {path.name: checksum(path) for path in runtime}
print(json.dumps({'plan': plan, 'created': created, 'repeat_create': refused,
                  'input_runtime_and_existing_output_bytes_unchanged': True},
                 sort_keys=True))
```

Invoke with the absolute extracted-source folder and a **new** private output
folder whose parent exists. PowerShell:

```powershell
& $python -B 'D:\Private\ProjectWorkspace\fictional_walkthrough.py' 'D:\Source\project-workspace-0.1.0' 'D:\Private\ProjectWorkspace\fictional-demo'
```

Ubuntu:

```sh
"$python" -B '/absolute/private/project-workspace/fictional_walkthrough.py' '/absolute/source/project-workspace-0.1.0' '/absolute/private/project-workspace/fictional-demo'
```

Expected driver output includes a complete plan (exit 0), successful creation
(exit 0), repeat-create refusal (exit 2) and the unchanged-bytes boolean true.
The driver's 60-second subprocess limit is a caller choice, not a tool-wide
I/O deadline. Choose another new output folder when repeating; there is no
automatic deletion or rollback. Hash equality does not certify timestamps,
ACLs or every OS observation. The documented driver is a verification example;
only the packaging helpers require normal Python as their own execution policy.

## Output, preservation and privacy limits

The layout includes `original`, `working`, `evidence/screenshots`,
`evidence/test-output`, `deliverables`, `logs`, `rollback`, `.gitignore` and
neutral `CONTROL.md`. A selected source becomes opaque `original/intake.bin`
and `working/intake.bin`, with size/SHA-256 only in `original/SOURCE.json`.
Original names/paths are not placed in that metadata; private input bytes can
still contain identifiers or secrets. Input is never parsed/imported/launched.

The POSIX bodies/template remain preserved. Windows uses checked local paths,
native identity/handle guards, bounded input reads, exclusive directory/file
creation and readback of expected output bytes. Ordinary hardlinked sources
remain supported. Observed links/reparse components and unsupported Windows
spellings/providers are refused. Use fully spelled local fixed/removable paths;
UNC/device/ADS, traversal, drive/root-relative, reserved/invalid names and observed
short-name aliases are outside supported Windows spelling. See
[WINDOWS.md](docs/WINDOWS.md) for precise native behavior and historical evidence.

Only unnamed input data is copied. Streams, ACLs, ownership, topology and
timestamps are not backed up. Reads can affect OS access metadata, and Python
caches are separate; the example uses `-B`. A 16 MiB source limit is not a total
CPU/memory/elapsed-time quota. No deadline covers every filesystem call.

On error/interruption a newly created tree can be partial or complete-looking
but unconfirmed. Inspect it privately and require the actual successful result.
Existing destinations are refused; no automatic recursive cleanup or rollback
occurs. The ignore file is attempted early but can fail or remain incomplete.
Ignore rules are not confidentiality controls; parent ACLs and OS/Python
permissions remain relevant. Keep generated workspaces, sources, hashes,
results and captures private, and prepare a separate reviewed export to share.

Trusted quiescent local parents remain required. Sampled checks retain
pathname/create/open race windows, with no atomic transaction or adversarial
filesystem sandbox. Drive rebinding, live/cloud/remote providers, blocking I/O,
hardware/power loss and all-stream backup acceptance remain outside scope.

## Maintainer source packaging and qualification

From the reviewed committed repository module, create two fresh private source
packages and qualify with a selected normal interpreter:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Package outputs must be new with existing parents. Qualification package/
reference directories must already exist; workspace/report must be new absolute
paths with existing parents. The two helpers refuse `-O`, `-OO` and
`PYTHONOPTIMIZE`. Consumer qualification can omit the reference, honestly
recording both `identical_*` flags false; it supplies no independent Git rebuild.
All eight hosted lanes require both ZIP and build-manifest identity flags true.

Original six shared bodies plus 40 safety methods and copied CLI consumers use
authored disposable data. Actual discovered/passed/skipped results belong to
release `VALIDATION.json`, separate from historical checks. See
[QUALIFICATION.md](docs/QUALIFICATION.md) and [PROVENANCE.md](docs/PROVENANCE.md).
