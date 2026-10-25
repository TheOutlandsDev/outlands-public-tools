# Android VINTF Manifest Inspector

Index supported HAL instance declarations in selected Android VINTF XML and
optionally compare two explicitly supplied sets. It reports duplicate/conflicting
selected declarations and added, removed or changed supported instances without
merging effective device configuration or contacting any service.

## Restricted XML reader

This edition uses an original bounded reader for the documented UTF-8 XML
subset. It has no native XML-parser dependency. Supported syntax includes
balanced ASCII element/attribute names, quoted attributes, comments, XML 1.0
declarations and predefined/numeric references decoded once. DTDs, entities,
CDATA and unhandled markup are refused; namespaces require coverage review.
This deliberately limited reader is not a general-purpose XML implementation.

## Quick start

From this module folder, in PowerShell:

```powershell
$base = Join-Path ([System.IO.Path]::GetTempPath()) 'outlands-vintf-demo'
New-Item -ItemType Directory -Path $base
python -B examples/generate.py --output "$base/fixtures"
python -B vintf_inspector.py --file "$base/fixtures/clean.xml" --output "$base/report-index"
python -B vintf_inspector.py --before "$base/fixtures/clean.xml" --file "$base/fixtures/same.xml" --output "$base/report-same"
python -B vintf_inspector.py --before "$base/fixtures/clean.xml" --file "$base/fixtures/changed.xml" --output "$base/report-changed"
python -B vintf_inspector.py --file "$base/fixtures/review.xml" --output "$base/report-review"
```

Index and equivalent declaration forms exit 0. Changed and review examples exit
1. Repeat `--file` for current fragments and `--before` for prior fragments, up
to 32 explicitly selected files total. Duplicate input files are refused.
`--include-details` adds supported package/version/interface/instance and
transport fields to private reports. Raw XML, comments and input filenames
are never embedded in reports.

## Scope and interpretation

Supported meta-versions are 1.0/2.0 with device/framework types and a documented
HIDL/AIDL instance subset. AIDL requires meta-version 2.0 and one explicit integer
version in this subset. Equivalent supported interface/fqname forms compare by
declared identity. A version change is removal/addition. Transport/architecture
changes can be compared for unique matching identities. Repeated identities on
either side are held as ambiguous without arbitrary pairing.

This is not `assemble_vintf`, `checkvintf`, a full schema validator, effective
fragment/override merger or framework compatibility-matrix checker. API-level
filtering, runtime service presence, inferred AIDL defaults, native HALs and
unselected manifests are outside scope. Root metadata and non-HAL changes are
outside instance-diff scope. Overrides/modifiers, unknown syntax and uninspected
elements remain explicit coverage. No include, XInclude, URI or external resource
is opened. DTD/entity declarations are refused before parsing.

## Install and run

Use an updated CPython 3.12 or newer on Windows or Linux. These are standalone
Python standard-library tools; no pip dependencies, admin rights or device
connection are required. VINTF uses the deliberately restricted XML reader described above. Download the repository ZIP or clone it, then open a terminal
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
