# Ingestion Receipt Reconciler 0.1.0

Rerun bounded CSV/XLSX intake, compare a supplied typed preview, and reconcile a
receipt's raw-byte pins and count claims. This MIT CLI/library uses the standard
library only. Windows/Ubuntu qualification targets the exact CPython 3.12–3.15
builds in [PYTHON-LOCK.json](PYTHON-LOCK.json). It does not import records or verify
receipt authority, real ingestion, source authority or actual store contents.

## Four explicit selections

From the complete tool directory, in PowerShell 5.1 or a POSIX shell:

```text
python -E -s -B receipts.py --receipt examples/receipt.json --source examples/source.txt --mapping examples/mapping.json --preview examples/preview.json
```

The invented example returns PASS/exit 0 with three observed logical data rows:
two accepted records and one duplicate. No real records are used. Optional `--out`
creates a fresh external report under a trusted existing parent. The independent
CSV, inline/shared XLSX and refusal exercise is in [USAGE.md](USAGE.md).

Library entry: `receipts.reconcile(receipt_raw, source_raw, mapping_raw, preview_raw)`.
All four inputs are explicitly supplied bytes. The receipt selects `csv` or
`xlsx`; filename extensions are not guessed. Paths are never taken from receipt,
mapping, preview or source content. The unused symbolic-artifact helpers in
`run_core.py` do not impose their 16-artifact manifest contract on this CLI.

## Recomputed facts and a review gate

The exact receipt fields are `format: outlands-ingestion-receipt-v1`,
`receipt_id`, `source_sha256`, `mapping_sha256`, `preview_sha256`, `source_format`,
`sheet`, `counts`. Receipt IDs match `[a-z][a-z0-9_-]{0,47}` and hashes are 64
lowercase hexadecimal characters. CSV requires sheet null; XLSX requires a
nonempty name of at most 31 characters and exact selected-name matching.

Count fields are exactly `input_rows`, `accepted_records`, `duplicate_rows`,
`rejected_rows`, `conflict_rows`, each an actual integer 0–1,000, excluding
booleans. Their declared arithmetic and equality to observed counts are checked.
These counts refer to logical data rows after the header, not physical CSV lines.

The included public intake parser is actually rerun on the selected source and
explicit mapping. The report therefore sets `row_counts_recomputed: true` and
retains `observed_counts` and `intake_status`, including under review holds.
This is a calculation from selected bytes, not independent source authority or
store verification. It never establishes which records were actually committed.

Receipt pins are compared with the selected raw bytes. Supplied preview JSON is
compared with the recomputed complete preview as canonical typed JSON: true is
not integer 1 and false is not integer 0. Accepted values, ordered arrays,
source-row provenance, mapping fields, counts, issues and flags all participate.
Changing totals or re-pinning forged preview content cannot qualify it.

Whitespace-only JSON reserialization can match semantically when the receipt's
raw preview pin is updated. Supplied and recomputed preview hashes can then differ.
Reserializing the map also changes its raw hash inside the recomputed preview;
that preview must agree too. The receipt itself has an exact raw fingerprint.

Any pin, preview-content or count mismatch, inconsistent declared accounting, or
intake review status makes `ready_for_explicit_review` false. There is no import
permission, partial readiness or fallback to plausible totals. Invalid/conflicting
source rows and header-only inputs hold readiness even when valid accepted records
remain in the independently recomputed preview. Observed counts are not erased.
Receipt/preview syntax and source-parser refusals return exit 2 rather than a
reconciliation report. A valid JSON preview with altered/extra fields is a content
mismatch; it is not a substitute for the complete expected preview.

## Typed intake scope

The exact map has `format: outlands-table-map-v1`, `identity`, `fields`,
`unknown_columns`. One to 32 fields explicitly map source header strings to
lowercase symbolic target IDs, with `text`, `integer`, `decimal`, `boolean` or
`date` and an actual Boolean `required`. Identity selects one to four required
targets. Source/target names are unique. Unknown headers are rejected or explicitly
ignored. Headers/values are literal: there is no implicit whitespace trimming.

Valid identical normalized records sharing an identity count once plus duplicates;
their preview lists every logical source-row position. Different records with
the same identity withhold the whole group, including identical repeats. Invalid
rows are accounted separately; unrelated accepted records may remain visible in
the preview while readiness is held. Empty optional values become null, not zero.

Integer/decimal magnitudes are bounded to 10^12; decimal grammar permits at most
six fractional digits. Dates require the mapped calendar format, booleans literal
`true`/`false`. Decimal normalization uses the ambient Decimal context: qualified
CLI evidence uses a fresh default precision 28, ROUND_HALF_EVEN context and C
Decimal bindings. The bounded accepted values need at most 19 significant digits.
Library callers changing context are outside that qualified arithmetic scope.
Signed decimal zero remains `-0`, which can conflict with a `0` record.

CSV is bounded UTF-8, allowing a UTF-8 BOM. XLSX is a deliberately narrow plain-cell
subset supporting inline/shared strings and bounded literal cell forms. Every
bound sheet is checked, including unselected sheets. Formula/cache, hidden/merged
content, external relationships, macro parts and unsupported features are refused.
Styles do not convert serials or render display formats. Known opaque styles and
property parts are bounded rather than interpreted as full OOXML documents.
Ordinary workbooks may be refused; no Excel/Office interoperability, visible layout,
formula evaluation or general workbook compatibility is claimed.

## Qualification, privacy and filesystem limits

Eight archive lanes select 52 preserved originals plus exactly 30 copied CLI
methods each: 82 per lane, 656 selections. Actual pass/skip counts are measured.
Five non-generator runtime files contain 64 top-level definitions; 63 stay
unchanged. The separate fictional workbook generator's two definitions remain
unchanged. Only the Windows exclusive-create safeguard is ported. Five other
runtime/generator files, all original tests, four invented examples and three
historical records preserve their bytes. See [qualification](docs/QUALIFICATION.md),
[methodology](docs/METHODOLOGY.md) and [changes](CHANGELOG.md).

Each of four selected ordinary single-link files is bounded to 4 MiB. JSON bounds
include depth 32, 100,000 nodes, strings 4,096 characters and integers ±10^18;
duplicate keys, floats/nonfinite values and invalid Unicode are refused. CSV caps
1,001 logical rows including header, 32 cells per row and 4,096 characters per
cell. Mapped nonempty values are at most 256 characters and exclude ASCII C0+DEL,
not every Unicode control. Reports are escaped ASCII JSON bounded to 8 MiB.

XLSX limits include 64 ZIP members, 2 MiB per expanded member, 8 MiB total expanded
bytes and ratio 200:1, at most 16 sheets, 20,000 cells per parsed sheet, 32 columns
and 1,001 rows per sheet. Shared XML limits include depth 32, 50,000 nodes and
2,097,152 accumulated text/attribute characters. These are application bounds,
not OS quotas or complete OOXML validation. Document-input archives are read and
decompressed in memory, without extraction to the filesystem.

The summary exports receipt ID, raw input pins, supplied/recomputed preview hashes,
observed counts, intake status, issue codes and flags. It omits accepted body values,
mapping fields and row-level provenance as fields; coincidences with a chosen
receipt ID or fixed text remain possible. Omission/hashing is not anonymization.
Previews contain accepted values and provenance by default. Keep every operational
selection, preview, receipt, report and fingerprint private.

Use trusted quiescent inputs and fully spelled parents. Selections are sequential
bounded snapshots, not atomic capture. Native output refuses existing leaves and
source-tree destinations; failed writes can retain an unconfirmed partial file.
Preserve it and choose a fresh name. Shell redirection does not inherit native
guards. There is no hostile-writer containment, rollback, full metadata-preservation
or power-loss guarantee. Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 handled
interruption. See [IO-SAFETY.md](IO-SAFETY.md), [ORIGINS.md](ORIGINS.md),
[historical validation](VALIDATION.md), [notices](THIRD-PARTY-NOTICES.txt).
