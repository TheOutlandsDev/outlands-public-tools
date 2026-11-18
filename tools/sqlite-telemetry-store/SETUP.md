# Save a fictional telemetry snapshot

Download the source ZIP and `SHA256SUMS.txt` from the release page. Verify
the ZIP before extracting it.

On Windows, compare the output of this PowerShell command with the ZIP
digest in `SHA256SUMS.txt`.

```powershell
Get-FileHash -Algorithm SHA256 .\sqlite-telemetry-store-0.1.0.zip
```

On Ubuntu, run this command from the download directory.

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Open a terminal at the extracted root. Use CPython 3.12 or 3.15 for the
`python` command. The runtime uses Python's standard-library `sqlite3` module.

Save the following as `save_snapshot.py` at the extracted root.

```python
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from sentinel_monitor.models import AlertEvent, SystemSnapshot
from sentinel_monitor.storage import SqliteStore

boot_time = datetime(2000, 1, 1, tzinfo=UTC)
sample_time = boot_time + timedelta(minutes=5)
snapshot = SystemSnapshot(
    timestamp=sample_time,
    cpu_percent=25.0,
    per_cpu_percent=[25.0],
    cpu_frequency_mhz=None,
    memory_total_bytes=1024,
    memory_used_bytes=256,
    memory_available_bytes=768,
    memory_percent=25.0,
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
    uptime_seconds=300.0,
)
alert = AlertEvent(
    timestamp=sample_time,
    severity="warning",
    key="demo",
    label="Example alert",
    value=25.0,
    threshold=20.0,
    unit="%",
    message="Fictional reading crossed the example threshold.",
)

with TemporaryDirectory() as folder:
    database = Path(folder) / "telemetry-demo.db"
    store = SqliteStore(database, retention_days=30)
    try:
        session = store.start_session(boot_time)
        print("Previous session unclean", session.previous_unclean)
        store.log_snapshot(snapshot, [alert])
    except BaseException:
        store.close(clean_exit=False)
        raise
    else:
        store.close(clean_exit=True)

    with closing(sqlite3.connect(database)) as connection:
        print("Journal mode", connection.execute("PRAGMA journal_mode").fetchone()[0])
        print("Saved samples", connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0])
        print("Saved alerts", connection.execute("SELECT COUNT(*) FROM alerts").fetchone()[0])
        print("Clean exit", connection.execute("SELECT clean_exit FROM sessions").fetchone()[0])
```

Run `python save_snapshot.py`. The example writes to a temporary directory
and removes it when the script exits.

```text
Previous session unclean False
Journal mode wal
Saved samples 1
Saved alerts 1
Clean exit 1
```

For your own inputs, keep a dedicated local database and call
`start_session(boot_time)` once per run. Call `close(clean_exit=True)` on
normal shutdown. On a later run, an unclean session can be reported as a
possible application interruption or system restart based on the supplied
boot time.

Logging persists supplied details such as device identifiers, process names,
event messages, and alerts. Use fictional or approved inputs and keep
database files private when they contain identifying information. Retention
prunes expired snapshots, alerts, and hardware events using the supplied
snapshot time. Pass `enabled=False` to skip opening or writing the database.

To run the two original test cases, create a virtual environment and install
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

The release's `VALIDATION.json` records Windows and Ubuntu test results
from fresh ZIP extractions.
