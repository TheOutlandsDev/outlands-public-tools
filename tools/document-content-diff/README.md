# Document Content Diff

Compare supported stored paragraphs/tables by position with exact source and content pins. Fresh generic code and invented examples; no private application or business rules are copied.

## Fictional walkthrough

```text
python -B fictional_docx.py --out NEW_PRIVATE_BEFORE.docx
python -B fictional_docx.py --variant after --out NEW_PRIVATE_AFTER.docx
python -B document_diff.py --before NEW_PRIVATE_BEFORE.docx --after NEW_PRIVATE_AFTER.docx
```

The example returns DIFFERENCES/exit 1 for changed paragraph/table content.
Generating the second document with --variant formatting instead returns MATCH
with raw_bytes_changed true. Content comparison deliberately excludes formatting
and document properties; it is not a complete binary or visual document diff.
The raw source pins remain distinct and must be reviewed separately.

Blocks compare by position, with ADDED, REMOVED, CHANGED and KIND_CHANGED classes.
Paired tables compare cells by one-based row/column position, preserving empty
string versus missing-cell distinctions. Insertions can shift later positions;
there is no fuzzy matching, semantic move detection or stable business row identity.
Use Tabular Reconciliation Checker for explicitly keyed record comparison.

Default differences contain block/cell hashes and structural coordinates. Optional
--show-values includes private stored values as well; no markup is executed.
No document property values or style bytes are copied to either report form.
At most 512 changed blocks and 4,096 changed cells per paired table are permitted;
overflow refuses the complete comparison, without truncating into success.

Library: `document_diff.compare(before_docx_bytes, after_docx_bytes, show_values=False)`.
Both inputs must pass the supported DOCX checks before any result is returned.

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
