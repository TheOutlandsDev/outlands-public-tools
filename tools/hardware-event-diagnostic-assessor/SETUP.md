# Assess a fictional hardware event

Download the source ZIP and `SHA256SUMS.txt` from the release page. Verify
the ZIP before extracting it.

On Windows, run this command in PowerShell and compare the output with the
ZIP digest in `SHA256SUMS.txt`.

```powershell
Get-FileHash -Algorithm SHA256 .\hardware-event-diagnostic-assessor-0.1.0.zip
```

On Ubuntu, run this command from the download directory.

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Open a terminal at the extracted root. Use CPython 3.12 or 3.15 for the
`python` command. The runtime uses the Python standard library.

Save the following as `assess_samples.py` at the extracted root.

```python
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from sentinel_monitor.diagnostic_engine import DiagnosticEngine
from sentinel_monitor.models import HardwareEvent, SystemSnapshot

start = datetime(2000, 1, 1, tzinfo=UTC)
event = HardwareEvent(
    channel="System",
    record_id=1,
    timestamp=start,
    category="WHEA PCIe",
    severity="critical",
    provider="Microsoft-Windows-WHEA-Logger",
    event_id=17,
    message="Fictional PCIe warning for the walkthrough.",
)
first = SystemSnapshot(
    timestamp=start,
    cpu_percent=10.0,
    per_cpu_percent=[10.0],
    cpu_frequency_mhz=None,
    memory_total_bytes=100,
    memory_used_bytes=20,
    memory_available_bytes=80,
    memory_percent=20.0,
    swap_total_bytes=0,
    swap_used_bytes=0,
    swap_percent=0.0,
    disks=[],
    disk_read_bps=0.0,
    disk_write_bps=0.0,
    network_receive_bps=0.0,
    network_send_bps=0.0,
    gpus=[],
    hardware_sensors=[],
    processes=[],
    uptime_seconds=0.0,
    source_status={"Windows diagnostics": "Active: Synthetic fixture"},
    hardware_events=[event],
)

engine = DiagnosticEngine(auto_clear_samples=2, session_started=start)
for seconds, events in [(0, [event]), (1, []), (2, [])]:
    snapshot = replace(
        first,
        timestamp=start + timedelta(seconds=seconds),
        uptime_seconds=float(seconds),
        hardware_events=events,
    )
    result = engine.evaluate(snapshot)
    print(seconds, result.status, result.severity, result.auto_cleared)
```

Run `python assess_samples.py`. Each line shows elapsed seconds, status,
severity, and whether the engine cleared the finding.

```text
0 active critical False
1 monitoring warning False
2 resolved normal True
```

Keep one `DiagnosticEngine` for a session and submit snapshots in timestamp
order. Use timezone-aware timestamps for the session start and events.
An event at the session start counts as active. Earlier events enter the
historical assessment. The two clean samples in the example move the active
finding through monitoring to resolved. With `engine.acknowledge()`, the
engine marks the current assessment acknowledged.

The engine reads the snapshots you supply and returns an assessment with
recommendation text. Messages about collector retries describe the wider
monitor. The example uses fictional event text because the assessment can
quote supplied messages.

To run the five original test cases, create a virtual environment and install
the pinned test dependencies.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-test.txt
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests
```

Ubuntu

```sh
python -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-test.txt
.venv/bin/python -B -m pytest -q -p no:cacheprovider tests
```

The release's `VALIDATION.json` records the four qualification environments
and test results from fresh ZIP extractions.
