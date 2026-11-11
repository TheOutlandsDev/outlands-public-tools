# Use Documentation Check 0.1.0

Download the source ZIP from the
[standalone release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/documentation-check-v0.1.0)
and extract it into a fresh directory. Keep `docs_check.py` and
`docs_windows.py` together. The CLI uses Python 3.12–3.15 and the standard
library only: no pip packages, network, model or account. Python/OS prerequisites
are separate; no interpreter, dependency binary, actual documents or report
is bundled. Qualification selects Python 3.15.2 for that minor.

Use trusted quiescent ordinary local paths and fully spelled Windows parents.
User-owned Python/venvs do not inherently require administrator access. Follow
device policy and never bypass it to install software or make fixtures pass.

## Select a private interpreter

Open a terminal in the extracted source directory. A new no-pip venv is optional
for ordinary use and required by release qualification. Its parent must exist.
PowerShell example with fictional paths:

```powershell
py -3.12 -m venv --without-pip 'D:\Private\DocumentationCheck\venv312'
$python = 'D:\Private\DocumentationCheck\venv312\Scripts\python.exe'
& $python --version
& $python -B docs_check.py --help
& $python -B docs_check.py --root 'D:\Private\DocumentationCheck\selected-docs'
$LASTEXITCODE
```

Ubuntu example:

```sh
python3.12 -m venv --without-pip '/absolute/private/documentation-check/venv312'
python='/absolute/private/documentation-check/venv312/bin/python'
"$python" --version
"$python" -B docs_check.py --help
"$python" -B docs_check.py --root '/absolute/private/documentation-check/selected-docs'
printf '%s\n' "$?"
```

Select your own interpreter/minor and existing private documentation directory.
`--root` is required. There are no implicit scan/report destinations and no
`--output` option. Normal checks write JSON to stdout, not to the selected tree.
If you redirect stdout, choose a fresh private capture filename outside the
tree: ordinary shell redirection can overwrite a file. Help is text/exit zero.

## Fictional good/bad trees and preserved input bytes

Save the following demonstration as a new `fictional_walkthrough.py` in an
external [private workspace](docs/PRIVATE-WORKSPACE.md). It creates only its new
owned workspace. It runs the actual adjacent runtime files using the selected
interpreter; no fixture text is imported or executed. The generated good tree
has a valid local link, an unfetched external example URL and valid JSON. The
bad tree has a missing local target and nonstandard NaN JSON.

```python
import hashlib
import json
from pathlib import Path
import subprocess
import sys

source = Path(sys.argv[1])
work = Path(sys.argv[2])
assert source.is_absolute() and source.is_dir()
assert work.is_absolute() and not work.exists() and work.parent.is_dir()
runtime = [source / 'docs_check.py', source / 'docs_windows.py']
assert all(path.is_file() for path in runtime)
runtime_before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in runtime}
work.mkdir(mode=0o700)
good, bad = work / 'good', work / 'bad'
good.mkdir(mode=0o700)
bad.mkdir(mode=0o700)
(good / 'README.md').write_text('[guide]' + '(guide.md)\n[site]' + '(https://example.org)\n', encoding='utf-8')
(good / 'guide.md').write_text('# Fictional guide\n', encoding='utf-8')
(good / 'sample.json').write_text('{"fictional":true}\n', encoding='utf-8')
(bad / 'README.md').write_text('[missing]' + '(absent.md)\n', encoding='utf-8')
(bad / 'sample.json').write_text('{"fictional":NaN}\n', encoding='utf-8')

def contents():
    return {path.relative_to(work).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in work.rglob('*') if path.is_file()}

before = contents()
for name, root, expected, status in (
    ('good', good, 0, 'PASS'),
    ('bad', bad, 1, 'FAIL'),
    ('missing-root', work / 'not-created', 2, 'ERROR'),
):
    result = subprocess.run([sys.executable, '-B', str(runtime[0]), '--root', str(root)],
                            stdin=subprocess.DEVNULL, capture_output=True, text=True,
                            encoding='utf-8', errors='strict')
    report = json.loads(result.stdout)
    assert result.returncode == expected and report['status'] == status
    assert result.stderr == ''
    print(json.dumps({'case': name, 'exit': result.returncode, 'report': report}, sort_keys=True))
assert contents() == before
assert runtime_before == {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in runtime}
print(json.dumps({'input_and_runtime_bytes_unchanged': True}))
```

The split strings create ordinary Markdown in the fictional files. Invoke the
saved walkthrough with your absolute extracted-source path and a **new** private
workspace whose parent exists. PowerShell:

```powershell
& $python -B 'D:\Private\DocumentationCheck\fictional_walkthrough.py' 'D:\Source\documentation-check-0.1.0' 'D:\Private\DocumentationCheck\fictional-demo'
```

Ubuntu:

```sh
"$python" -B '/absolute/private/documentation-check/fictional_walkthrough.py' '/absolute/source/documentation-check-0.1.0' '/absolute/private/documentation-check/fictional-demo'
```

Expected cases are exit **0/PASS**, **1/FAIL**, **2/ERROR**, followed by a true
unchanged-bytes record. The bad tree's completed findings are expected, not a
failed test. Choose another new workspace when repeating. The wrapper captures
child output in memory and prints JSON; any saved capture is your explicit
private shell action. Hash equality checks file bytes, not access timestamps,
ACLs or every OS observation.

## Result and parser scope

```text
python -B docs_check.py --root SELECTED_LOCAL_DIRECTORY
```

Successful inspection returns JSON with `status`, `checked_documents`,
`findings` and `limits`. A finding records a relative `path`, a fixed `rule`
and a line number where applicable. `PASS` exits `0`; findings produce `FAIL`
and exit `1`. A fixed root/argument/input-output error produces `ERROR`, code
`DOCUMENTATION_CHECK_FAILED`, exit `2`. Some per-file read/size/type failures
are findings and therefore exit `1`, not a complete root-level error.

Handled Windows interruption returns `ERROR` /
`DOCUMENTATION_CHECK_INTERRUPTED`, exit `130`. POSIX interruption is re-raised
with its existing behavior. Do not treat an error or interrupted capture as a
successful complete check.

Only `.md` and `.json` files in the selected scope are checked. Markdown covers
common inline/image links and reference definitions, with limited fenced/simple
inline-code skipping. Local targets are decoded and checked for containment,
existence and supported link/reparse behavior. HTTP, HTTPS and mail schemes
are skipped without fetching; other schemes fail. Pure fragments are skipped.
There is no full CommonMark parsing, reference-use resolution, anchor checking,
external-site testing or target-content/application validation.

JSON retains default duplicate-key behavior and rejects nonstandard NaN/infinity.
It does not validate schemas or detect duplicate keys. UTF-8 BOM handling and
universal CR/LF/CRLF conversion remain. The preserved
[FILESYSTEM.md](docs/FILESYSTEM.md) gives exact parser/platform behavior and
historical evidence.

## Bounds, privacy and filesystem assumptions

Bounds are **10,000 encountered entries** and **2 MiB per selected file**.
Excluded entries consume the entry budget. Directory collection is bounded
before sorting; actual reads are bounded and compare identity/size/time.
They are not aggregate byte, CPU, elapsed-time, result-size or RAM quotas.
Root Git metadata, hidden subdirectories and named private/runtime/cache/
dependency directories are excluded according to the existing rules. Findings
do not attest to excluded content.

Windows checks native supported names, held handles, observed identity and
metadata-only local targets; unsupported network/device/ADS spellings, reparse
components and observed short-name aliases are refused. POSIX uses its retained
link/containment checks and available no-follow/nonblocking flags. Platform
target-type behavior differs. Source hard links cover unnamed data only, not
ADS, ACLs, ownership or full metadata.

Use trusted quiescent local trees and stop writers. Checks have race windows
and do not freeze a tree or provide a hostile-filesystem sandbox, universal
I/O deadline, live/remote-provider acceptance or power-loss protection. The
checker writes no tree/report/manifest, but reads may affect OS access metadata.

Reports contain relative filenames and line numbers, which can identify private
work. They are not redacted/anonymous. Arguments, shell history and captures
can retain data. Keep actual docs/reports/mappings private; public reproductions
must be authored fictional material you may share. PASS means documentation
hygiene, not confidentiality, security, source rights or application acceptance.

## Maintainer packaging and qualification

The source/build helpers use the standard library and refuse optimized Python
(`-O`, `-OO` or `PYTHONOPTIMIZE`). Packaging requires reviewed repository source
committed in Git; it is not needed to run the extracted CLI. From that module:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
```

Release reproduction also creates another new reference package from the same
committed source, then uses `packaging/qualify.py --packages PACKAGE_DIR
--reference-build REFERENCE_DIR --workspace NEW_ABSOLUTE_WORKSPACE --report
NEW_ABSOLUTE_REPORT_JSON`. Input artifact directories must exist; workspace/
report must be new with existing parents. A consumer/local run can omit the
reference, but then both `identical_*` flags are false: it supplies no independent
Git-source rebuild proof.

Keep destinations external/private. Eight fresh Windows/Ubuntu Python lanes
use no-pip/no-distribution venvs, five original shared regressions with minimal
standalone scaffolding, 40 existing I/O methods and 26 actual copied-runtime
process methods. Actual counts/outcomes
belong to release `VALIDATION.json`. See [QUALIFICATION.md](docs/QUALIFICATION.md)
for exact helper commands and evidence limits, and [PROVENANCE.md](docs/PROVENANCE.md)
for rights and retained-source boundaries.
