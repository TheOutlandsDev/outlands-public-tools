# Offline Source Inventory Diff review — 2026-10-25

This batch adds [Offline Source Inventory Diff](../tools/source-inventory-diff/README.md),
a fresh comparison utility over the published Source Inventory CSV/summary
format. Python 3.12+ and the standard library are sufficient; the single script
has no sibling-module dependency. The private audit's source-version/duplicate
review area supplied the candidate boundary. No held source archive, original
private inventory, filename/hash mapping, configuration, credential, operational
record or game asset was selected, read, copied or executed. Existing source and
rights holds remain. Parser/escaping/input-guard patterns adapt public MIT code.

## Input and trust boundary

Only `files.csv` and `summary.json` are read from each explicitly selected run.
The tool does not enumerate source roots or report directories, read tree files,
reopen inventoried bodies, generate commands, move/delete files, verify renames
or choose a canonical copy. It prints JSON and creates no report files itself.

The supported summary schema, coverage and path encoding are exact. CSV snapshot
hashes, selected/hashed counts, byte totals, top-level counts, configured limits,
basic UTC timestamps, skip counts and exclusion metadata are checked. Unknown
top-level fields, duplicate JSON keys/decoded paths, unsupported row statuses,
wrong columns, malformed text and inconsistent totals fail. The optional tree
object is bounded but uninterpreted; tree text/metadata is not compared or certified.

The original reversible spreadsheet escape is checked canonically. Exactly one
leading apostrophe is removed only for a true flag. Quoted/control/Unicode names,
formula-like strings and embedded backslashes remain literal data. Supported
relative path text is never joined to a source root or used as a command. Output
uses ASCII JSON escapes; no spreadsheet CSV output is produced.

Summary hashes provide internal consistency, not authenticity: an editor can
rewrite CSV and summary together. No original body hash is recomputed, trust
anchor consulted, root equivalence established, or ownership/license/source
safety verified. Real filenames, hashes, times, sizes and relationships remain
private; metadata-only output is not anonymization or publication clearance.

## Comparison and uncertainty

Matching uses exact decoded names without case folding or Unicode normalization.
Digest case and equivalent aware UTC timestamp spellings are normalized. Rows
are sorted by folded/exact names, and classified as only in before, only in after,
hash/size changed, timestamp-only changed or unchanged. Omitted records do not
establish additions, deletion or absence in an underlying source tree.

Effective directory exclusions, suffix exclusions and configured limits are
compared separately from record changes. Any declared skipped entry requires
review, even when counts match. Matching coverage declarations do not establish
matching actual scopes. Run labels/capture times and optional tree metadata do
not affect record classes; exact input report hashes are retained separately.

Distinct exact names sharing a Python case-fold key remain separate and raise
an ambiguity review signal. Reported hash/size pairs are grouped for review when
duplicates occur or path sets differ across reports. Many-to-many cases remain
one group, without quadratic rename-pair expansion. A digest associated with
multiple sizes raises a separate conflict and is not treated as one size group.
No hint proves a rename, an authentic original, a disposable copy or a canonical
source. Even unchanged records with duplicate hints require review.

Review issues take precedence over `DIFFERENCES_REPORTED`; otherwise matching
selected records without issues give `MATCHING_SELECTED_RECORDS`. Exit 0 is the
last case, exit 1 differences/review, exit 2 error and exit 130 interruption.
Every source-scan/body-access/mutation/deletion/rename/canonical-selection/
authenticity/scope/network verification flag remains false.

## Fictional validation

The local Windows/Python 3.12.7 utility suite discovered 45 methods: 43 passed and
two unavailable native-link operations were skipped. Skips are not passes. A
compatibility case generated a new report from disposable fictional source text
using the published inventory generator. The diff itself opened control reports
only; no real inventoried source body or private record was used.

Two hundred seeded report pairs were checked against separate list-search and
grouping reference logic. Other checks cover malformed schemas/hashes/CSV/JSON,
canonical escaping, literal/control/Unicode names, time normalization, coverage
and skip uncertainty, ambiguity/conflicts, reverse/permutation behavior, sampled
identity changes, no-side-effect behavior and pre-print output bounds. A maximum
10,000-row duplicate case remained one group instead of generating pairs.

A separate standalone CLI walkthrough passed 33 fresh-process scenarios with
newly authored reports. It covered matching/different/uncertain cases, shipped
examples, malformed metadata, unsupported inputs, arguments and help/version.
Input/script bytes remained unchanged; no bytecode appeared. The collection
regression discovered 518 methods: 493 passed and 25 skipped, no failures/errors.
Ruff checks/formatting and 275 local Markdown/JSON checks passed. Dedicated CI
targets Windows/Ubuntu with Python 3.12/3.13; consult exact-commit Actions results
for executed native operations. Synthetic metadata and native observations are
distinct evidence.

## Bounds, publication and remaining limits

Each CSV is bounded at 16 MiB and each summary at 1 MiB. Each run permits 10,000
rows, relative names up to 4,096 characters, declared 64 MiB/file and 256 MiB
total selected bytes. JSON nesting/value-node limits are 16/50,000. Serialized
stdout JSON is bounded at 32 MiB before printing, plus its final newline. A bound
failure emits a fixed error rather than partial comparison JSON; OS output
failure/interruption can still leave partial captured output.

Sampled ordinary-file, single-link, ancestor and descriptor/path identity checks
apply to control files. All four snapshots are rechecked after comparison. Use
stable trusted local inputs: sequential reads are not an atomic four-file
transaction or hostile-filesystem sandbox. Mount aliases, blocked OS I/O and
network-backed storage remain outside the guarantee. Fixed CLI errors omit
supplied/native values; formatted library exceptions can retain Python source
locations. Future real reports require their own private handling and review.

The exact selected publication set receives a separate pattern/private-marker
review and byte inventory. Private markers, runtime walkthrough reports, scanner
output, source mappings, publication receipts and audit ledger remain outside
the repository. CSV/summary fixture bytes are preserved by local attributes so
recorded hashes survive checkout. This batch does not clear unrelated imports,
Git history, held source/rights families or existing v0.1.0 release assets.
Selected original code/docs/tests and invented fixtures use MIT under
TheOutlandsDev; no third-party implementation or runtime is bundled.

The 19-file export retains one conservative rooted-Windows-path finding in a
fictional report-path rejection test. It is literal metadata, never a filesystem
target or actual private path. Its private disposition is bound to the exact
file hash. Scanner status remains `REVIEW_REQUIRED`; unresolved findings,
private-marker matches and scanner errors are zero, with no detector disabled.
