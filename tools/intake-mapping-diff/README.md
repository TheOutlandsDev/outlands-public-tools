# Intake Mapping Diff 0.1.0

Describe revisions of the supported public intake mapping without applying them.
This is a standalone MIT CLI/library with standard-library dependencies only.
Qualification targets Windows and Ubuntu with the exact CPython 3.12–3.15 builds
in [PYTHON-LOCK.json](PYTHON-LOCK.json). No pip package, Office installation,
record set or workbook is needed.

The CLI reads one JSON file containing `before` and `after` maps. It validates
both map declarations, matches fields by exact target identifier and reports
fixed change codes. Source-header attributes are omitted. Target IDs,
counts, list order and exact fingerprints remain private information, not an
anonymized or compatibility-approved result.

## Start with fictional mappings

From the complete tool directory, in PowerShell 5.1 or a POSIX shell:

```text
python -E -s -B mapping_diff.py --input examples/input.json
python -E -s -B mapping_diff.py --input examples/needs-review.json
```

The first returns `PASS` and no changes (exit 0). The second returns
`REVIEW_REQUIRED` (exit 1) with `SOURCE_HEADER_CHANGED`, `TYPE_CHANGED` and
`REQUIRED_CHANGED` for target `units`. The complete independent fictional
walkthrough, including canonical fingerprints and native file refusals, is in
[USAGE.md](USAGE.md). Optional `--out` requires a fresh external filename under
a trusted existing parent. Nothing is applied, imported, transformed or retried.

Library entry: `mapping_diff.compare(raw_json_bytes)`. Keep this complete tool
directory on a trusted import path. The outer object has exactly `format`,
`before` and `after`, with format `outlands-intake-mapping-diff-v1`. Each embedded
map uses `outlands-table-map-v1`: exactly `format`, `identity`, `fields` and
`unknown_columns`. See [input.json](examples/input.json).

## Declaration checks and descriptive changes

Each map has 1–32 fields. Each field has exactly `source`, `target`, `type` and
`required`. Source headers are unique, nonempty strings of at most 256 characters;
ASCII C0 controls (U+0000–U+001F) and DEL (U+007F) are refused. Targets are unique
ASCII identifiers matching `[a-z][a-z0-9_-]{0,47}`. Supported type labels are
`text`, `integer`, `decimal`, `boolean` and `date`; `required` is an actual boolean.
Identity is an ordered list of 1–4 distinct required targets. Any supported type
can be declared for a required identity target; no record value is tested here.
Unknown-column policy is exactly `reject` or `ignore`.

Fields match by exact target ID. An added/removed target yields `FIELD_ADDED` or
`FIELD_REMOVED`. A changed ID yields removal/addition, never an inferred rename,
even if the source header stays the same. Matched targets compare literal source
header, type label and required flag, in that order. Field changes are ordered by
target ID, followed by identity order/membership, unknown-column policy and field
list order/membership changes, in that order. The global rows have `target: null`.

Object-key order does not affect canonical mapping hashes. Field and identity
list order remain significant. Mapping pins cover compact sorted-key ASCII JSON
plus LF, not an independently supplied standalone map file's original formatting.
`input_sha256` covers the exact outer JSON bytes, so whitespace, key order or a
UTF-8 BOM can change that input pin while canonical map pins stay equal.

Any valid descriptive difference returns `REVIEW_REQUIRED` and retains the full
change list. `issues` stays empty for these valid comparisons. Invalid before or
after maps refuse the entire operation with no new report. `PASS` only means no
compared declaration differences; it does not establish compatibility, migration
safety, rights, source completeness or production approval. No trim, case folding,
header alias, Unicode normalization or rename inference is performed.

## Product and evidence boundaries

The included unchanged `intake.py` is used only for mapping declaration validation.
This CLI does not call its record conversion or CSV/XLSX parsing functions, open
workbooks, validate rows, interpret Decimal values or evaluate an import. Those
unused functions remain preserved; their presence is not product coverage.
The shared `control_core.report` wrapper contributes fixed false receipt/accounting
flags; it does not authenticate a receipt or recompute row counts in this tool.
The original shared-control regression methods remain separate evidence.

The Windows backend ports only the documented exclusive-create safeguard. Four
other runtime files, all 54 original methods, two fictional JSON examples and
three historical records remain unchanged. The required archive matrix adds
exactly 30 copied-runtime CLI cases: 84 selections per lane, 672 across eight
Windows/Ubuntu Python lanes. Actual passes and finite skips belong to measured
validation records; skipped safeguards are not passed safeguards.

The full archive qualifier identifies selected Python XML/compression components
for shared-toolkit boundary tests and requires C XMLParser/TreeBuilder affinity.
Product inputs are JSON only. There is no workbook/XML-input support claim or
arithmetic-product/context envelope. See [qualification](docs/QUALIFICATION.md)
and [methodology](docs/METHODOLOGY.md).

## Files, limits and privacy

Read one explicit ordinary single-link JSON file, at most 4 MiB. JSON rejects
duplicate keys, floats/nonfinite numbers, invalid Unicode, strings over 4,096
characters, depth over 32, over 100,000 nodes and integers outside ±10^18. Report
encoding is escaped ASCII JSON, bounded to 8 MiB. Native reads/writes have the
cooperative limits in [IO-SAFETY.md](IO-SAFETY.md); use trusted, quiescent inputs
and parents. A successful read is not a hostile-writer or atomic-snapshot proof.

Default stdout is private. Source-header attributes and supplied paths are not
serialized, but coincidentally equal text can remain in retained IDs or JSON keys.
This is field omission, not a general substring-redaction guarantee. Symbolic
IDs, counts, changes and fingerprints can identify a known mapping.
`--out` exclusively creates a fresh report outside the source tree, with no parent
creation or overwrite. A failed write may retain unconfirmed partial bytes;
preserve them and choose another name. Shell redirection does not inherit these
guards. No transaction rollback, full metadata preservation, crash/power-loss
durability or OS resource sandbox is established.

Exit 0 `PASS`, 1 `REVIEW_REQUIRED`, 2 fixed refusal, 130 handled interruption.
See [origins](ORIGINS.md), [historical validation](VALIDATION.md),
[changes](CHANGELOG.md) and [notices](THIRD-PARTY-NOTICES.txt).
