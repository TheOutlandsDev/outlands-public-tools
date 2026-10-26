# Windows Event Timeline Inspector

Build a chronological report from explicitly supplied saved Windows event
metadata. Group repeated provider/channel/event-ID/version declarations, observe
timestamp gaps and review repeated/conflicting exported record IDs without
querying the current PC's logs or interpreting private event payloads.

## Quick start

From this module folder in PowerShell:

```powershell
$base = Join-Path ([System.IO.Path]::GetTempPath()) 'outlands-events-demo'
New-Item -ItemType Directory -Path $base
python -B examples/generate.py --output "$base/fixtures"
python -B event_timeline.py --file "$base/fixtures/clean.json" --format json --output "$base/report-clean"
python -B event_timeline.py --file "$base/fixtures/review.json" --format json --output "$base/report-review"
python -B event_timeline.py --file "$base/fixtures/clean.xml" --format xml --output "$base/report-xml"
```

Clean JSON/XML exit 0 with three events in two groups. The repeated group is an
observation, not automatically an error. Review exits 1 with a duplicate record,
a threshold-exceeding declared time gap and a record lacking an explicit timezone.
Set `--gap-seconds 0` to disable gap findings; the default is 300 seconds. Repeat
`--file` to combine selected files of the same explicitly chosen format.

## Supported inputs and interpretation

Use the documented normalized JSON export schema or the supported UTF-8 Event /
Events XML subset. Native `.evtx` and `.evt` binaries are not supported. The
original bounded XML reader has no native XML-parser dependency and never loads
resources. Namespace support is deliberately limited to the documented default
Windows event namespace or unnamespaced examples, not arbitrary prefixes.

Timestamps require a known explicit offset or Z and retain up to seven fractional
digits (100 ns). Naive times, unknown -00:00 offsets, invalid dates and unsupported
precision require review. Relative intervals and record IDs are decimal strings
in output JSON so consumers do not lose integer precision. Equal timestamps
retain input order, without implying causal order.

Default reports show relative intervals, event IDs, levels and opaque group IDs.
`--include-details` adds canonical UTC timestamps, provider names/GUIDs, channels
and record IDs. Computer names are used only internally to scope record-ID
comparisons and are omitted even with details. Raw messages, event payloads,
security/user data and input filenames are never included in reports.

Duplicate record-ID checks require declared computer, channel and record ID,
and apply only within an individual selected file. Cross-file identity, host
authenticity and event completeness are not inferred. Counts include accepted
duplicates; nothing is silently deduplicated. A time gap or repeated event is
not proof of a failure or its cause. See [exporting and schema](docs/EXPORTING.md)
for a private manual export workflow and the [precise format](docs/FORMAT.md).

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
