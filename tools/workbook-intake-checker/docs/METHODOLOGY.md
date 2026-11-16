# Methodology and interpretation

## Three separate contracts

The caller chooses source bytes, CSV/XLSX format and, for XLSX, one exact visible
sheet name. The caller supplies an exact field map. The tool checks that declared
syntax/type/grouping contract and creates a private preview. It neither infers
business policy nor checks that the source is complete, authoritative or current.

Source headers and mapped text are literal: no trimming, alias discovery, Unicode
normalization or case folding. Lowercase target identifiers use the declared
grammar. Required fields and identity are explicit. Optional empty text becomes
null, which differs from numeric zero or false. Integer/decimal grammars refuse
exponents even when an XLSX numeric cell permits the stored exponent spelling.
XLSX `d` cells only bound the literal; a mapped `date` then validates its calendar.

## Accounting and provenance

Only successfully converted rows enter identity groups. Equal normalized records
within a group count once and export every contributing row position. Different
normalized records with the same identity withhold all valid group members;
invalid rows remain separately rejected. A duplicate count is not a proof that
two real-world entities are the same. Signed decimal zero is retained as `"-0"`,
so a record containing it can conflict with the same identity containing `"0"`.

CSV positions count logical records from one header row; quoted physical newlines
do not add records. XLSX positions follow contiguous worksheet rows. The exported
`source_rows` positions refer to the selected supplied table, not another system's
record identifier or an external lineage trail. All rows obey the displayed
accounting invariant. Header-only tables require review. Unrelated accepted
records stay visible after a rejected/conflicting row, while the whole-batch
readiness flag is false. A PASS is never approval or import permission.

## Workbook coverage and privacy

Every bound worksheet is checked before the exact requested sheet is returned.
A supported selected sheet cannot mask an unsupported unselected sheet. Formula
caches do not authorize formula cells. The parser reads allowed ZIP parts in
memory and applies explicit structural/relationship checks; it does not unpack an
input archive, execute a macro or resolve an external target. Known property/style
parts can remain bounded opaque bytes, so their acceptance is not complete OOXML,
style or property validation. Their bytes still affect the raw source fingerprint.

Plain inline/shared strings in the fictional cases have the same expected typed
records, but distinct archive/source hashes. These cases and the one fictional
generator are not evidence of independent writer interchange or general Excel
compatibility. There is no rendering, display-format/date-serial interpretation,
formula evaluation, automatic sheet search or visual-layout verification.

The preview intentionally exports accepted values, map fields, selected sheet,
counts, row positions and source/map hashes by default. Rejected supplied values
are excluded from row issues; fixed codes and positions are not anonymization.
Exact fingerprints may disclose equality with another known input. Keep reports,
fixtures, mapping, ledger and manifests private.

## Bounds, arithmetic and files

Byte budgets bound source/map reads and ZIP compressed/expanded parts. Python
`len` budgets count raw-cell/mapped-text characters and aggregate parsed XML text
plus attribute names/values. The mapped-text predicate refuses ASCII C0 and DEL;
it does not reject every Unicode control or invisible character. Date validation
and explicit types do not establish quantity units, timezone or business meaning.

Decimal absolute-value checks and normalization inherit the ambient Decimal
context. The qualified fresh CLI uses the C binding and unchanged default context
at precision 28, adequate for the at-most-19-significant-digit input spelling.
Changing a library caller's context is outside the observed contract. Component
measurements identify the selected complete Python archive, not reproducible or
separately certified Expat/zlib/Decimal builds.

Both source and mapping paths are guarded independently. A successful read's
cooperative stability checks do not create one atomic snapshot across both files.
Use trusted, quiescent files and parent directories. Fresh report creation refuses
existing leaves; a write failure can leave an unconfirmed prefix. Preserve it and
choose a new output name rather than retrying over it. The qualified Windows
exclusive-create port is the only runtime change. No hostile-directory race proof,
full ACL/metadata preservation, transaction rollback or crash/power-loss guarantee
follows. Parser limits are not an OS resource sandbox.

## Evidence separation

Original regression methods, copied-runtime CLI cases and the independent
executable guide are separate evidence. The guide's expected records/counts/issues
and report bytes are authored explicitly rather than obtained from `preview`,
`_convert`, worksheet parsing or original test helpers. It verifies every retained
fixture, report, prior file, manifest row and partial-write artifact. Actual
script entry points run under bounded child processes with extraction/remote/
process actions refused and C XML/Decimal affinity/context checked before/finally.
The controlled write fault calls the owned copied backend separately.

The matrix validates only the named platform/interpreter builds and fictional
contracts. It establishes no real workbook acceptance, downstream import, database
write, Office interoperability, business approval or production readiness. Consult
the actual validation records for selected/passed/skipped methods and scope.
