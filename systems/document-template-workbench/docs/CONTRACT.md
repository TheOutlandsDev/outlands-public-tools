# Template and document contracts

Requests use exact object fields. JSON duplicate keys, nonfinite numbers, invalid
UTF-8 and excessive nesting are refused. IDs are 32 lowercase hexadecimal digits;
pins are 64. CLI request files must be explicitly selected below `inbox/` using the
portable ASCII path subset, at most eight components/240 characters. Parent segments,
empty components, stream syntax, backslashes, trailing spaces/dots and Windows
device names fail. Included files are regular single-link files with guarded parents.

A template has exactly `format`, `label`, `title`, `fields`, `sections`. Format is
`outlands-document-template-v1`. Field/section identifiers begin with an ASCII letter,
then letters/digits/underscores, at most 32 characters. Each set is unique ignoring
case; lookup is exact and case sensitive. Field schemas are:

- Scalar: `name`, `label`, `kind` (`text` or `quantity`).
- Rows: `name`, `label`, `kind: rows`, `columns`; each column has `name`, `label`,
  `kind` (`text` or `quantity`). Every row and scalar value is required exactly.

Text must be valid UTF-8 and XML-compatible. Controls below space are refused except
tab, CR/LF; surrogate values and XML noncharacters U+FFFE/U+FFFF fail. Quantities are
exact nonnegative integers through 999999999; Boolean, decimal and string quantities
are not coerced. Unicode normalization, locale conversion and value defaults are
not supplied. Row text is bounded independently of longer scalar body values.

A section has `id`, `title`, `optional`, `blocks`. The optional flag is an exact
Boolean. Explicit selection must include every required section, contain no unknown
or duplicate IDs and select at least one section. Output follows template order.
All declared values are validated even when their section is omitted.

Paragraph/bullet blocks have `kind`, `text`. Only exact `{{scalar_name}}` markers
are substituted; names must refer to declared scalar fields. Unmatched marker
delimiters, attribute/index expressions and row-field substitution fail. Replacement
text is never parsed recursively or executed. Expanded CRLF/CR normalizes to LF.

A table block has `kind: table`, row-field `source`, `columns`, `totals`. Each selected
column has `field`, integer `width` between 1 and 100; widths must total 100 and names
must be unique. Totals name selected quantity columns only. Row order is preserved;
empty tables have a header and zero totals. Total quantities are integer sums.

Preview format `outlands-document-preview-v1` records expanded title/sections,
literal blocks, table rows/totals, included/omitted IDs, template/value pins and
summary. `paragraphs` counts paragraph/bullet template blocks, not every Word XML
paragraph in headings/cells/totals. Canonical JSON bytes are pinned independently
of artifact folder/ID. Repeated equal models can produce byte-identical DOCX files.

Each build request identifies a registered preview and exact pin with four exact
true quality/privacy/rights/context assertions. It creates a new directory and DOCX,
retains the preview, verifies every expected XML part and writes the final receipt.
No existing file is replaced. A completed typed journal event is also required.

The DOCX uses exactly `[Content_Types].xml`, `_rels/.rels`, `docProps/core.xml`,
`docProps/app.xml`, `word/document.xml`, `word/styles.xml`, `word/settings.xml` and
`word/_rels/document.xml.rels`. Members use fixed dates/regular attributes, no ZIP
comments/extras/encryption and stored compression. Root relationships target only
the main document and fixed properties. Document relationships target styles and
settings. No source pathname, workstation author or input title is put into core
properties. Body values remain private. Inspection compares complete expected part
bytes; it is not a general validator for received Office files.

Journal events are started/completed/failed/interrupted attempts. Replay validates
sequence, parent and payload hashes, types, requests, parent references, pins,
composition counts and results without filesystem operations. Ordinary updates and
deletes are blocked by SQLite triggers; schema and chain checks add integrity
verification. One pending job blocks another. A terminal slot is reserved when
starting. Hashes do not authenticate a history rewritten consistently by an attacker.
