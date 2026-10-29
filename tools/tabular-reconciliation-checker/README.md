# Tabular Reconciliation Checker

Compare declared typed record sets, identity groups and exact numeric totals. Fresh generic code and invented examples; no private application or business rules are copied.

## Fictional walkthrough

```text
python -B reconcile.py --before examples/before.json --after examples/after.json --contract examples/contract.json
```

Returns exit 1/DIFFERENCES: one changed, one missing and one added record. Both
sides total 19 units, with delta 0. Equal totals do not hide row differences.
Use --show-values only when a private report should include complete before/after
record values. Default changes include identity fields, changed field names and
hashes, without complete payloads. Identical sets return MATCH/exit 0.

Library: `reconcile.compare(before_bytes, after_bytes, contract_bytes, show_values=False)`.
It operates only on supplied buffers. No source adapter, SQL connection, business
formula, currency conversion, tolerance or inferred unit conversion is included.

## Typed contracts and complete accounting

[contract.json](examples/contract.json) declares exact fields, each with name,
type and explicit nullable boolean; one to four nonnullable text/integer identity
fields; and optional nonnullable integer/decimal total fields. Record inputs have
exact schema `{format: outlands-record-set-v1, records: [...]}`. Every record must
contain all declared fields, including explicit null for nullable values; extra
fields and implicit conversions are refused. [Before](examples/before.json) and
[after](examples/after.json) contain invented records.

Types: text (1–256 characters, no controls), strict integer excluding boolean,
strict boolean, valid YYYY-MM-DD date string and bounded decimal string with up
to six fractional places. Quantities have absolute bound one trillion. Decimal
arithmetic is exact; insignificant trailing zeros and negative zero normalize.
JSON float literals, nonfinite values and duplicate keys are invalid. Identity
comparison is exact and case-sensitive; whitespace is not trimmed. Meaning,
source completeness, units and contract suitability remain caller assertions.

Identical normalized duplicate identities count once with duplicate-row accounting.
A conflicting group withholds every valid member. Invalid rows have fixed-code
position diagnostics without rejected values. Each side conserves input_rows =
accepted_records + duplicate_rows + rejected_rows + conflict_rows. Any rejection
or conflict globally withholds changes and totals (both null), returning review
required. Qualified empty sets are allowed with numeric totals of zero.

Qualified comparison reports ONLY_IN_BEFORE, ONLY_IN_AFTER or CHANGED and an
unchanged count. Totals sum unique qualified records; delta is after minus before.
At most 1,000 records per side, 32 fields, 4 MiB per input, JSON depth 32/100,000
nodes and 8 MiB output. A matching result establishes only these supplied-set
relationships, not real-world inventory, accounting accuracy or anonymization.

## Runtime, privacy and file handling

Python 3.12/3.13, standard-library runtime, MIT TheOutlandsDev. No installation,
Office process, network connection, database or service is used. Each directory
is independently runnable with its included source files. Input files are selected
explicitly; no drive discovery or implicit mapping occurs.

Run commands from this tool directory. Generated DOCX and reports must use fresh
external paths under an existing trusted private parent. Replace placeholders
with fully spelled external absolute paths, or run from a private directory using
absolute script paths. Literal parent traversal is refused. Default reports are
ASCII-escaped JSON on stdout. --out NEW_PRIVATE_REPORT.json exclusively creates a
new external file; it never replaces an existing destination. Failed writes can
leave retained unconfirmed output. See [I/O boundaries](IO-SAFETY.md).

Inputs, selected body values, mapping/identity fields, report hashes and provenance
may contain private information. These programs do not anonymize or establish
sharing rights for real documents. Generated reports stay private. There are no
original documents, templates, customer records, identities, private configurations,
paths, credentials or third-party assets in these source examples.

Exit 0 PASS/MATCH; 1 DIFFERENCES or review required; 2 invalid input/refused I/O;
130 handled interruption. Diagnostics use fixed codes without supplied argument
values or native paths. Source/property omission is not a confidentiality proof.
See [origins](ORIGINS.md) and [fictional validation](VALIDATION.md).
