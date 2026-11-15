# Document Content Diff

Compare supported stored DOCX paragraph/table blocks by document position. Reports distinguish added, removed, changed and kind-changed block representations, with one-based changed-cell coordinates for paired tables. They do not render documents, compare formatting/properties, infer semantic moves or establish Word compatibility. The five runtime/generator files use Python's standard library.

From this directory, generate invented inputs at new absolute external paths, then compare them:

```text
python -E -s -B fictional_docx.py --variant before --out NEW_EXTERNAL_BEFORE.docx
python -E -s -B fictional_docx.py --variant after --out NEW_EXTERNAL_AFTER.docx
python -E -s -B document_diff.py --before NEW_EXTERNAL_BEFORE.docx --after NEW_EXTERNAL_AFTER.docx
python -E -s -B document_diff.py --before NEW_EXTERNAL_BEFORE.docx --after NEW_EXTERNAL_AFTER.docx --show-values --out NEW_EXTERNAL_REPORT.json
```

Use fresh names under an existing trusted private parent outside the source directory. The `after` variant produces paragraph/table differences. The `formatting` variant instead produces `MATCH` with `raw_bytes_changed` true. The `needs-review` variant is ordinary invented stored text; its name does not invoke business validation. [USAGE](USAGE.md) provides an executable fictional guide with complete independently authored expected reports and a file manifest. [METHODOLOGY](docs/METHODOLOGY.md) explains the evidence boundaries.

Both selected inputs must pass the complete bounded DOCX subset before a comparison result is returned. Blocks pair only by their position. Insertions and reorders can shift later comparisons; derived paragraph/table IDs and positions are part of the stored block representation. An earlier kind change can renumber a later block and produce `CHANGED` even when its text or cells remain equal. A paired table can therefore have an empty `cell_changes` list. These are structural observations, not stable business identities, fuzzy matching or move detection.

Paired tables compare one-based row/column positions. A missing cell is null and has a null hash; a present empty cell is the empty string and has its own string hash. Added/removed blocks and kind changes are reported at block level rather than inventing paired-cell semantics. Explicit values are plain stored strings/row matrices in JSON, never executed markup.

Default reports expose raw/content fingerprints, block IDs/kinds, structure, table dimensions and changed-cell coordinates/hashes. They omit full block/cell values. `--show-values` adds values only to reported changes, not an unconditional dump of all unchanged content. Counts, shapes, coordinates and hashes remain identifying; neither mode anonymizes data. Property/style bytes are never exported or interpreted. Formatting, properties or ZIP transport can change raw source bytes while stored content still matches.

At most 512 changed blocks and 4,096 changed cells **per paired table** are allowed. Exceeding either limit refuses the complete comparison with no successful/truncated report. Two paired tables can each have 4,096 changes: the cell limit is not a global 4,096-cell budget. Input, XML, content and output bounds still apply independently.

The supported subset is bounded Transitional WordprocessingML paragraphs and rectangular plain-text tables. Spaces, tabs and line breaks are preserved; multiple paragraphs within a cell join with LF. DTDs, processing instructions, XML comments, external relationships, macros, direct hidden-run markers, tracked changes, fields, hyperlinks, nested/merged cells and unsupported structures are refused. All main-body content is checked on each side. Known formatting/property parts may be bounded opaque bytes; their contents are not evaluated or used to resolve resources. Visibility through styles, numbering, pagination, visible layout and general Word compatibility remain unverified. Ordinary DOCX outside the subset may be refused.

Limits are 4 MiB per DOCX input, 64 ZIP entries, 2 MiB per expanded part, 8 MiB total expanded bytes and a 200:1 expansion ratio; XML depth 32, 50,000 nodes and 2,097,152 aggregate XML text/attribute characters; 2,000 top-level paragraphs, 32 tables, 1,001 rows per table, 32 columns, 20,000 total cells, 4,096 characters per paragraph/joined cell and 1,048,576 total extracted stored-block characters (including cell-joining LF). Encoded JSON output is limited to 8 MiB. Byte budgets and Python string-character budgets are separate; these are cooperative application controls, not an OS sandbox or hard deadline.

The application reads/decompresses DOCX members in memory and never unpacks input archives onto the filesystem. Qualification helpers separately extract the verified source ZIP. No document is executed or rendered, no external resource is followed, and no Office process or external writer is exercised. Raw/content hashes establish byte/representation agreement, not document authenticity, visible meaning or production acceptance.

Both file roles require trusted, quiescent ordinary single-link inputs. New reports are exclusively created outside the source directory; existing or partial outputs are retained and cannot be silently reused. Sampled metadata/hashes are not atomic snapshots, hostile-filesystem containment or full metadata preservation. POSIX requests mode 0600; Windows inherits parent ACLs without a confidentiality guarantee. Shell redirection does not inherit `--out` protections.

Version 0.1.0's [qualification recipe](docs/QUALIFICATION.md) selects Windows/Ubuntu with pinned CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2. Its source ZIP selects 30 files plus the manifest, without Python binaries, DOCX inputs, generated reports or private evidence. All 55 original test bodies, four runtime/generator files and historical [I/O](IO-SAFETY.md), [origins](ORIGINS.md) and [validation](VALIDATION.md) records remain unchanged. The sole runtime correction ports the published Windows `exclusive_write` fix, with existing-leaf refusal before exclusive create-new/reparse-point output handling. That declared exception supersedes historical backend-byte-identity wording without rewriting the historical records.

Exit 0 means `MATCH`; exit 1 means `DIFFERENCES`; exit 2 means invalid input/refused I/O; handled interruption returns 130. Fixed diagnostics omit supplied argument values and native paths. `document_diff.compare(before_bytes, after_bytes, show_values=False)` operates on supplied buffers; native CLI file protections do not automatically cover a caller's own input acquisition.
