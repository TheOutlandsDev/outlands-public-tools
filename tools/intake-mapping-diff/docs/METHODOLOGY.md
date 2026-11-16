# Methodology and interpretation

## Separate declaration differences from acceptance

One exact outer JSON snapshot supplies two complete map declarations. Both must
pass the supported public mapping schema before a comparison result is produced. The
schema checks field shape, unique source/target labels, type labels, actual
booleans, required identity targets and explicit unknown-column policy. It does
not inspect a source table, validate an example value, establish units or choose
business policy. The included intake module is used only for this schema check.

Fields match by exact target ID. A new target is added and an absent target is
removed. A changed target never becomes a rename, even with an unchanged source
header. For matched targets, literal header/type/required comparisons generate
fixed codes in that order. Targets sort lexically before global identity,
unknown-column policy and field-order/membership codes. Global changes have null
targets. Source-header attributes are not serialized; symbolic target names
remain and can coincidentally equal an omitted source value. No general substring
redaction is claimed.

Identity is an ordered declaration of required targets; no supported type is
excluded merely because it would be unsuitable for a caller's real record identity.
No row is supplied or validated, and the tool cannot infer migration safety or
compatibility. PASS means no compared declaration differences. REVIEW_REQUIRED
with an empty issues list and retained changes is the intended valid-difference
result, not a malformed-row withholding rule. Invalid embedded maps instead
refuse the entire operation and create no new report.

## Fingerprint units and disclosure

The input pin hashes every exact outer-file byte. Mapping pins hash separately
validated objects using compact sorted-key escaped ASCII JSON plus one LF. They
do not reconstruct an unknown standalone map file. Object-key order and outer
formatting can change the raw input pin without changing canonical map pins.
Field and identity lists are ordered and remain significant. No trim, alias,
case folding or Unicode normalization is performed on literal headers/identifiers.

Symbolic targets, field counts, change lists and exact hashes can identify or
correlate a known map even though source-header strings are omitted. Errors omit
supplied values and paths but do not anonymize a real input. Keep snapshots,
reports, fixtures, manifests and ledgers private. Hash equality neither verifies
source completeness nor authenticates ownership, an import or a transaction.

The shared report scaffold includes row_counts_recomputed,
receipt_authority_verified, exactly_once_verified and target_changes_performed,
all fixed false. These are scope limits. Unused shared batch/receipt functions
and their retained regression tests do not make them this product's CLI contract.

## Independent examples and safe file limits

The guide authors expected reports, field counts, code ordering and normalized-map
hash inputs directly, without calling compare, intake.mapping or control_core.report
as an expected-results oracle. Its 23 complete reports span identical/ordered/key-
reordered/attribute-changed/added/removed declarations and supported schema edges.
Invalid map fixtures run in both before and after positions with the other side
valid, preventing an earlier refusal from masking the intended guard. No generator,
external writer, CSV/XLSX parser, Office process or Decimal conversion is exercised.

Actual script entry points run in bounded child processes with extraction, remote
and process actions refused and C XMLParser/TreeBuilder affinity checked before
and in finally afterward. Component identities belong to the selected complete
Python SDK. There is no arithmetic/context envelope or independent library-build
certificate. The controlled partial-write helper separately calls the owned copied
backend; it is not another CLI or a completed report.

Each case verifies all prior workspace entries and every authored input hash.
Complete report bytes, observation rows, file hashes and the manifest readback
must match independent expectations. The five-byte interrupted-write prefix stays
unconfirmed and cannot be reused as an output. No automatic deletion or rollback
is claimed. Existing outputs and source-tree destinations are refused; Windows
ACLs inherit from the trusted parent.

Raw JSON input is bounded in bytes; JSON/source-header text budgets use Python
character counts. The source-header filter specifically rejects ASCII C0 and DEL,
not every Unicode invisible/control character. Use trusted quiescent inputs and
parents: cooperative stability checks are not a hostile-writer containment or
atomic-snapshot proof. Parser/audit limits are application controls, not an OS
resource sandbox, full metadata-preservation guarantee or hardware durability test.
