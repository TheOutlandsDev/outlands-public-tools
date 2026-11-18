# Build an offline system status snapshot

Download the source ZIP and `SHA256SUMS.txt` from the release page.
Verify the ZIP digest before extracting it.

On Windows, compare the output of this PowerShell command with the ZIP entry
in `SHA256SUMS.txt`.

```powershell
Get-FileHash -Algorithm SHA256 .\system-status-snapshot-builder-0.1.0.zip
```

On Ubuntu, run this command from the download directory.

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Open a terminal at the extracted root. Use CPython 3.12 or 3.15 for the
`python` command. Install the hash-pinned tzdata wheel into a virtual
environment.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-runtime.txt
```

Ubuntu

```sh
python -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-runtime.txt
```

Save the following as `show_status.py` at the extracted root.

```python
from datetime import UTC, datetime
from zoneinfo import reset_tzpath

reset_tzpath(())

from production_planning.system_status import build_system_status

status = build_system_status(
    app_version="0.1.0-demo",
    app_environment=" Test ",
    latest_ingestion_at=datetime(2000, 1, 15, 17, 0, tzinfo=UTC),
    now=datetime(2000, 7, 15, 16, 0, tzinfo=UTC),
)
print(status["environment"], status["version"])
print(status["server_time"]["iso"], status["server_time"]["timezone"])
print(status["last_ingestion_status"])
if status["last_ingestion"] is not None:
    print(status["last_ingestion"]["iso"], status["last_ingestion"]["timezone"])
```

Run the script with your virtual environment's interpreter.

Windows PowerShell

```powershell
.\.venv\Scripts\python.exe show_status.py
```

Ubuntu

```sh
.venv/bin/python show_status.py
```

Expected output

```text
Development Environment 0.1.0-demo
2000-07-15T12:00:00-04:00 EDT
AVAILABLE
2000-01-15T12:00:00-05:00 EST
```

Set `latest_ingestion_at=None` to report `UNAVAILABLE` with a missing
`last_ingestion` value. If you omit `now`, the builder uses the current
clock. It treats timestamps without a timezone as UTC. Use
`reset_tzpath(())` in a fresh process before importing the builder to use
the pinned wheel for timezone lookups on both platforms.

To run the three original tests, install `requirements-test.txt` with the
same pip flags used for `requirements-runtime.txt`. Run the command below
from the extracted root, substituting `python` with
`.\.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on Ubuntu.

```text
python -B -c "from zoneinfo import reset_tzpath; reset_tzpath(()); import pytest; raise SystemExit(pytest.main(['-q', '-p', 'no:cacheprovider', 'tests']))"
```

The release's `VALIDATION.json` records the four tested environments,
dependency pins, test results, and checks against the extracted ZIP.
