# DOCX Table Extractor

Inspect a deliberately narrow DOCX subset and export explicitly selected stored table or paragraph text. The runtime uses Python's standard library and does not start Office. This release qualifies Python 3.12.16, 3.13.18, 3.14.10 and 3.15.2 on Windows and Ubuntu through the pinned [qualification recipe](docs/QUALIFICATION.md).

Run from this tool directory with the five runtime files kept together. Generate a fresh fictional input and request a table:

```text
python -E -s -B fictional_docx.py --variant before --out NEW_EXTERNAL_INPUT.docx
python -E -s -B docx_tables.py --input NEW_EXTERNAL_INPUT.docx
python -E -s -B docx_tables.py --input NEW_EXTERNAL_INPUT.docx --table table-1 --include-paragraphs --out NEW_EXTERNAL_REPORT.json
```

Replace placeholders with new absolute paths under an existing trusted private parent outside the source directory. [USAGE](USAGE.md) contains a self-contained, executable fictional walkthrough with independently calculated expectations and hashes. The source download contains 29 selected files plus its source manifest, with no DOCX inputs, generated reports or Python distribution.

The default report includes counts, a table index, the input SHA-256 and a stored-content SHA-256. It omits selected body values and document properties. Repeat `--table` to select tables in caller order; use `--include-paragraphs` to include all stored top-level paragraphs. IDs follow document order and positions are one-based. Duplicate or unknown selections are refused. The `needs-review` generator variant still parses successfully: its cell strings are fictional data, with no business rules inferred from their names or values.

`docx_tables.inspect(raw_bytes, tables=['table-1'], include_paragraphs=False)` provides the same selection API. `docx_core.extract(raw_bytes)` returns all supported body blocks to trusted in-memory callers. These APIs accept supplied bytes; CLI native file protections apply to file selection through the CLI.

Only bounded Transitional WordprocessingML paragraphs and rectangular plain-text tables are supported. Stored spaces, tabs and line breaks are preserved; multiple paragraphs within one cell join with LF. All main-body content is checked, including unselected tables. Macros, external relationships, unsupported parts, hyperlinks, fields, tracked changes, direct hidden-run markers, nested tables and merged cells are refused. Parsed XML refuses DTDs, processing instructions and comments.

Known property and formatting parts may be present as bounded opaque bytes with checked internal relationship targets. They are not exported, interpreted or used to resolve resources. The tool reads and decompresses selected ZIP members in memory; it never unpacks the input DOCX onto the filesystem. Qualification helpers separately unpack the verified **source** ZIP into their own workspace.

This extracts stored text. It does not calculate Word's visible layout, visibility through styles, numbering, labels, pagination or rendered meaning. Formatting, property or ZIP transport changes can retain the same stored-content hash while changing the input hash. Neither hash establishes document authenticity, safe attachments, full OOXML conformance or general Word compatibility. Ordinary DOCX files outside this narrow subset may be refused.

Limits include 4 MiB input; 64 ZIP entries; 2 MiB per expanded member, 8 MiB total and a 200:1 expansion ratio; parsed XML depth 32 and 50,000 nodes; 2 MiB aggregate XML text/attribute characters; 2,000 top-level paragraphs, 32 tables, 1,001 rows per table, 32 columns and 20,000 total cells; 4,096 characters per paragraph/cell and 1 MiB total extracted text; 8 MiB JSON output. Limits refuse rather than truncate and do not provide an operating-system resource sandbox.

Select trusted, quiescent ordinary single-link inputs. `--out` exclusively creates a new external file and does not replace an existing destination. Interrupted writes retain unconfirmed output; review it privately and choose a fresh name. Metadata checks are sampled and do not provide atomic snapshots or hostile-filesystem containment. POSIX requests mode 0600; Windows inherits parent permissions without an ACL confidentiality guarantee. Default omission and JSON escaping do not anonymize content, fingerprints or provenance.

The retained [I/O history](IO-SAFETY.md), [origins](ORIGINS.md) and [original validation](VALIDATION.md) describe the baseline. This release ports the published Windows `exclusive_write` correction: existing leaf entries are refused before exclusive native creation, preserving fixed CLI error codes and partial-output retention. Four other runtime/generator files and all 50 original tests are unchanged. The historical backend-byte-identity statement does not describe this explicit one-function correction. See [CHANGELOG](CHANGELOG.md).

Exit 0 reports accepted input; exit 2 reports invalid input or refused I/O. Fixed JSON diagnostic codes omit supplied argument values and native paths. The walkthrough does not use real documents, render or execute content, start Office, follow external resources, or establish production compatibility. Keep actual inputs, selections and report fingerprints private.
