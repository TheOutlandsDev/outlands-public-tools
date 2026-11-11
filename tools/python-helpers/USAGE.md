# Use Python Helpers 0.1.0

Download the source ZIP from the
[standalone release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/python-helpers-v0.1.0)
and extract it into a fresh folder. Keep `helpers.py` and `helpers_windows.py`
adjacent. **This is a library, not a CLI or installer.** Your consumer imports
the explicitly selected module and decides how to handle values/exceptions.
Running the file does not provide commands or a reporting service.

Use Python **3.12–3.15**, standard library only. Qualification selects 3.15.2
for that minor. No pip packages, network, model or account are needed. Python/
OS prerequisites are separate. User-owned interpreters/venvs do not inherently
need administrator access; respect device/software policy without bypasses.

## Private interpreter and explicit import

Choose an existing external [private parent](docs/PRIVATE-WORKSPACE.md). A new
no-pip venv is optional for normal use and required by release qualification.
PowerShell example, with fictional paths:

```powershell
py -3.12 -m venv --without-pip 'D:\Private\PythonHelpers\venv312'
$python = 'D:\Private\PythonHelpers\venv312\Scripts\python.exe'
& $python --version
```

Ubuntu equivalent:

```sh
python3.12 -m venv --without-pip '/absolute/private/python-helpers/venv312'
python='/absolute/private/python-helpers/venv312/bin/python'
"$python" --version
```

Select the intended interpreter/minor for your system. Import from an explicit
trusted source path, for example with `importlib.util.spec_from_file_location`
as below. There is no install step, PATH registration or automatic discovery of
your data. Windows file loading needs the adjacent backend; pure redaction and
POSIX loading do not invoke that backend, but the release keeps both files.

## Fictional create → load → redact → preserve bytes

Save this consumer as a new `fictional_consumer.py` in your external private
workspace. It creates only a new owned input folder, loads authored JSON and
records complete API outcomes. The `case`/`ok`/`value`/`error` dictionaries are
the **consumer's demonstration format**, not a new library result schema.
All printed values are fictional. Real decoded/redacted values remain private.

```python
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

source = Path(sys.argv[1])
work = Path(sys.argv[2])
assert source.is_absolute() and source.is_dir()
assert work.is_absolute() and not work.exists() and work.parent.is_dir()
runtime = [source / 'helpers.py', source / 'helpers_windows.py']
assert all(path.is_file() for path in runtime)
runtime_before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in runtime}
spec = importlib.util.spec_from_file_location('selected_python_helpers', runtime[0])
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
work.mkdir(mode=0o700)
fixture = {
    'API-Key': 'fictional-key-value',
    'items': [{'password': 'fictional-password', 'note': 'Fictional text remains.'}],
    'unrecognized_credential': 'fictional-unknown-key-value',
    'free_text': 'Fictional identifying text is not automatically removed.'
}
paths = {'object': work / 'fictional.json', 'invalid': work / 'invalid.json',
         'array': work / 'array.json'}
for path, data in (
    (paths['object'], (json.dumps(fixture) + '\n').encode('utf-8')),
    (paths['invalid'], b'{"fictional":NaN}\n'),
    (paths['array'], b'[]\n'),
):
    with path.open('xb') as output:
        output.write(data)
before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths.values()}

def outcome(name, call, expected_error=None):
    try:
        value = call()
    except helpers.HelperError as error:
        assert str(error) == expected_error
        return {'case': name, 'ok': False, 'error': str(error)}
    assert expected_error is None
    return {'case': name, 'ok': True, 'value': value}

loaded = helpers.load_json_object(paths['object'])
original = copy.deepcopy(loaded)
redacted = helpers.redact_structure(loaded)
assert loaded == original
assert redacted is not loaded and redacted['items'] is not loaded['items']
assert redacted['API-Key'] == '<redacted>'
assert redacted['items'][0]['password'] == '<redacted>'
assert redacted['free_text'] == loaded['free_text']
assert redacted['unrecognized_credential'] == loaded['unrecognized_credential']
results = [
    {'case': 'load_object', 'ok': True, 'value': loaded},
    {'case': 'redact_copy', 'ok': True, 'value': redacted},
    outcome('invalid_limit', lambda: helpers.load_json_object(paths['object'], max_bytes=True), 'INVALID_LIMIT'),
    outcome('too_small', lambda: helpers.load_json_object(paths['object'], max_bytes=1), 'JSON_OBJECT_LOAD_FAILED'),
    outcome('invalid_json', lambda: helpers.load_json_object(paths['invalid']), 'JSON_OBJECT_LOAD_FAILED'),
    outcome('object_required', lambda: helpers.load_json_object(paths['array']), 'JSON_OBJECT_LOAD_FAILED'),
    outcome('unsupported_value', lambda: helpers.redact_structure({'visible': object()}), 'JSON_TYPES_REQUIRED'),
    outcome('depth_limit', lambda: helpers.redact_structure({'items': [[1]]}, max_depth=1), 'DEPTH_LIMIT'),
]
assert before == {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths.values()}
assert runtime_before == {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in runtime}
print(json.dumps({'outcomes': results, 'input_and_runtime_bytes_unchanged': True}, sort_keys=True))
```

Invoke the consumer with absolute extracted-source and **new** private workspace
paths whose parent exists. PowerShell:

```powershell
& $python -B 'D:\Private\PythonHelpers\fictional_consumer.py' 'D:\Source\python-helpers-0.1.0' 'D:\Private\PythonHelpers\fictional-demo'
```

Ubuntu:

```sh
"$python" -B '/absolute/private/python-helpers/fictional_consumer.py' '/absolute/source/python-helpers-0.1.0' '/absolute/private/python-helpers/fictional-demo'
```

Expected output contains two successful values, six fixed error outcomes and
`input_and_runtime_bytes_unchanged: true`. Sensitive-key values are replaced;
the ordinary text/unknown field remains. The loaded value and input/runtime
bytes stay unchanged. Hash equality does not certify access timestamps, ACLs
or every OS observation. Choose another new workspace when repeating; there
is no automatic cleanup or deletion of inputs.

## Exact API behavior

`load_json_object(path, max_bytes=1024*1024)` returns a dictionary. `max_bytes`
must have exact type `int` (not bool), be positive and be at most 16 MiB; invalid
limits raise `HelperError('INVALID_LIMIT')` before I/O. The default is 1 MiB.
Read/decoding/JSON/object/path-type failures use
`HelperError('JSON_OBJECT_LOAD_FAILED')` with suppressed display context.

UTF-8 BOM is accepted; only an object is returned. Duplicate keys retain the
standard decoder's last-value-wins behavior. Nonstandard NaN/infinity literals
are refused, but standard number/exponent behavior remains. For example,
exponent overflow is not rejected as a new finite-number rule. There is no
new schema, duplicate-key, JSON-depth or total-resource policy.

`redact_structure(value, *, max_depth=32)` makes separate dictionaries/lists.
The depth limit must have exact type `int` and be 1–128, or `INVALID_DEPTH` is
raised. Traversal begins at depth zero; excess nesting raises `DEPTH_LIMIT`.
Encountered mapping keys must be strings (`STRING_KEYS_REQUIRED`). Unredacted
unsupported values raise `JSON_TYPES_REQUIRED`. Supported primitive values are
None and exact str/int/float/bool types; existing float behavior is unchanged,
including nonfinite caller-supplied values.

Sensitive keys are `password`, `api_key`, `authorization`, `secret`, `token`,
`access_token`, `refresh_token`, `secret_key`, `private_key`. Matching uses
`casefold().replace('-', '_')`; output key spelling is preserved. A sensitive
value becomes `<redacted>` without inspection/traversal. There is no whitespace
stripping, free-text scanning or discovery of unknown credential keys.

These fixed strings describe library exceptions, not CLI exit/status codes.
Your caller controls errors, serialization, finite-number policy, logs and
captures. Fixed displayed messages do not anonymize stack traces, caught
exception objects/contexts, decoded values or logs. Catching/printing a fixed
message as above is a demonstration, not complete privacy clearance.
`KeyboardInterrupt` propagates while owned file resources close; no retry,
rollback, cleanup routine or CLI interruption code is added.

## Input and privacy boundary

Use ordinary stable files under trusted quiescent local parents. Absolute and
supported relative child paths work; parent traversal, observed symlinks/reparse
components, special files and unsupported Windows spellings/providers are
refused. Hardlinked ordinary sources remain supported. File data is decoded
as JSON, never imported/evaluated/launched because of its extension.

Windows uses the adjacent native backend and fully spelled local fixed/removable
paths. UNC/device/drive-relative/root-relative/ADS spellings, reserved names,
trailing dots/spaces, invalid controls and observed short-name aliases are
refused. POSIX uses available no-follow/nonblocking flags and noninheritable
descriptors. Size/identity/time checks surround actual bounded reads; one
excess rejection byte can be consumed but is not decoded. Only unnamed data
is read, not named streams, ACLs, ownership or topology.

Neither API writes a selected report/input/output. Reads can affect OS access
metadata, while Python manages import caches separately; the demo uses `-B`.
Byte/depth limits are not total CPU, memory, result-size or elapsed-time quotas.
Checks have race windows and do not create atomic snapshots or an adversarial
filesystem sandbox. Network/virtual/live/provider, blocking native calls and
power-loss recovery are not equivalent acceptance. Read the preserved
[INPUT-CONTRACT.md](docs/INPUT-CONTRACT.md).

Redacted output can retain names, text, business data and unknown fields. Keep
actual inputs/results/exception objects and caller captures private. Omission
of paths from a message and replacement of known keys do not establish
anonymity, confidentiality, ownership or permission to share.

## Maintainer source packaging and qualification

The two source/build helpers use the standard library and refuse optimized
Python (`-O`, `-OO` or `PYTHONOPTIMIZE`). From reviewed committed repository
source, create a new private package:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
```

Create another new reference package from the same committed source and qualify
with `packaging/qualify.py --packages PACKAGE_DIR --reference-build REFERENCE_DIR
--workspace NEW_ABSOLUTE_WORKSPACE --report NEW_ABSOLUTE_REPORT_JSON`. Both input
artifact directories must exist; workspace/report must be new with existing
parents. A consumer/local run may omit the reference and honestly records both
`identical_*` flags false, supplying no independent Git-source rebuild proof.

Eight fresh Windows/Ubuntu Python lanes use no-pip/no-distribution venvs, the
five original shared bodies plus 40 input methods and real copied-library
consumer processes. Actual discovered/passed/skipped counts belong to release
`VALIDATION.json`. See [QUALIFICATION.md](docs/QUALIFICATION.md) and
[PROVENANCE.md](docs/PROVENANCE.md); no Python/runtime/dependency binary, real
input/result, original helper or raw log belongs in the source ZIP.
