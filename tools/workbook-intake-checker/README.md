# Workbook & CSV Intake Checker

Preview explicitly selected CSV or a deliberately limited `.xlsx` subset using a
caller-authored field map. Python 3.12/3.13; standard-library runtime; MIT,
copyright TheOutlandsDev. No Excel installation is needed for parsing.

This is fresh generic code with invented records and a fictional workbook
generator. No private application, workbook, business formula, column mapping,
customer record or operating policy is selected. It imports nothing into a store.

Run from this tool directory:

```text
python -B intake.py --input examples/records.csv --mapping examples/mapping.json --format csv
python -B intake.py --input examples/needs-review.csv --mapping examples/mapping.json --format csv
```

The first returns exit 0: three input rows, two accepted records and one duplicate.
The second returns exit 1: two conflicting rows and one rejected row, with no
accepted records. Row diagnostics contain fixed codes and logical record positions,
excluding rejected values. Accepted records and their provenance remain private.

For a generated fictional XLSX, select a fresh file outside the checkout:

```text
python -B fictional_workbook.py --out NEW_PRIVATE_WORKBOOK.xlsx
python -B intake.py --input NEW_PRIVATE_WORKBOOK.xlsx --mapping examples/mapping.json --format xlsx --sheet Records
```

`NEW_PRIVATE_WORKBOOK.xlsx` is a placeholder: provide an external absolute path
or run from a private working directory with an absolute script path. Input
examples may be read from the source tree; output inside the checkout is refused.
No generated XLSX or binary asset is bundled. The generator uses fixed fictional
ZIP dates and does not inspect user or machine metadata.

Library entry point: `intake.preview(source_bytes, mapping_bytes, 'csv')` or
`intake.preview(workbook_bytes, mapping_bytes, 'xlsx', 'Records')`. Keep the tool
directory on the trusted import path. No sibling tool installation is required.

## Mapping and accounting

The exact `outlands-table-map-v1` schema is demonstrated in
[mapping.json](examples/mapping.json). Every field declares a source header,
target identifier, type and required boolean. Headers and text match exactly:
no trimming, inferred aliases, business rules, default values or schema discovery.
Targets and source headers must be unique. One to four required target fields
define record identity. Unknown columns require an explicit `ignore` policy and
are counted, or the complete input is refused.

Types: `text`, `integer`, `decimal`, `boolean`, `date`. Text is at most 256
characters, with control characters refused. Integers use canonical base-10 text
and absolute values at most one trillion. Decimal text permits at most six
fractional places and absolute values at most one trillion; normalized output is
a decimal string. Exponent notation is refused by those numeric mappings.
Booleans are exactly `true`/`false`; dates are real `YYYY-MM-DD` calendar dates.
Blank optional values become null; blank required values are rejected. Boolean,
date and quantity meaning always comes from the supplied mapping.

Identical normalized records with the same identity produce one accepted record
and retain all source-row positions. A conflicting identity withholds **every**
valid row in that identity group. Invalid rows are counted separately. The
invariant is `input_rows = accepted_records + duplicate_rows + rejected_rows +
conflict_rows`. CSV positions count logical records, including blank rows, rather
than physical lines within quoted fields. Header-only tables require review.
Any rejected/conflicting row withholds `ready_for_explicit_review` for the batch.
A PASS is a validation result, never automatic approval or an import action.

## Supported workbook subset

Transitional SpreadsheetML `.xlsx`, one explicitly named visible sheet, contiguous
rows starting at row 1, and ascending unique cell coordinates through column AF.
Plain inline strings, plain shared strings, numeric literals, booleans and ISO
date cells are recognized. Sparse trailing/middle cells become blank values.
Numeric cells remain their literal stored text: styles do not convert Excel date
serials, percentages, rounding or displayed number formats into semantic values.
Rich strings, formula/cached-formula cells, error cells, merged cells, hidden
sheets/rows/columns and unsupported worksheet features fail closed. Every workbook
sheet is structurally inspected; an unsupported unselected sheet also refuses
the workbook. There is no formula evaluation, macro execution or Office process.

ZIP names and relationships are allowlisted. Duplicate entries, traversal,
encrypted/unsupported compression, macros, external links, arbitrary parts and
ambiguous references fail. No ZIP is extracted. Ordinary document property and
style parts may be present but are not returned or interpreted; their bytes
still affect the raw workbook digest. This is a subset parser, not a complete
OOXML validator or a general Excel compatibility claim. Public format background:
[Microsoft cell representation](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.cell)
and [shared strings](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-the-shared-string-table).

Limits: 4 MiB input, 1,000 data rows, 32 columns/fields, 20,000 worksheet cells,
4,096 characters per raw cell, 16 sheets, 64 ZIP entries, 2 MiB per expanded
part, 8 MiB total expansion and a 200:1 maximum expansion ratio. XML depth is 32
with 50,000 elements and 2 MiB aggregate text/attribute characters per part.
DTDs, entities through DTDs, processing instructions and comments are refused,
including UTF-16 declarations. These bounds do not provide an OS resource sandbox.

## Output and validation

Default output is private ASCII-escaped JSON on stdout, containing accepted values,
declared mapping, row provenance, counts and exact source/mapping SHA-256 pins.
Nothing anonymizes a real input. `--out NEW_PRIVATE_REPORT.json` creates only a
fresh external report and prints a count-free status; it never replaces a file.
See [filesystem limits](IO-SAFETY.md), [provenance](ORIGINS.md) and
[validation](VALIDATION.md). Exit 0 PASS; 1 review required; 2 invalid input or
refused I/O; 130 handled interruption. Argument/native errors omit supplied values.
