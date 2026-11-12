# Fictional loopback-declaration walkthrough

Extract the [0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/connection-plan-checker-v0.1.0)
into a fresh folder and select normal Python **3.12–3.15**, with 3.15.2 selected
for that minor in qualification. The CLI needs only `connection_check.py` and
the standard library. Supply Python separately; no pip distribution, listener,
service, account, model or network connection is required by the checker.

The interface is `python -B connection_check.py --plan CONTROL_JSON`. `--plan`
is required; `--help` and `--version` are static. JSON goes to stdout. There is
no output-file option. A caller's shell redirection is separate and can
overwrite that caller's chosen capture file.

`NO_DECLARED_CONFLICTS` describes equality between supported declarations. It
does not prove that a port is available, a listener can start, a connection
works, or an operating-system configuration is safe. The checker opens no
sockets, resolves no DNS, inspects no processes, executes no programs and
installs no rules. Keep actual plans, identifying IDs and captures private.

## Run the complete fictional exercise

Create an existing user-owned private parent outside source. Save the single
Python block below as `fictional_walkthrough.py` there and run it unchanged
with two absolute arguments: extracted script and existing private parent.
PowerShell, with fictional paths:

```powershell
python -B 'D:\Private\connection-review\fictional_walkthrough.py' 'D:\Source\connection-plan-checker-0.1.0\connection_check.py' 'D:\Private\connection-review'
```

Ubuntu:

```sh
python3.12 -B '/absolute/private/connection-review/fictional_walkthrough.py' '/absolute/source/connection-plan-checker-0.1.0/connection_check.py' '/absolute/private/connection-review'
```

The driver creates a **new** `fictional-demo` child and refuses to reuse it.
It retains six invented controls, an unrelated file and a prior capture for
private inspection. All IDs, ports and relationships are authored examples;
the two supported address literals are schema values. No listener or other
program is started, and no actual configuration or operational record is used.

| Case | Exit | Complete JSON status | Observation |
| --- | ---: | --- | --- |
| `distinct` | 0 | `NO_DECLARED_CONFLICTS` | Four different tuples remain distinct. |
| `tcp_conflict` | 1 | `DECLARED_CONFLICTS` | All three repeated TCP members are marked. |
| `udp_conflict` | 1 | `DECLARED_CONFLICTS` | Repeated UDP declarations also conflict. |
| `separated_components` | 0 | `NO_DECLARED_CONFLICTS` | Changing transport, accepted address or port changes the tuple. |
| `ordered_groups` | 1 | `DECLARED_CONFLICTS` | Groups follow first appearance; checks and members keep declaration order. |
| `invalid_port` | 2 | `ERROR` / `PORT_INVALID` | A Boolean is not an integer port. |

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
    "network_probed", "programs_executed", "runtime_verified", "availability_verified",
), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def binding(identifier, transport="tcp", address="127.0.0.1", port=49152):
    return dict(id=identifier, transport=transport, address=address, port=port)


def plan(rows):
    return dict(schema_version=1, bindings=rows)


def expected(identifiers, groups=()):
    repeated = {identifier for group in groups for identifier in group}
    return dict(
        schema_version=1,
        status="DECLARED_CONFLICTS" if groups else "NO_DECLARED_CONFLICTS",
        scope="DECLARED_LOOPBACK_BINDINGS_ONLY", **FLAGS,
        counts=dict(bindings=len(identifiers), conflict_groups=len(groups),
                    conflicting_bindings=len(repeated)),
        checks=[dict(id=identifier,
                     status="CONFLICT" if identifier in repeated else "DISTINCT",
                     evidence="REPEATED_DECLARED_BINDING" if identifier in repeated
                     else "UNIQUE_DECLARED_BINDING") for identifier in identifiers],
        conflict_groups=[dict(ids=list(group)) for group in groups],
    )


distinct = [binding("sample_a"), binding("sample_b", transport="udp"),
            binding("sample_c", address="::1"), binding("sample_d", port=49153)]
tcp = [binding("sample_z"), binding("sample_a"), binding("sample_m")]
udp = [binding("sample_udp_a", transport="udp", address="::1"),
       binding("sample_udp_b", transport="udp", address="::1")]
separated = [binding("tcp_v4"), binding("udp_v4", transport="udp"),
             binding("tcp_v6", address="::1"),
             binding("udp_v6", transport="udp", address="::1"),
             binding("other_port", port=49153)]
ordered = [binding("group_z_first", port=49153),
           binding("group_a_first", transport="udp"),
           binding("group_a_second", transport="udp"),
           binding("distinct", address="::1"),
           binding("group_z_second", port=49153)]
cases = [
    ("distinct", plan(distinct), 0,
     expected(["sample_a", "sample_b", "sample_c", "sample_d"])),
    ("tcp_conflict", plan(tcp), 1,
     expected(["sample_z", "sample_a", "sample_m"],
              [["sample_z", "sample_a", "sample_m"]])),
    ("udp_conflict", plan(udp), 1,
     expected(["sample_udp_a", "sample_udp_b"], [["sample_udp_a", "sample_udp_b"]])),
    ("separated_components", plan(separated), 0,
     expected(["tcp_v4", "udp_v4", "tcp_v6", "udp_v6", "other_port"])),
    ("ordered_groups", plan(ordered), 1,
     expected(["group_z_first", "group_a_first", "group_a_second", "distinct", "group_z_second"],
              [["group_z_first", "group_z_second"], ["group_a_first", "group_a_second"]])),
    ("invalid_port", plan([binding("sample_invalid", port=True)]), 2,
     dict(status="ERROR", code="PORT_INVALID", **FLAGS)),
]
selected = []
for name, value, exit_code, result in cases:
    control = WORK / (name + ".json")
    write_new(control, (json.dumps(value, ensure_ascii=True, sort_keys=True) + "\n").encode())
    selected.append((name, control, exit_code, result))
write_new(WORK / "unrelated.txt", b"FICTIONAL_EXTRA_NOT_A_SELECTED_PLAN\n")
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
for name, control, exit_code, complete_expected in selected:
    completed = subprocess.run(
        [sys.executable, "-B", "-s", "-X", "utf8", str(SCRIPT), "--plan", str(control)],
        cwd=WORK, env=environment, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=60,
    )
    assert completed.returncode == exit_code, (name, "EXIT_MISMATCH")
    assert completed.stderr == "", (name, "UNEXPECTED_STDERR")
    assert completed.stdout.endswith("\n") and len(completed.stdout.splitlines()) == 1
    actual = json.loads(completed.stdout)
    assert actual == complete_expected, (name, "FULL_JSON_MISMATCH")
    assert str(WORK) not in completed.stdout.replace("\\\\", "\\")
    assert all('"' + key + '"' not in completed.stdout for key in ("transport", "address", "port"))
    assert "FICTIONAL_EXTRA_NOT_A_SELECTED_PLAN" not in completed.stdout
    assert snapshot_tree() == original, (name, "INPUT_TREE_OR_PRIOR_CAPTURE_CHANGED")
    assert sha(SCRIPT.read_bytes()) == runtime_hash, (name, "RUNTIME_CHANGED")
    results.append(dict(case=name, exit_code=completed.returncode, report=actual))

print(json.dumps(dict(
    cases=results, input_plans_tree_prior_output_and_runtime_bytes_preserved=True,
), ensure_ascii=True, sort_keys=True, indent=2))
```

The driver checks sampled byte/tree preservation, not access times, every OS
property or ACL privacy. Its requested private file modes remain subject to the
actual OS, Python and inherited permissions. There is no automatic cleanup or
rollback. Inspect the retained invented work before removing it yourself.

## Interpret the declaration contract

The root has exactly `schema_version` and `bindings`. Version is integer 1.
Each binding has exactly `id`, `transport`, `address` and `port`. IDs are unique
neutral ASCII tokens matching `[a-z][a-z0-9_-]{0,39}`. Transport is exactly `tcp`
or `udp`; address is exactly `127.0.0.1` or `::1`; port is an integer from
**1 through 65535**. Boolean, floating-point and string ports are refused.
The selected UTF-8 JSON may include a BOM and is at most **64 KiB**, with
**1–128 bindings**. Unknown fields, duplicate keys/IDs, wrong types, address
aliases and nonstandard numbers are input errors. These are not complete
CPU/memory/I/O quotas.

Two bindings conflict only when all three declared fields match exactly:
transport, accepted address literal and port. Every member of a repeated tuple
is marked `CONFLICT`, including UDP declarations. Distinct transports and the
two different address literals remain separate. This is not a model of every
OS bind, dual-stack, wildcard, exclusive-use or reuse rule.

Checks retain input order. Groups retain the first appearance of their tuple;
members retain declaration order. Groups are not alphabetically sorted, and
the checker does not choose a preferred owner or repair a conflict. It does
not validate actual listeners, port availability, reachability or policy.

## Privacy, paths and remaining limits

Results retain IDs, counts, statuses and grouping relationships. Raw transport,
address and port fields, selected paths and native errors are omitted. IDs and
relationships can still identify an operational design. Fixed CLI errors do
not anonymize library tracebacks or caller captures. All four verification
flags remain false on success, conflicts and errors.

Use fully spelled canonical paths and stable trusted local inputs. The reader
requires an ordinary single-link file and ordinary ancestors, and samples
descriptor/path identity around a bounded read. Component checks happen after
absolute-path normalization. Local Windows fictional probes on Python 3.12.7
and 3.15.2 accepted leaf trailing-dot, leaf trailing-space and parent
trailing-dot spellings, while refusing the parent trailing-space spelling.
This is retained normalization behavior, not a blanket suffix-refusal or
alias-safety guarantee. Do not rely on those aliases. Observed links/reparse
points, special files, stream/device/UNC forms, traversal and reserved names
are unsupported inputs.

The reader does not hold an atomic snapshot, deny concurrent writers or enforce
a hostile-filesystem sandbox. Remote/mounted/virtual/live-changing storage,
mount rebinding and blocked OS I/O remain outside the qualification. Reads can
affect access metadata, and Python caches are separate; this guide uses `-B`.
Exit 130 means interruption; a partial or failed stdout capture is not a
completed report. No input, output or test authorizes execution, configuration
changes or publication of actual plans. Read the preserved [contract](README.md),
[private workspace guide](docs/PRIVATE-WORKSPACE.md),
[qualification boundary](docs/QUALIFICATION.md) and [provenance](docs/PROVENANCE.md)
before using your own private declarations.
