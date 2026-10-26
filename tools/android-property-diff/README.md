# Android Property Configuration Diff

Compare supported Android `.prop` snapshots by literal key/value declaration.
Explain added, removed and changed values while keeping duplicate keys visibly
ambiguous. Useful for reviewing selected text changes without applying properties
or guessing a winning partition/import order.

## Quick start

From this module folder in PowerShell:

```powershell
$base = Join-Path ([System.IO.Path]::GetTempPath()) 'outlands-properties-demo'
New-Item -ItemType Directory -Path $base
python -B examples/generate.py --output "$base/fixtures"
python -B property_diff.py --before "$base/fixtures/before.prop" --after "$base/fixtures/same.prop" --output "$base/report-same"
python -B property_diff.py --before "$base/fixtures/before.prop" --after "$base/fixtures/changed.prop" --output "$base/report-changed"
python -B property_diff.py --before "$base/fixtures/before.prop" --after "$base/fixtures/review.prop" --output "$base/report-review"
```

Same exits 0 despite comment, whitespace and order differences. Changed exits 1
with one changed value and one added key. Review exits 1 with a duplicate key
held for review and an unfollowed import. Repeat `--before`/`--after` for selected
sets, up to 32 files total. Add `--include-details` only for private key/value
fields; default records use opaque IDs and source-line locations.

## Scope

Only literal `key=value` lines, blank lines and full-line comments are supported.
Split at the first equals sign and trim surrounding ASCII spaces/tabs. Empty
values are valid. Hashes, quotes, backslashes and dollar expressions in values
remain literal data; no shell/property expansion or line continuation occurs.
Unknown lines/keys and imports are explicit coverage issues, never followed.

Duplicate keys on either side are held even when their values are identical.
No first/last winner is selected. Unmatched keys are held when the opposite side
contains unidentified rows or imports. Unique supported matched changes remain
visible with coverage. Renames are removal/addition only when absence can be
assessed within the selected parsed scope. No effective property state, reserved
key behavior, property permissions, partition precedence or runtime compatibility
is evaluated. This is a snapshot review tool, not Android's property service.

## Installation and workspace

Use CPython 3.12 or newer on Windows or Linux. This tool uses only the Python
standard library; no pip dependencies, admin rights or device/game installation
are required. Download the repository ZIP or clone it, then open a terminal in
this module folder. Keep the whole folder intact when downloading it separately.

Examples use `python`; use `python3` if that is your Python 3 command. PowerShell
setup creates an external temporary workspace. Choose a new name if it exists.
On Linux, run `base="$(mktemp -d)"` and use the same Python commands with `$base`,
omitting the two PowerShell setup lines. Every output directory must be new and
its parent must already exist. Quote paths. Keep inputs and reports outside the
source tree so the exact source inventory remains reproducible.

## Reports and exit codes

A completed inspection creates `report.json`, escaped static `report.html` and
`MANIFEST.json` with the reports' SHA-256 hashes and byte lengths. Open HTML
locally in a browser or consume JSON directly. The HTML has no scripts, external
resources or active input content. Stdout contains counts and fixed codes.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | NO_SCOPE_FINDINGS | No findings within the supported selected scope. |
| 1 | REVIEW_REQUIRED | Findings, declared changes or incomplete coverage. Read both findings and coverage_issues. |
| 2 | INCOMPLETE | Invalid/refused input, bounds or I/O failure; no complete result. |

An empty supported input can produce exit 0. A complete report does not imply a
complete system inventory, diagnosis, effective configuration or deployment
approval. A failed write may leave a new partial folder: fix the cause and use a
different fresh output. Existing files are refused rather than replaced.
Unsigned manifests verify bytes and accidental drift, not authorship/authenticity.

## Privacy and input handling

Local input filenames are omitted from reports and errors. Default reports omit
the documented identifying fields but retain opaque IDs, counts, hashes,
positions and structural observations. This is not anonymization: hashes and
structure can identify an input. Use `--include-details` only when you need its
documented private values, and review the result before sharing.

Inputs must be explicitly selected absolute paths to stable regular local files.
Links/reparse points, UNC/device paths, Windows alternate streams, duplicate
input files and changing inputs are refused. Inputs are opened read-only; only
fresh report files are created. This is not an OS sandbox against a hostile
concurrent filesystem mutator. Use trusted files and output parents you control.
There is no system scan, log query, subprocess, network, import/include following,
ADB, mount, permission/property change or device action in the inspector. Tests
launch only the authored Python CLI on disposable generated inputs.

Limits include 32 selected files total, 1 MiB/file, 4 MiB aggregate bytes, 4,000
rows per bounded report collection and 8 MiB each for JSON/HTML. Text snapshots
support UTF-8 with optional BOM, LF/CRLF, up to 20,000 physical lines including
the final empty line and 8,192 characters/line. Controls, bare CR and NUL are
refused. Event JSON has separate documented structure limits. A bound fails the
run rather than silently truncating an inspection.

## Tests and contributions

Run from this module folder:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

Tests use generated fixtures, the actual CLI, supported/unsupported parsing,
private-field omission, stable read-only inputs, fresh output, escaping and
report hashes. Windows/Ubuntu CI runs Python 3.12/3.13/3.14 as documented in
[validation](docs/VALIDATION.md). Platform/link-creation skips are reported
separately from passes. No real logs, device or effective system state is tested.

For a source change, review the diff before deliberately updating the explicit
inventory with `python -B source_check.py --write-manifest`, then rerun both
checks. The first-party file/report helpers and shared tests are copied into
each module for standalone downloads. Diff comparison code is shared identically
between the two configuration diff folders.

Bug reports, feature requests and usability/format suggestions are welcome at the
[issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Choose this tool's bug or suggestion form. Include a minimal fictional example,
expected behavior, OS, Python version and source commit. Do not attach real
logs/configs, credentials, customer data or unredacted reports. Read
[CONTRIBUTING.md](CONTRIBUTING.md), [format](docs/FORMAT.md),
[provenance](docs/PROVENANCE.md) and [security guidance](SECURITY.md).

MIT covers this original code, authored documentation/tests and generated
fictional examples. Inspected inputs retain their own ownership and notices.
