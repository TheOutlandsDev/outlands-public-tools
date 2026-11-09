# Install and use the maintenance and service tools

These four independent MIT wheels review supplied maintenance declarations
without reading equipment or changing operational records. Supply Python 3.12
or 3.13; runtime dependencies are the standard library only. See the
[terms and evidence limits](../../methodology/MAINTENANCE-SERVICE.md) and
[component contracts](components.json).

| Tool | Selected question | Boundary |
| --- | --- | --- |
| [Meter history checker](../../tools/meter-history-checker/README.md) | Do supplied readings and reset boundaries yield a consistent usage history? | Does not collect or verify a physical reading. |
| [Maintenance due planner](../../tools/maintenance-due-planner/README.md) | What due state follows from selected intervals, as-of ordinal and declared usage? | Does not judge interval suitability or schedule service. |
| [Work-order lifecycle checker](../../tools/work-order-lifecycle-checker/README.md) | Does a declared order snapshot match its revision and state events? | Does not dispatch or update an order. |
| [Service completion checker](../../tools/service-completion-checker/README.md) | Do declared tasks, parts and evidence match a pinned order contract? | Does not inspect evidence bytes or approve physical work. |

Reports retain selected identifiers and hashes. Keep real inputs and reports
private. A PASS is consistency under one tool's stated contract, not proof of
physical service, meter provenance, actual stock movement or authorization.

## Install

Download selected wheels and SHA256SUMS.txt from the
[v1.0.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/maintenance-service-wheels-v1.0.0).
Verify hashes before installing. Create a fresh environment outside this
checkout with Python 3.12 or 3.13 and run:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_meter_history_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-maintenance-service-collection==1.0.0
```

The collection requires all five wheels in one directory and pins its four
components exactly. Run `outlands-maintenance-service` to list commands.
Each component has `outlands-TOOL-demo` for an embedded fictional example and
`outlands-TOOL --input PRIVATE_JSON` for explicit private input. CLI exit codes
are 0 PASS, 1 REVIEW_REQUIRED, 2 refusal and 130 interruption. The source
guides document bounded schemas, result meanings and guarded fresh outputs.

## Python API

Each package exposes `check(raw_json_bytes)`. For example:

```python
from importlib.resources import files
from outlands_meter_history_checker.meters import check

raw = files("outlands_meter_history_checker").joinpath("examples", "input.json").read_bytes()
report = check(raw)
assert report["status"] == "PASS"
assert report["snapshots"][0]["total_usage"] == 12
assert report["live_reading_collected"] is False
```

Run `python -B integrations/maintenance-service/exercise.py` in an environment
with the collection installed. It uses only embedded fictional examples and
checks four positive cases, four review cases, a repeated declared meter total
and an exact work-order snapshot pin used by the completion example.

The due example repeats the meter example's computed total as a *supplied
declaration*. Its `source_sha256` is not a receipt from the meter checker and
the due tool does not verify that source. The completion example pins the
fictional work-order snapshot, but neither tool checks physical service or
evidence bytes. No equipment, scheduler, stock system or work-order application
is contacted.

## Package verification

`build_wheels.py` reads only SOURCE-MANIFEST-pinned public source and fictional
examples. `verify_wheels.py` checks wheel members, RECORD hashes, fixed ZIP
metadata, exact release hashes, fresh individual installs, the collection,
commands, APIs and positive/review examples. `compare.py` checks byte-identical
platform builds. `public_download.py` anonymously verifies public assets and
repeats fresh installs. Build output must be an existing empty directory outside
the repository.
