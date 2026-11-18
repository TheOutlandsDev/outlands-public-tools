# Evaluate synthetic telemetry alerts

Download the source ZIP and `SHA256SUMS.txt` from the release page. Verify
the ZIP before extracting it.

On Windows, run this command in PowerShell and compare the result with the
ZIP digest in `SHA256SUMS.txt`.

```powershell
Get-FileHash -Algorithm SHA256 .\telemetry-alert-evaluator-0.1.0.zip
```

On Ubuntu, run this command from the download directory.

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Open a terminal at the extracted root. Use CPython 3.12 or 3.15 for the
`python` command. Save this example as `evaluate_samples.py` in that directory.

```python
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from sentinel_monitor.alerts import AlertEngine
from sentinel_monitor.config import DEFAULT_CONFIG
from sentinel_monitor.models import SystemSnapshot

first = SystemSnapshot(
    timestamp=datetime(2000, 1, 1, tzinfo=UTC),
    cpu_percent=96.0,
    per_cpu_percent=[96.0],
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
)

engine = AlertEngine(DEFAULT_CONFIG)
for seconds, cpu in [(0, 96.0), (1, 96.0), (2, 96.0), (62, 96.0), (902, 96.0), (903, 10.0)]:
    snapshot = replace(
        first,
        timestamp=first.timestamp + timedelta(seconds=seconds),
        cpu_percent=cpu,
        per_cpu_percent=[cpu],
        uptime_seconds=float(seconds),
    )
    emitted = engine.evaluate(snapshot)
    print(f"{seconds:>3}s {engine.overall_severity()} {len(emitted)}")
```

Run `python evaluate_samples.py`. Each line shows the elapsed time, active
severity, and number of alerts emitted for that sample.

```text
  0s normal 0
  1s normal 0
  2s critical 1
 62s critical 0
902s critical 1
903s normal 0
```

The default CPU critical threshold is 95%. An alert becomes active on the
third consecutive elevated sample. A steady critical reading repeats at the
15-minute boundary measured from the last emitted alert. The normal sample
clears the active alert. Submit samples in timestamp order, and keep the same
`AlertEngine` instance to retain alert state between samples.

The evaluator uses the supplied snapshots and Python's standard library. It
considers CPU, memory, and disk usage, GPU temperatures, and supported live
CPU and storage temperature sensors. Static sensor limits, such as a drive's
warning temperature, are excluded from live temperature evaluation.

To run the three original tests, create a virtual environment and install
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

The release's `VALIDATION.json` records the tested platforms, dependencies,
three original tests, and eight API checks from fresh ZIP extractions.
