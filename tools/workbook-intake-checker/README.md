# Workbook & CSV Intake Checker 0.1.0

Preview an explicitly selected CSV or a narrow plain-cell XLSX subset using a
caller-authored field map. The standard-library runtime needs no Excel installation
or Python packages. Qualification targets Windows and Ubuntu with the exact
CPython 3.12–3.15 builds in [PYTHON-LOCK.json](PYTHON-LOCK.json).

The report is a private preview: accepted typed values, field mappings, logical
row positions, sheet selection and exact source/mapping SHA-256 fingerprints are
visible by default. It imports nothing. A `PASS` does not establish business
meaning, source completeness, approval or fitness for a production workflow.

## Start with invented records

From this tool directory, these commands work in PowerShell 5.1 and a POSIX shell:

```text
python -E -s -B intake.py --input examples/records.csv --mapping examples/mapping.json --format csv
python -E -s -B intake.py --input examples/needs-review.csv --mapping examples/mapping.json --format csv
```

The first example has three input rows, two accepted records and one duplicate
(exit 0). The second has two conflicting rows and one rejected row, with no
accepted records (exit 1). See the self-contained fictional generator → CSV/XLSX
parity → typed preview → review/refusal walkthrough in [USAGE.md](USAGE.md).
Use a private output directory outside the checkout and choose a fresh report
name. No workbook binary or real record is bundled in the source archive.

## Explicit mapping and whole-batch readiness

The exact `outlands-table-map-v1` schema appears in
[mapping.json](examples/mapping.json). Every field declares a source header,
target identifier, type and actual boolean `required`. One to four required
targets define identity. Source headers and targets must be unique. There is no
trimming, case folding, inferred alias, schema discovery, default value or unit
conversion. Unknown columns either refuse the input or require an explicit
`unknown_columns: "ignore"` policy; their count is reported.

Types are `text`, `integer`, `decimal`, `boolean` and `date`. Mapped values are at
most 256 characters and reject ASCII C0 controls (U+0000–U+001F) and DEL (U+007F).
Integers use canonical base-10 text and absolute values at most one trillion.
Decimals permit up to six fractional places and that same absolute bound, with
normalized output as a string. Exponents are refused by these numeric mappings.
Booleans are exactly `true`/`false`; mapped dates are valid `YYYY-MM-DD` calendar
dates. Empty optional values become null; empty required values are rejected.

Identical normalized records with the same identity count once and retain every
contributing `source_rows` position. A conflicting identity withholds every valid
member of that group. Invalid rows are counted separately. The accounting rule is:

```text
input_rows = accepted_records + duplicate_rows + rejected_rows + conflict_rows
```

Unrelated accepted records can remain visible in a `REVIEW_REQUIRED` report.
Any rejected/conflicting row keeps `ready_for_explicit_review` false for the
whole batch. A header-only input also requires review. CSV positions count
logical records, including blank records, rather than physical lines inside
quoted fields. Positions describe the supplied table, not an external data lineage.

Decimal `abs` and normalization use Python's active Decimal context. Qualification
covers a fresh CLI with C Decimal/Context bindings and the default precision 28,
`ROUND_HALF_EVEN` context. The bounded decimal spelling has at most 19 significant
digits, within that precision. Library callers that change the ambient context
are outside this claim. Signed decimal zero stays `"-0"`; it need not group with
`"0"` as an identical record.

## Supported workbook subset

Select one exact visible sheet name in a transitional SpreadsheetML XLSX. Every
declared sheet is structurally checked before selection returns; unsupported
content on an unselected sheet can refuse the complete workbook. Rows must be
contiguous from 1, and cell coordinates must increase uniquely through AF.
Plain inline/shared strings and stored numeric, boolean and date-cell literals
are supported. Sparse XLSX cells become blank values; a short CSV record instead
fails row-width validation. Cell type `d` alone does not validate a calendar date;
the mapping performs date validation. Numeric exponent literals can be parsed as
stored XLSX text and subsequently rejected by an integer/decimal mapping.

Formula cells are refused even with cached values. The checked subset refuses
rich strings, hidden sheets/rows/columns, merged cells and specified unsupported
features. ZIP names, content types and relationships have narrow checks: macros,
external relationship targets, arbitrary parts, duplicate members and traversal
are refused. Known property/style parts may be bounded opaque bytes and are not
interpreted or exported. This is not a complete OOXML validator, an Excel rendering
test or a promise that every unsupported attribute is detected. Styles never
convert date serials, percentages or displayed number formats into typed values.
Input ZIP parts are read/decompressed in memory; the application does not unpack
input archives into a filesystem directory.

Limits include 4 MiB per source or mapping input, 1,000 data rows, 32 columns/fields,
20,000 cells per worksheet, 4,096 characters per raw cell, 16 sheets and 64 ZIP
entries. Expanded parts are at most 2 MiB each, 8 MiB in total and at most 200 times
their compressed size. Each parsed XML part permits depth 32, 50,000 elements,
tag names up to 256 characters, 32 attributes per element and 2,097,152 aggregate
text/attribute-name/attribute-value characters. DTD declarations, processing
instructions and comments are refused. [METHODOLOGY.md](docs/METHODOLOGY.md)
distinguishes application limits from operating-system isolation.

## Files, privacy and evidence

Default stdout is ASCII-escaped JSON. `--out` writes a fresh report outside the
source tree and prints a count-free status. Existing outputs are refused. Reports
and fingerprints are private, not anonymized. Rejected values and source filenames
are omitted from diagnostics; accepted values and explicit mapping remain present.
No formula evaluation, macro execution, Excel/Office process, import,
external-resource access or real workbook use is qualified.

The Windows backend contains the documented exclusive-create safeguard port;
the other three runtime/generator files and all 47 original methods remain
unchanged. The archive qualification requires 47 originals plus 30 copied-runtime
cases on each of eight Windows/Ubuntu Python lanes: 77 selections per lane, 616
overall. Actual pass/skip counts belong to the validation record; a skipped fixture
is not a passed safeguard. See [qualification](docs/QUALIFICATION.md),
[filesystem boundaries](IO-SAFETY.md), [origins](ORIGINS.md),
[historical validation](VALIDATION.md), [changes](CHANGELOG.md) and
[notices](THIRD-PARTY-NOTICES.txt).

Exit codes: 0 `PASS`; 1 `REVIEW_REQUIRED`; 2 invalid input/refused I/O; 130 handled
interruption. A failed write may retain an unconfirmed partial file. Preserve it
for review and use a new filename; no rollback or power-loss durability is claimed.
