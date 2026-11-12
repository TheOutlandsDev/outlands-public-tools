# Fictional maintenance-planning walkthrough

Extract the [Server Maintenance Planner 0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/server-maintenance-v0.1.0). Supply ordinary CPython 3.12, 3.13, 3.14 or 3.15; qualification selects 3.15.2 for that minor. Keep both runtime files adjacent. The planner needs only the standard library and the host OS APIs. No administrator privilege, activation, execution-policy change, package installation or account is part of these commands. Actual file/executable permissions and workplace policies still apply.

Use an existing trusted private parent outside source and public/synchronized checkouts. Create a new optional no-pip environment there, then call its Python directly. The paths below are explicitly fictional placeholders; replace them with your actual source, Python and private parent. Choose a new environment path.

PowerShell:

```powershell
$source = 'D:\Source\server-maintenance-0.1.0'
$privateWork = 'D:\Private\maintenance-review'
python -I -B -m venv --without-pip (Join-Path $privateWork 'new-environment')
$py = Join-Path $privateWork 'new-environment\Scripts\python.exe'
& $py -I -B (Join-Path $source 'maintenance.py') --help
```

Ubuntu, with fictional absolute paths:

```sh
source=/path/to/server-maintenance-0.1.0
private_work=/path/to/private-maintenance-review
python3 -I -B -m venv --without-pip "$private_work/new-environment"
py="$private_work/new-environment/bin/python"
"$py" -I -B "$source/maintenance.py" --help
```

Help is ordinary argparse help. Windows uses the fixed program name `maintenance.py`; the preserved POSIX help behavior can reflect the invoked script name. Do not rely on help as a universal redaction API. Unknown arguments, including `--version`, are handled input errors rather than a version feature.

## Run all seven examples unchanged

Save the single Python block below as `fictional_walkthrough.py` in your private parent. It creates a new uniquely named fixture directory under that parent, writes five invented JSON inputs and retains them for inspection. The planner creates no files. Every invocation uses the selected interpreter in a fresh process, checks the complete JSON and output bytes, and verifies that the five fixture contents and runtime bytes stay unchanged.

The example calendar is an invented January 2030 exercise, not a selected maintenance date. The restart result contains checklist words, not executed commands. Valid blocked plans and incomplete readiness declarations return exit 0. The final two cases return exit 2 with fixed error JSON. Every result has `execution_performed: false`.

PowerShell:

```powershell
& $py -I -B (Join-Path $privateWork 'fictional_walkthrough.py') (Join-Path $source 'maintenance.py') $privateWork
```

Ubuntu:

```sh
"$py" -I -B "$private_work/fictional_walkthrough.py" "$source/maintenance.py" "$private_work"
```

```python
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

assert len(sys.argv) == 3
script = Path(sys.argv[1]).resolve()
parent = Path(sys.argv[2]).resolve()
assert script.is_file() and script.name == "maintenance.py"
assert parent.is_absolute() and parent.is_dir()
assert not parent.is_symlink() and not getattr(parent, "is_junction", lambda: False)()
runtime = {name: hashlib.sha256(script.with_name(name).read_bytes()).hexdigest()
           for name in ("maintenance.py", "maintenance_windows.py")}
work = Path(tempfile.mkdtemp(prefix="fictional-maintenance-", dir=parent))
plan = dict(action="restart", state="running", players=0,
            observation_age_seconds=30, maximum_age_seconds=300,
            cooldown_remaining_seconds=0, previous_attempt="completed",
            target_verified=True, backup_verified=True)
ready = dict(target_verified=True, new_instance=True,
             fresh_log_markers=True, probe_succeeded=True)
inputs = {
    "plan.json": json.dumps(plan, sort_keys=True) + "\n",
    "players.json": json.dumps(dict(plan, players=3), sort_keys=True) + "\n",
    "readiness.json": json.dumps(ready, sort_keys=True) + "\n",
    "incomplete.json": json.dumps(dict(ready, new_instance=False), sort_keys=True) + "\n",
    "invalid.json": '{"action":"restart","action":"stop"}\n',
}
for name, text in inputs.items():
    with (work / name).open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
snapshot = lambda: {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in work.iterdir() if p.is_file()}
before = snapshot()
assert set(before) == set(inputs)
error = dict(status="ERROR", code="PLAN_INPUT_INVALID", execution_performed=False)
cases = [
    ("calendar", ["calendar", "--year", "2030", "--month", "1", "--weekday", "0", "--offset-days", "7"], 0,
     dict(anchor="2030-01-07", followup="2030-01-14", next_anchor="2030-02-04",
          weekday=0, time_of_day="operator_selected", timezone="operator_selected",
          execution_performed=False)),
    ("restart_ready", ["plan", "--input", str(work / "plan.json")], 0,
     dict(status="PLAN_READY", action="restart",
          steps=["notify", "request_save", "request_stop", "verify_stopped",
                 "refresh_backup", "verify_backup_pin", "start",
                 "verify_new_instance", "verify_fresh_readiness"],
          execution_performed=False)),
    ("players_present", ["plan", "--input", str(work / "players.json")], 0,
     dict(status="PLAYERS_PRESENT", action="restart", steps=[], execution_performed=False)),
    ("readiness_complete", ["readiness", "--input", str(work / "readiness.json")], 0,
     dict(status="OBSERVATIONS_COMPLETE", missing=[], execution_performed=False)),
    ("readiness_incomplete", ["readiness", "--input", str(work / "incomplete.json")], 0,
     dict(status="NOT_ESTABLISHED", missing=["new_instance"], execution_performed=False)),
    ("duplicate_keys", ["plan", "--input", str(work / "invalid.json")], 2, error),
    ("invalid_arguments", ["--unknown", "FICTIONAL_SENTINEL"], 2, error),
]
env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}
env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
records = []
for name, arguments, code, expected in cases:
    done = subprocess.run([sys.executable, "-I", "-B", str(script), *arguments],
                          cwd=work, env=env, capture_output=True, timeout=30)
    newline = "\r\n" if os.name == "nt" else "\n"
    expected_stdout = (json.dumps(expected, sort_keys=(code == 0)) + newline).encode("utf-8")
    assert done.returncode == code and done.stdout == expected_stdout and done.stderr == b"", name
    value = json.loads(done.stdout)
    assert value == expected and value["execution_performed"] is False, name
    assert snapshot() == before and {p.name for p in work.iterdir()} == set(inputs), name
    records.append(dict(case=name, exit_code=code, value=value,
                        stdout=done.stdout.decode("utf-8"), stderr=done.stderr.decode("utf-8")))
assert runtime == {name: hashlib.sha256(script.with_name(name).read_bytes()).hexdigest()
                   for name in runtime}
assert not list(work.rglob("*.pyc"))
print(json.dumps(dict(status="FICTIONAL_MAINTENANCE_WALKTHROUGH", cases=records,
                      cases_checked=7, valid_declarations=5, fixed_refusals=2,
                      fixture_files=5, fixture_sha256=before,
                      runtime_sha256=runtime, planner_files_created=0,
                      execution_performed=False, source_bytecode_files=0), sort_keys=True))
```

A successful wrapper returns `FICTIONAL_MAINTENANCE_WALKTHROUGH` with seven checked cases, five valid declarations, two fixed refusals and five retained fixture hashes. It exits after verification; it does not delete or overwrite an old directory. Repeating it creates a different new private fixture directory. The wrapper writes the five fixtures; `planner_files_created: 0` describes the planner calls, not the wrapper's setup or OS metadata activity.

The result statuses are `PLAN_READY`, `PLAYERS_PRESENT`, `OBSERVATIONS_COMPLETE`, `NOT_ESTABLISHED` and `ERROR`. Calendar output leaves time of day and timezone `operator_selected`. `OBSERVATIONS_COMPLETE` accepts declared booleans and does not probe or establish real readiness. Keep actual inputs and any caller-saved stdout or logs private.

## Verify the download and qualification

Download `SHA256SUMS.txt`, `build-manifest.json`, `VALIDATION.json`, `USAGE.md` and the source ZIP together from the same release. Verify the four listed SHA-256 values using a trusted checksum tool before extracting. Checksums establish byte agreement with the selected review, not authorship or permission to use private data.

`source_check.py` verifies the finite source inventory. `packaging/build.py --out NEW_EXTERNAL_DIRECTORY` builds the reviewed committed source; its Git source check requires a checkout at the reviewed commit. `packaging/qualify.py --packages PACKAGES --workspace NEW_WORKSPACE --report NEW_REPORT` performs archive extraction, a fresh no-pip/no-distribution environment and selected tests. Hosted qualification also supplies `--reference-build` from an independent source rebuild. Reports and workspaces are new external paths. The helper flags and precise gates are described in [qualification](docs/QUALIFICATION.md).

The eight lanes select 61 original and 30 copied-runtime methods each: 91 per lane, 728 total. Actual Python patches, platforms, hashes, named skips and results are in `VALIDATION.json`. The preserved [input-safety contract](INPUT-SAFETY.md) records limits and earlier observations separately. [Private workspace guidance](docs/PRIVATE-WORKSPACE.md) explains what should remain outside the release.
