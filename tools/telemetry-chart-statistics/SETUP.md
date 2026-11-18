# Summarize a synthetic telemetry series

Download the source ZIP and `SHA256SUMS.txt` from the release page. Verify the
ZIP before extracting it.

On Windows, run this command in PowerShell and compare the result with
the ZIP digest in `SHA256SUMS.txt`.

```powershell
Get-FileHash -Algorithm SHA256 .\telemetry-chart-statistics-0.1.0.zip
```

On Ubuntu, run this command from the download directory.

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Open a terminal at the extracted root and use CPython 3.12 or 3.15 for the
`python` command. Save the following as `summarize_samples.py` in that directory.

```python
from sentinel_monitor.charting import nice_axis_max, percentile, series_stats
from sentinel_monitor.formatting import format_bytes, format_duration

samples = [None, 0.0, 10.0, 20.0, 30.0, 40.0, float("nan"), float("inf")]
summary = series_stats(samples)
if summary is not None:
    print(
        f"min {summary.minimum:g}, mean {summary.average:g}, "
        f"p95 {summary.p95:g}, max {summary.maximum:g}"
    )
print(f"median {percentile(samples, 0.5):g}, axis ceiling {nice_axis_max(samples):g}")
print(format_bytes(1536), format_bytes(1024 * 1024, per_second=True))
print(format_duration(90061))
```

Run `python summarize_samples.py`. The example uses synthetic samples and
requires only the standard library.

```text
min 0, mean 20, p95 38, max 40
median 20, axis ceiling 50
1.5 KB 1.0 MB/s
1d 1h 1m
```

Chart helpers skip `None`, NaN, and infinity. `series_stats` and `percentile`
return `None` when there are no finite samples. Pass `percentile` a fraction
from 0 to 1. Axis ceilings use a 1, 2, 5, or 10 multiple of a power of ten,
with a default minimum of 1 and 8% headroom. Byte formatting divides by 1024
at each step and retains the original labels such as KB and MB. Add
`per_second=True` for a rate. Duration formatting reports whole minutes with
hours and, when present, days.

To run all five original tests, create a virtual environment and install
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
original tests, and checks from fresh ZIP extractions.
