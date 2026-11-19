# Use the Offline Observation Window Selector

## Verify and extract

Download the source ZIP and `SHA256SUMS.txt` from the
[GitHub release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/observation-window-selector-v0.1.0).
Compare the ZIP digest with its entry in `SHA256SUMS.txt` before extracting
into a fresh directory.

PowerShell

```powershell
Get-FileHash .\observation-window-selector-0.1.0.zip -Algorithm SHA256
Expand-Archive .\observation-window-selector-0.1.0.zip .\observation-demo
Set-Location .\observation-demo\observation-window-selector-0.1.0
```

Ubuntu shell

```sh
sha256sum observation-window-selector-0.1.0.zip
unzip observation-window-selector-0.1.0.zip -d observation-demo
cd observation-demo/observation-window-selector-0.1.0
```

## Select a day from fictional observations

Run with Python 3.12 or 3.15. Use `python3` if that is the name of your
interpreter.

```text
python -I -B observation_window.py --input examples/observations.json --start 2042-12-01T00:00:00 --end 2043-01-01T00:00:00
```

The newest observation is `2042-12-31T23:59:59.997` and appears twice.
The CLI counts all three rows and prints this result.

```json
{
  "count": 3,
  "window": {
    "start": "2042-12-31T00:00:00",
    "end": "2043-01-01T00:00:00"
  }
}
```

Try the same bounds with `examples/empty.json` to get `count: 0` and
`window: null`. Both inputs exit with status 0. `examples/invalid.json`
contains a timestamp equal to the upper bound. It exits with status 2 and
a diagnostic on stderr.

## Supply your own saved rows

Use a regular UTF-8 JSON file of up to 16 KiB with no byte-order mark.
It accepts up to 100 rows. Each row is an array containing exactly one
timestamp string. Order rows newest-first and retain duplicates.

Use `YYYY-MM-DDTHH:MM:SS` with an optional one to three fractional digits.
Timestamps and bounds are timezone-naive. Use the same calendar and clock
convention for every value. The start bound is inclusive, the end bound is
exclusive, and the start must precede the end.

The selected window always covers the complete calendar day of the newest
observation. Its midnights can extend beyond a partial-day input range. If
the following midnight is outside Python's representable date range, the
CLI exits with status 2. The report contains a count and the selected
midnights. The input file is read-only and the report goes to stdout.

## Verify the extracted source

```text
python -I -B source_check.py
python -B -m unittest discover -s tests -v
```

The release validation record gives the results for fresh source ZIP
extractions on Windows and Ubuntu with both pinned Python versions.
