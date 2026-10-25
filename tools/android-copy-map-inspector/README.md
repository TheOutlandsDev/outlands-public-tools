# Android Build Copy-Map Inspector

Review declared Android `PRODUCT_COPY_FILES +=` source/destination words without
running Make or copying payloads. It finds repeated declarations, conflicting
destinations, case/Unicode portability collisions and file-versus-parent paths.
Useful when reviewing a proposed product file list before a separate build review.

## Quick start and examples

From this module folder, using PowerShell:

```powershell
$base = Join-Path ([System.IO.Path]::GetTempPath()) 'outlands-android-copy-map-inspector-demo'
New-Item -ItemType Directory -Path $base
python -B examples/generate.py --output "$base/demo-inputs"
python -B copy_map_inspector.py --file "$base/demo-inputs/clean.mk" --output "$base/report-clean"
python -B copy_map_inspector.py --file "$base/demo-inputs/review.mk" --output "$base/report-review"
python -B copy_map_inspector.py --file "$base/demo-inputs/roots.mk" --roots "$base/demo-inputs/roots.json" --output "$base/report-roots"
```

Clean has two distinct destinations: exit 0. Review declares collisions, an unsafe
relative path, an unknown variable and an uninspected include: exit 1. Roots has a
single mapping, resolved through your explicitly supplied substitution JSON: exit
0. No default partition roots are guessed. Repeat `--file` for selected Make text.
Add `--include-details` only to a private run to expose declared and resolved
source/destination/owner values. On Linux run `base="$(mktemp -d)"` and use the same Python commands with
`$base`, omitting the PowerShell setup lines.

## Supported scope

Only literal append statements and single terminal-backslash line joining are
supported. Copy words are `source:destination[:owner]`. Both paths must be safe
relative text; they are never accessed. Simple leading `$(UPPERCASE_NAME)` roots
can be replaced only through supplied JSON. General Make expressions, other
assignments, includes and conditionals are not evaluated and require review.
Declarations under conditions may still be listed as candidates, with incomplete
coverage; collisions are declared candidates, not a claim about evaluated build
output. Actual assignment order, source existence, owner semantics, payload
licensing, AOSP validation rules and successful build are outside scope.

## Requirements and installation

Use an updated CPython 3.12 or newer on Windows or Linux. This tool uses only the
Python standard library: no pip packages, admin rights, device connection or game
installation are needed. Download the repository ZIP or clone it, then open a
terminal in this module folder. Keep this folder intact when copying it alone;
`text_support.py`, examples, tests and the source inventory are included.

Commands below use Python 3 as `python`; use `python3` if that is its name on your
system. In PowerShell, `(Get-Location).Path` gives the current absolute folder.
In a POSIX shell, `$PWD` does the same. Replace example absolute paths with your
chosen directories. The parent folder must already exist, and the output folder
must be new for every run. Quote paths containing spaces.

## Reports and interpretation

Each completed inspection creates `report.json`, a static escaped `report.html`
and `MANIFEST.json` containing SHA-256 hashes and byte lengths for both reports.
Open the HTML locally in a browser; it has no scripts, external links/resources
or embedded configuration execution. JSON is the machine-readable record.
The stdout summary contains counts and fixed status/error codes.

| Exit | Meaning |
| --- | --- |
| 0 | `NO_SCOPE_FINDINGS`: no findings within the supported selected text subset. |
| 1 | `REVIEW_REQUIRED`: supported differences/findings or incomplete coverage. Read both lists. |
| 2 | `INCOMPLETE`: invalid arguments, refused input, bounds or I/O failure. No complete result. |

An empty input can produce exit 0. Exit 0 does not establish completeness of a
device configuration, correct firmware, successful boot/build or redistribution
rights. Coverage issues are never counted as a clean result. A write failure may
leave a new partial output folder; do not use it as a completed report. Choose a
different fresh output folder after fixing the cause.

## Privacy and limits

Default reports omit local input filenames and raw declared names/paths/values.
They retain opaque input/record IDs, line numbers, hashes, counts and finding
codes. This is data minimization, not anonymization: hashes and structure may
still identify a configuration. `--include-details` deliberately adds selected
declared fields; review that report privately before sharing. Never submit real
credentials, device identifiers, private paths, firmware or customer configs.
Even fictional text containing HTML is escaped in the report.

Inputs must be explicitly selected absolute paths to stable regular local files.
Links/reparse points, UNC/device paths, Windows alternate streams, duplicate
input files, non-UTF-8, NUL and other control characters are refused. UTF-8 BOM,
LF and CRLF are supported. Maximums: 1 MiB per input, 4 MiB total selected text,
32 input files, 20,000 physical lines including the final empty line, 8,192
characters per physical/logical line, 4,000 rows per bounded collection and
8 MiB per serialized report. At a limit the run fails, rather than truncating a
result. The optional copy-map roots JSON has its own smaller limits.

Source files are opened for reading only. Output is exclusive to a new folder;
existing files are never intentionally replaced. Checks reject ordinary linked
and changing inputs, but this is not an OS sandbox against a hostile concurrent
filesystem mutator. Use trusted local files and an output parent you control.
There is no recursive scan, subprocess, shell, network access or privileged
operation in the inspector. The examples launch only this Python program in tests.

## Development, tests and suggestions

From this module directory:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

Tests create disposable fictional files, run the actual CLI and check parser
semantics, bounded input, source immutability, report escaping and manifests.
Windows/Ubuntu CI runs Python 3.12/3.13/3.14 as listed in
[validation](docs/VALIDATION.md); platform-specific filesystem tests may skip
when their mechanism is unavailable. No real firmware/device testing is claimed.
To contribute a source change, inspect the diff and deliberately update the
inventory with `python -B source_check.py --write-manifest`, then rerun both
checks. The unsigned manifest detects accidental drift; it is not authentication.

Bug reports, feature requests, format examples and usability suggestions are
welcome through the [public issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Choose this tool's bug or suggestion form. Include OS, Python version, source
commit, expected behavior and a minimal fictional example. Read
[CONTRIBUTING.md](CONTRIBUTING.md), [format details](docs/FORMAT.md),
[provenance](docs/PROVENANCE.md) and [security guidance](SECURITY.md).

MIT covers this original source, authored tests/docs and generated fictional
examples. Inspected inputs retain their own licenses and ownership.
