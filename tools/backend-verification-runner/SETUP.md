# Generate a fictional verification report

Download the source ZIP and `SHA256SUMS.txt` from the release page.
Verify the ZIP digest before extracting.

Windows PowerShell

```powershell
Get-FileHash -Algorithm SHA256 .\backend-verification-runner-0.1.0.zip
```

Ubuntu

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Open a terminal at the extracted root. Use Python 3.12 or 3.15 in place of
`python` if needed.

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

Save the following example as `demo_report.py` at the extracted root.

```python
from datetime import UTC, datetime
import json
from pathlib import Path

from production_planning.backend_verification import (
    VerificationSpec,
    observation,
    run_backend_verification,
)

def demo_check(row):
    spec = VerificationSpec(
        check_id=row["check_id"], category=row["category"], label=row["label"]
    )

    def check():
        return observation(row["status"], row["detail"], **row["metrics"])

    return spec, check

rows = json.loads(Path("examples/demo_checks.json").read_text(encoding="utf-8"))
report = run_backend_verification(
    app_version="0.1.0-demo",
    checks=(demo_check(row) for row in rows),
    now=lambda: datetime(2000, 2, 10, 14, 30, tzinfo=UTC),
)
print(report.overall_status, report.passed_count, report.warning_count, report.failed_count)
print(report.result_sha256)
```

Run `.\.venv\Scripts\python.exe demo_report.py` on Windows or
`.venv/bin/python demo_report.py` on Ubuntu.

The first line prints `PASS_WITH_WARNINGS 1 1 0`. The second prints the
same fingerprint for the same inputs, check order, and timestamp. Even one
failed check makes the overall result `FAIL`. Use a timezone-aware clock
and provide between 1 and 32 checks with unique, normalized IDs.

The runner invokes callbacks directly, so use trusted read-only callbacks.
The report flags describe the expected callback behavior. Supply public
values for check labels, details, and metrics. If a callback raises an
exception, the runner records the exception class and a fixed failure
message. The example needs no database or network connection after setup.

Install `requirements-test.txt` with the same pip flags to run the five
tests from the extracted root. Use the virtual environment's interpreter
for `python -B -m pytest -q -p no:cacheprovider tests`. The release's
`VALIDATION.json` lists the tested platforms, pinned dependencies, and
fresh-extraction checks.
