# Fictional flat-settings walkthrough

Extract the [0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/configuration-contract-checker-v0.1.0)
into a fresh folder and select normal Python **3.12–3.15**, with 3.15.2 selected
for that minor in qualification. The CLI needs only `config_check.py` and the
standard library. Supply Python separately; no pip distribution, application,
service, account, model or network connection is required by the checker.

The interface is `python -B config_check.py --contract CONTRACT_JSON --settings
SETTINGS_JSON`. Both selections are required; `--help` and `--version` are
static. JSON goes to stdout. There is no output-file option. A caller's shell
redirection is separate and can overwrite that caller's chosen capture file.

`NO_DECLARED_VIOLATIONS` means the supplied settings meet this declared flat
contract. It does not prove that an application accepts the configuration,
dependencies work, or an actual configuration is secure or ready to run. The
checker contacts no hosts, inspects no running software, executes no programs,
installs no packages and modifies no configuration. Keep actual contracts,
settings, identifying IDs and captures private.

## Run the complete fictional exercise

Create an existing user-owned private parent outside source. Save the single
Python block below as `fictional_walkthrough.py` there and run it unchanged
with two absolute arguments: extracted script and existing private parent.
PowerShell, with fictional paths:

```powershell
python -B 'D:\Private\settings-review\fictional_walkthrough.py' 'D:\Source\configuration-contract-checker-0.1.0\config_check.py' 'D:\Private\settings-review'
```

Ubuntu:

```sh
python3.12 -B '/absolute/private/settings-review/fictional_walkthrough.py' '/absolute/source/configuration-contract-checker-0.1.0/config_check.py' '/absolute/private/settings-review'
```

The driver creates a **new** `fictional-demo` child and refuses to reuse it.
It retains one invented contract, seven invented settings files, an unrelated
file and a prior capture for private inspection. All IDs, keys, values, bounds
and choices are authored examples. No actual application configuration or
operational record is used. No input is applied to another program.

| Case | Exit | Complete JSON status | Observation |
| --- | ---: | --- | --- |
| `valid` | 0 | `NO_DECLARED_VIOLATIONS` | Four fields and the ordering rule pass. |
| `optional_absent` | 0 | `NO_DECLARED_VIOLATIONS` | An unused optional field is `NOT_SUPPLIED`, not `PASS`. |
| `ordering_failure` | 1 | `REVIEW_REQUIRED` | Individually valid integers violate their declared order. |
| `missing_operand` | 1 | `REVIEW_REQUIRED` | Missing lower operand blocks before the invalid present upper operand is compared. |
| `invalid_operand` | 1 | `REVIEW_REQUIRED` | Both operands exist, but a Boolean fails the integer field and blocks the rule. |
| `unexpected_key` | 1 | `REVIEW_REQUIRED` | The extra settings key is counted without naming it. |
| `invalid_settings` | 2 | `ERROR` / `SETTINGS_VALUE_UNSUPPORTED` | A nested object is outside the flat settings schema. |

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
    "network_probed", "programs_executed", "configuration_modified", "runtime_verified",
), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def checked(identifier, status="PASS", evidence="PRESENT_VALID", kind="field"):
    return dict(id=identifier, kind=kind, status=status, evidence=evidence)


def expected(rows, unexpected=0):
    counts = {key: sum(row["status"] == status for row in rows)
              for key, status in (("passed", "PASS"), ("failed", "FAIL"),
                                  ("not_supplied", "NOT_SUPPLIED"), ("blocked", "BLOCKED"))}
    counts["unexpected_settings"] = unexpected
    return dict(
        schema_version=1,
        status="REVIEW_REQUIRED" if counts["failed"] or counts["blocked"] or unexpected
        else "NO_DECLARED_VIOLATIONS",
        scope="DECLARED_FLAT_SETTINGS_ONLY", **FLAGS,
        counts=counts, checks=rows,
        issues=["SETTINGS_KEYS_UNDECLARED"] if unexpected else [],
    )


contract = dict(schema_version=1, fields=[
    dict(id="sample_lower", key="FictionalLower", type="integer", required=True,
         minimum=0, maximum=10),
    dict(id="sample_upper", key="FictionalUpper", type="integer", required=False,
         minimum=0, maximum=10),
    dict(id="sample_mode", key="FictionalMode", type="string", required=False,
         choices=["fictional", "example"]),
    dict(id="sample_enabled", key="FictionalEnabled", type="boolean", required=True),
], rules=[dict(id="sample_order", op="less_or_equal", left="sample_lower", right="sample_upper")])
valid = dict(FictionalLower=3, FictionalUpper=7, FictionalMode="fictional", FictionalEnabled=True)
clean = [checked("sample_lower"), checked("sample_upper"), checked("sample_mode"),
         checked("sample_enabled"),
         checked("sample_order", kind="rule", evidence="INTEGER_ORDER_SATISFIED")]
cases = [
    ("valid", valid, 0, expected(clean)),
    ("optional_absent", dict(FictionalLower=3, FictionalUpper=7, FictionalEnabled=True), 0,
     expected([checked("sample_lower"), checked("sample_upper"),
               checked("sample_mode", "NOT_SUPPLIED", "OPTIONAL_SETTING_NOT_SUPPLIED"),
               checked("sample_enabled"),
               checked("sample_order", kind="rule", evidence="INTEGER_ORDER_SATISFIED")])),
    ("ordering_failure", dict(valid, FictionalLower=8, FictionalUpper=3), 1,
     expected([checked("sample_lower"), checked("sample_upper"), checked("sample_mode"),
               checked("sample_enabled"),
               checked("sample_order", "FAIL", "INTEGER_ORDER_VIOLATED", "rule")])),
    ("missing_operand", dict(FictionalUpper=11, FictionalEnabled=True), 1,
     expected([checked("sample_lower", "FAIL", "REQUIRED_SETTING_MISSING"),
               checked("sample_upper", "FAIL", "ABOVE_MAXIMUM"),
               checked("sample_mode", "NOT_SUPPLIED", "OPTIONAL_SETTING_NOT_SUPPLIED"),
               checked("sample_enabled"),
               checked("sample_order", "BLOCKED", "DEPENDENCY_NOT_SUPPLIED", "rule")])),
    ("invalid_operand", dict(valid, FictionalLower=True), 1,
     expected([checked("sample_lower", "FAIL", "TYPE_MISMATCH"),
               checked("sample_upper"), checked("sample_mode"), checked("sample_enabled"),
               checked("sample_order", "BLOCKED", "DEPENDENCY_INVALID", "rule")])),
    ("unexpected_key", dict(valid, FictionalExtra="invented"), 1, expected(clean, unexpected=1)),
    ("invalid_settings", dict(valid, FictionalMode={"nested": "invented"}), 2,
     dict(status="ERROR", code="SETTINGS_VALUE_UNSUPPORTED", **FLAGS)),
]
CONTROL = WORK / "contract.json"
write_new(CONTROL, (json.dumps(contract, ensure_ascii=True, sort_keys=True) + "\n").encode())
selected = []
for name, values, exit_code, result in cases:
    settings = WORK / (name + ".json")
    write_new(settings, (json.dumps(values, ensure_ascii=True, sort_keys=True) + "\n").encode())
    selected.append((name, settings, exit_code, result))
write_new(WORK / "unrelated.txt", b"FICTIONAL_EXTRA_NOT_A_SELECTED_INPUT\n")
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
for name, settings, exit_code, complete_expected in selected:
    completed = subprocess.run(
        [sys.executable, "-B", "-s", "-X", "utf8", str(SCRIPT),
         "--contract", str(CONTROL), "--settings", str(settings)],
        cwd=WORK, env=environment, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=60,
    )
    assert completed.returncode == exit_code, (name, "EXIT_MISMATCH")
    assert completed.stderr == "", (name, "UNEXPECTED_STDERR")
    assert completed.stdout.endswith("\n") and len(completed.stdout.splitlines()) == 1
    actual = json.loads(completed.stdout)
    assert actual == complete_expected, (name, "FULL_JSON_MISMATCH")
    assert str(WORK) not in completed.stdout.replace("\\\\", "\\")
    assert "Fictional" not in completed.stdout and '"choices"' not in completed.stdout
    assert "FICTIONAL_EXTRA_NOT_A_SELECTED_INPUT" not in completed.stdout
    assert snapshot_tree() == original, (name, "INPUT_TREE_OR_PRIOR_CAPTURE_CHANGED")
    assert sha(SCRIPT.read_bytes()) == runtime_hash, (name, "RUNTIME_CHANGED")
    results.append(dict(case=name, exit_code=completed.returncode, report=actual))

print(json.dumps(dict(
    cases=results, input_contract_settings_tree_prior_output_and_runtime_bytes_preserved=True,
), ensure_ascii=True, sort_keys=True, indent=2))
```

The driver checks sampled byte/tree preservation, not access times, every OS
property or ACL privacy. Its requested private file modes remain subject to the
actual OS, Python and inherited permissions. There is no automatic cleanup or
rollback. Inspect the retained invented work before removing it yourself.

## Interpret the declared contract

The contract root has exactly `schema_version`, `fields` and `rules`. Version
is integer 1. Declare **1–128 fields**, **0–128 rules** and at most **128 settings
keys**. Both selected UTF-8 inputs may include a BOM; each is at most **64 KiB**.
Fields support actual booleans, signed 64-bit integers and strings of at most
4096 Unicode code points. String choices contain **1–32 unique strings**, each
at most 128 code points. Integer and string bounds are inclusive. These are not
complete CPU/memory/I/O quotas. See the [exact schema](README.md) before writing
another contract.

Types and settings keys are exact. There is no coercion, trimming, case folding,
Unicode normalization, environment/home expansion, default filling, expression
language or arbitrary validator. A Boolean is not an integer. IDs share one
unique namespace across fields and rules; rule operands reference two distinct
declared integer field IDs, not settings keys or other rules. Repeated ordered
operand pairs, unknown fields, duplicate keys/IDs, contradictory constraints
and unsupported flat-settings values are input errors.

Missing required values fail; missing optional values are `NOT_SUPPLIED`.
An unused optional absence can coexist with exit 0. A missing rule operand
always produces `BLOCKED` / `DEPENDENCY_NOT_SUPPLIED`, even if the other operand
is present but invalid. When both exist, any field failure blocks with
`DEPENDENCY_INVALID`. The `less_or_equal` rule compares only two individually
valid integers. A blocked rule never silently passes. Unexpected settings keys
require review and are counted without echoing names or values.

Checks retain field declaration order, followed by rule declaration order.
Exit 0 is `NO_DECLARED_VIOLATIONS`; exit 1 is `REVIEW_REQUIRED`; exit 2 is a fixed
`ERROR`. All four flags remain false on every path. No defaults are applied,
configuration is repaired or application behavior is verified.

## Privacy, paths and remaining limits

Results retain declared IDs, kinds, counts, statuses and fixed evidence.
Settings key names, raw values, bounds, choices, selected paths and native
errors are omitted. IDs and evidence can still reveal an operational design.
Fixed CLI errors do not anonymize library tracebacks or caller captures.

Use fully spelled canonical paths and stable trusted local inputs. Each reader
requires an ordinary single-link file and ordinary ancestors, and samples
descriptor/path identity around a bounded read. Component checks happen after
absolute-path normalization. Local Windows fictional probes on Python 3.12.7
and 3.15.2 observed the same behavior for both contract and settings selections:
leaf trailing-dot, leaf trailing-space and parent trailing-dot spellings were
accepted; parent trailing-space was refused. This is retained normalization
behavior, not a blanket suffix-refusal or alias-safety guarantee. Do not rely
on those aliases. Observed links/reparse points, special files, stream/device/UNC
forms, traversal and reserved names are unsupported inputs.

The two inputs are read sequentially, not as an atomic pair. The reader does
not hold an atomic snapshot, deny concurrent writers or enforce a
hostile-filesystem sandbox. Remote/mounted/virtual/live-changing storage, mount
rebinding and blocked OS I/O remain outside the qualification. Reads can affect
access metadata, and Python caches are separate; this guide uses `-B`. Exit 130
means interruption; a partial or failed stdout capture is not a completed report.
No input, output or test authorizes application changes, program execution or
publication of actual settings. Read the [private workspace guide](docs/PRIVATE-WORKSPACE.md),
[qualification boundary](docs/QUALIFICATION.md) and [provenance](docs/PROVENANCE.md)
before using your own private declarations.
