# Document Intake Checker

Validate an explicitly selected DOCX table using caller-defined public typed mapping rules. Fresh generic code and invented examples; no private application or business rules are copied.

## Fictional walkthrough and mapping

```text
python -B fictional_docx.py --out NEW_PRIVATE_INPUT.docx
python -B document_intake.py --input NEW_PRIVATE_INPUT.docx --table table-1 --mapping examples/mapping.json
```

The example returns PASS: three input rows, two accepted records and one identical
duplicate, retaining source table rows 2 and 4 for the repeated identity. The
header is selected table row 1. `--variant needs-review` on the generator creates
a table with two conflicting rows and one invalid quantity: no accepted record
and exit 1. Unknown table IDs and missing mapped headers fail; no header search,
column alias inference or implicit business policy is supplied.

[mapping.json](examples/mapping.json) uses the existing public
`outlands-table-map-v1` contract. Source/target fields are unique, each field declares
text/integer/decimal/boolean/date and a required boolean, and one to four required
fields define identity. Unknown columns require explicit reject/ignore policy.
Canonical integer text has absolute bound one trillion; decimal text has at most
six fractional places and the same bound; booleans are exact true/false; dates
are valid YYYY-MM-DD. Optional blank values become null. No trimming or default
coercion occurs. Mapped text is bounded to 256 characters with controls refused.

The public intake core is retained byte-for-byte. It receives a bounded in-memory
CSV representation of the selected stored table, not an intermediate file. Row
invariant: input_rows = accepted_records + duplicate_rows + rejected_rows +
conflict_rows. Conflicting valid identity groups withhold every member. Invalid
row diagnostics omit rejected payloads; accepted values/provenance stay private.
Multiline cells are faithfully extracted but their control characters can be
rejected by the mapping rules. At most 1,000 data rows and 32 mapped fields.

Any issue or empty accepted set withholds ready_for_explicit_review. A PASS is
not an approval or import. Downstream adapters must enforce that whole-batch gate;
selecting accepted rows from a failed batch is not approved by this checker.
Raw DOCX, extracted-content, mapping and normalized-table hashes are distinct
pins. Property changes affect raw source hashes even when stored content agrees.

Library: `document_intake.preview(docx_bytes, mapping_bytes, 'table-1')`.
The tool never modifies the input or imports records into a store.

## DOCX subset and limits

Only a bounded Transitional WordprocessingML plain-text/rectangular-table subset
is supported. Runs preserve stored text, spaces, tabs and line breaks. Multiple
paragraphs in a cell join with LF. Table IDs follow document table order; positions
and row/cell coordinates are one-based. They are not stable business identities.

DTDs, processing instructions and comments in parsed XML are refused, including
UTF-16 declarations. Macros, external relationships, images/objects, hyperlinks,
fields, tracked changes, content controls, nested tables, merged/omitted cells,
nonrectangular tables, direct hidden-run markers and unsupported parts/features
are refused. All main-body content is checked, including unselected tables.
Known document-property/style/settings/font/theme/numbering parts may be present
as bounded opaque bytes, with checked internal relationship targets; their content
is not exported, evaluated, rendered or used to resolve other resources.

This extracts stored text, not Word's visible layout. Styles and numbering are
not interpreted: visibility, automatic labels, pagination and rendered meaning
are unverified. Hidden text through styles cannot be inferred. Formatting and
property changes can leave content hashes equal while raw hashes differ.
This is not full OOXML conformance validation or general Word compatibility.
Public format background: [Microsoft WordprocessingML tables](https://learn.microsoft.com/en-us/office/open-xml/word/working-with-wordprocessingml-tables).

Limits: 4 MiB input; 64 ZIP entries; 2 MiB per expanded part, 8 MiB total and
200:1 maximum expansion ratio. ZIP entries/relationships are allowlisted; no
archive is extracted. Parsed XML has depth 32, 50,000 nodes and 2 MiB aggregate
text/attribute characters. At most 2,000 top-level paragraphs, 32 tables, 1,001
rows per table, 32 columns, 20,000 total cells, 4,096 characters per paragraph/cell
and 1 MiB total extracted text. Output is limited to 8 MiB with refusal rather
than truncation. These bounds are not an operating-system resource sandbox.

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
