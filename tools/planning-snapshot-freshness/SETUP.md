# Report freshness for a set of planning timestamps

Download the source ZIP and `SHA256SUMS.txt` from the release page.
Verify the ZIP digest before extracting it.

Windows PowerShell

```powershell
Get-FileHash -Algorithm SHA256 .\planning-snapshot-freshness-0.1.0.zip
```

Ubuntu

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Open a terminal at the extracted root. Use CPython 3.12 or 3.15 in place
of `python` if your default interpreter is different.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe
```

Ubuntu

```sh
python -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python
```

Paste the example into the Python prompt.

```python
from datetime import date, datetime
import json
from pathlib import Path

from production_planning.flex_data_freshness import (
    build_flex_data_freshness,
    build_flex_data_freshness_view,
)

timestamps = json.loads(Path("examples/demo_timestamps.json").read_text(encoding="utf-8"))
inputs = {
    name: date.fromisoformat(value) if name == "comparison_planning_date"
    else datetime.fromisoformat(value)
    for name, value in timestamps.items()
}
sources = build_flex_data_freshness(**inputs)
report = build_flex_data_freshness_view(
    sources, source_ids=("current-orders", "accepted-wip"), show_operational_warning=True
)
snapshot = report.sources[1]
print(snapshot.freshness, snapshot.age_hours, report.show_warning)
```

The example prints `STALE 73 True`. The classifier uses the source revision
time for age and displays the acceptance timestamp separately. The snapshot
stays fresh through 24 completed hours, becomes aging at 25, and becomes
stale at 73. Future revisions report zero age. Pass `None` for a source
date you lack. Missing operational dates become unavailable, and external
evidence stays explicitly pending.

Use timezone-aware datetimes when you have them. Naive timestamps are treated
as UTC. The formatter reads the New York rules from the pinned tzdata wheel
and displays the applicable daylight or standard time. Pass an explicit UTC
`evaluated_at` to reproduce a report later. The view flag controls display
only. The API reads the supplied values and never queries a live source.

Install `requirements-test.txt` with the same pip flags to run the original
tests from the extracted root. Use the virtual environment's interpreter for
`python -B -m pytest -q -p no:cacheprovider tests`. The release's
`VALIDATION.json` records the installed wheels, original tests and extracted
API checks for each Windows and Ubuntu profile.
