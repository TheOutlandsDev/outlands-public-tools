# Kernel Module List & Dependency Inspector

Review explicitly supplied module dependency and load-list text. It reports
duplicate/ambiguous declarations, unresolved metadata references and cycle
witnesses, then gives a dependency-first order for the supported selected closure.
Useful for reviewing staged metadata without loading or executing module binaries.

## Quick start

From this module folder, in PowerShell:

```powershell
$base = Join-Path ([System.IO.Path]::GetTempPath()) 'outlands-modules-demo'
New-Item -ItemType Directory -Path $base
python -B examples/generate.py --output "$base/fixtures"
python -B module_inspector.py --deps "$base/fixtures/clean.dep" --load-list "$base/fixtures/clean.load" --available "$base/fixtures/available.txt" --output "$base/report-clean"
python -B module_inspector.py --deps "$base/fixtures/review.dep" --load-list "$base/fixtures/review.load" --output "$base/report-review"
```

Clean exits 0: one selected feature has a three-module dependency closure. Its
prerequisites need not be repeated in the load list. Review exits 1: a declared
cycle, an unresolved dependency, repeated selection and an unknown selected name.
Add `--include-details` only to expose declared module names/paths privately.

## Scope and interpretation

The input grammar is a literal human-readable `module.ko: dependency.ko ...`
subset plus one load selection per line. Optional `--available` is a supplied
text inventory of relative module paths, not a directory or observed filesystem
scan. Absence there means only not listed in that inventory. No module binary,
kernel, device or real system inventory is accessed.

Exact dependency paths are required. Load selections resolve by exact declared
path first, then an unambiguous literal basename or suffix-stripped basename.
Duplicate declarations remain ambiguous. Builtin modules, modprobe aliases,
dash/underscore equivalence, soft dependencies, kernel symbols, vermagic,
signatures, ABI, actual load behavior and recovery availability are not inferred.

The text `modules.dep` representation is not a stable kmod API; this inspector
uses a documented limited snapshot grammar and does not replace native kmod
inspection. Unsupported syntax is coverage, not guessed compatibility.

## Install and run

Use an updated CPython 3.12 or newer on Windows or Linux. These are standalone
Python standard-library tools; no pip dependencies, admin rights or device
connection are required. VINTF uses a deliberately restricted XML reader documented in its own guide. Download the repository ZIP or clone it, then open a terminal
in this module folder. Keep the entire folder intact when downloading it alone.

Examples use `python`; use `python3` if that is the Python 3 command on your host.
PowerShell setup below creates an external temporary workspace. If that workspace
already exists, choose a new name. Every output directory must be fresh and its
parent must already exist. On Linux, run `base="$(mktemp -d)"` and use the same
Python commands with `$base`, omitting the two PowerShell setup lines. Always
quote paths. Keep real inputs and reports outside the source tree.

## Reports and exit codes

A completed run creates three files in the new output directory:

- `report.json`: schema-versioned observations, findings and coverage issues.
- `report.html`: escaped static JSON, without scripts or external resources.
- `MANIFEST.json`: SHA-256 hashes and byte lengths of the two reports.

Open HTML locally in a browser or consume JSON directly. Stdout contains counts
and fixed status/error codes. Reports describe selected evidence, not deployment
approval, a complete system inventory or successful boot/runtime compatibility.

| Exit | Status | Interpretation |
| --- | --- | --- |
| 0 | NO_SCOPE_FINDINGS | No supported findings in the explicitly selected scope. |
| 1 | REVIEW_REQUIRED | Findings, supported differences or incomplete coverage; read both lists. |
| 2 | INCOMPLETE | Invalid/refused input, bounds or I/O failure; no complete result. |

Existing output is refused rather than replaced. A write failure may leave a new
partial folder; do not use that as a completed report. Fix the cause and choose a
different fresh output. The manifest is unsigned: byte verification detects
drift but does not authenticate its author or establish input ownership.

## Privacy and file handling

Local input filenames are omitted from reports and errors. Default reports omit
raw declared names, paths and identifiers where relevant. They retain structure,
opaque IDs, offsets/positions, counts and hashes. This is not anonymization:
hashes and layouts may identify an input. Add `--include-details` only when a
private report needs the documented fields; inspect it before sharing.

Only explicitly supplied stable regular local files are opened. Absolute paths
are required. Links/reparse points, UNC/device paths, Windows alternate streams
and changing inputs are refused. Inputs are read-only; fresh report files are
the only inspector outputs. These checks do not provide an OS sandbox against a
hostile concurrent filesystem mutator. Use trusted local inputs and an output
parent you control. No recursive system scan, subprocess, shell, network,
device access, module loading, mount operation or configuration edit is performed.
Tests launch only this tool's Python code on disposable generated fixtures.

JSON and HTML reports are each capped at 8 MiB; bounded record/finding collections
at 4,000 rows. A bound fails the run rather than silently truncating a result.
See [format and limits](docs/FORMAT.md) for tool-specific input budgets.

## Tests, source verification and suggestions

From this module folder:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```

Tests create fictional temporary inputs and exercise the real CLI. Shared tests
cover file/encoding bounds, source immutability, output refusal, escaping and
manifest integrity; parser-specific fixtures cover the declared semantics.
The [validation record](docs/VALIDATION.md) distinguishes platform skips and
metadata observations from real device/runtime proof. Windows and Ubuntu CI
run these checks against the reviewed source on Python 3.12/3.13/3.14.

If changing source, review the diff before deliberately regenerating the exact
source inventory with `python -B source_check.py --write-manifest`; then run both
checks again. `inspection_support.py` and shared tests are identical first-party
MIT code copied into each module to support standalone downloads.

Bug reports, feature requests and format/usability suggestions are welcome via
the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Select this tool's bug or suggestion form and provide a minimal fictional
reproduction, expected behavior, OS/Python version and source commit. Do not
attach real images, device IDs, customer configurations or unredacted reports.
See [CONTRIBUTING.md](CONTRIBUTING.md), [provenance](docs/PROVENANCE.md) and
[security guidance](SECURITY.md). MIT covers original source, authored docs/tests
and generated fictional examples. Inspected inputs retain their own rights.
