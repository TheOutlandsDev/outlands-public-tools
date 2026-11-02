# Filter & Sort Projection Checker

Check claimed ordered row IDs against exact view and embedded record-snapshot pins.

Independent MIT source; Python 3.12/3.13 standard library.

```text
python -B projections.py --input examples/input.json
python -B projections.py --input examples/needs-review.json
```

Library: `projections.check(raw_json_bytes)`. Optional `--out` selects a NEW
absolute private report outside source beneath an existing trusted parent.

Input exactly `{format,views,snapshots,projections}`, format `outlands-table-view-projections-v1`.


## Exact typed declarations

Every key below is required. Unknown keys/defaults and unsupported scalar types are
refused. IDs match `[a-z][a-z0-9_-]{0,47}`. Revisions are exact integers 1..1,000,000;
booleans never count as integers. The views/snapshots/plans/cases cohorts each permit
1..32 raw records. Projections permits 1..128; pages permits 0..512. Identical normalized
top-level identities collapse with duplicate accounting. Conflicting identities exclude
every member and withhold all assessment. Nested record IDs must always be unique.

Column exactly `{id,type,nullable}`. type is string, integer or boolean; nullable is an
exact bool. Column lists have 1..32 unique IDs, normalized lexically. Strings have 0..256
Unicode code points; integers are exact within +/-10^12. Floats/decimals, coercion, trimming,
case folding and Unicode normalization are unsupported. A null value is allowed only
under an explicitly nullable column. Schema column ordering is not a display layout.

View exactly `{id,revision,columns,predicates,sort,id_order}`. Predicates has 0..16 exact
`{id,field,op,value}` records with unique IDs and known column references, normalized by
predicate ID. All predicates combine with AND; an empty list accepts every typed row.
op is eq, ne, lt, le, gt, ge, is_null or is_not_null. Ordinary comparisons require a
NONNULL operand of the exact declared column type. Boolean predicates support eq/ne
and null tests only. is_null/is_not_null require null as their operand, even for a
nonnullable column. Null actual values match neither ordinary eq nor ne nor ordered
comparisons; explicit null predicates are required. No expressions, regexes or SQL.

sort is an ORDERED list of 0..8 exact `{field,direction,nulls}` rules. Fields are known
and unique; direction is asc/desc; nulls is first/last. Rule order controls sort priority
and is preserved in pins. Null placement is independent of direction: descending never
silently reverses null placement. Nonnull integers use exact numeric ordering, strings
use case-sensitive Unicode code-point order (not locale or numeric-string order), and
booleans sort false before true in ascending order. id_order is required asc/desc and
provides the final total-order tie-breaker on each unique row ID. Empty sort uses only
this explicit row-ID order. No implicit reliance on the input list's order.

Snapshot exactly `{id,revision,columns,rows}`. rows has 0..512 exact `{id,values}` records
with unique IDs, normalized by ID. values is an exact map containing EVERY declared
column, including explicit null entries where allowed. Extra/missing keys or wrong
types reject the snapshot. Snapshot columns must exactly match a selected view's
normalized columns. A view cannot silently reinterpret one snapshot under new types.

## Projection claims

Projection exactly
`{id,revision,view,view_revision,view_sha256,snapshot,snapshot_revision,snapshot_sha256,row_ids}`.
References pin whole normalized selected objects, including unused snapshot rows and
view rules. Unknown/stale references and column-contract mismatches withhold all
assessment. row_ids is an ORDERED list of 0..512 symbolic IDs. Duplicates and unexpected
IDs are representable logical findings, not silently removed. The checker recomputes
the filter and total ordering, then reports expected_row_ids, missing_count,
unexpected_count, duplicate_count, order_matches and valid. Missing/unexpected counts
are distinct-ID counts; duplicate_count counts excess occurrences. Unexpected means
outside the expected projection, including a real snapshot row excluded by filtering.
order_matches and valid both require the complete claimed list to equal the expected
ordered list, so equal membership alone never passes. Unknown claimed IDs are omitted
from diagnostics. A valid empty projection is possible under a pinned empty snapshot
or a filter selecting no rows; required definition/claim cohorts remain nonempty.

## Pagination claims and coverage

Plan exactly `{id,revision,projection,projection_revision,projection_sha256,page_size}`.
page_size is exact integer 1..128. The reference pins the COMPLETE normalized projection
claim, including its ordered IDs and underlying view/snapshot references. A page exactly
`{id,revision,plan,plan_revision,plan_sha256,index,row_ids}` pins the whole plan. index
is exact integer 0..511; row_ids has 0..128 entries and preserves order, including any
duplicates for visible accounting. Missing/stale/unknown bindings withhold all assessment.
The tool independently recomputes projection validity before using it as page evidence.

Expected pages are contiguous zero-based windows of page_size, with a possibly shorter
final window. An empty projection requires ONE explicit empty page at index zero.
Changing size, projection order or snapshot references invalidates old page pins.
Pages are grouped by exact plan and index. Distinct page IDs claiming the same slot are
ambiguous, even if payloads match; no first/latest record wins. Identical repeated
top-level page identities normalize once with accounting, as ordinary duplicate evidence.

Plan assessment reports complete, valid, expected_page_count, missing_indices,
unexpected_indices, duplicate_indices, per-slot pages and global coverage. complete
means every expected slot has exactly one observation and there are no extra slots;
valid additionally requires every exact page window and global ordered coverage to
match. Missing/extra/ambiguous slots retain unique known-slot checks but withhold global
coverage (null). Cross-page duplicates, missing rows and unexpected IDs remain findings.
Per-slot checks prevent arbitrary shifts across page boundaries even when flattening
all pages reproduces the correct row order. An invalid projection withholds page
conclusions entirely: complete/valid are false and page counts/windows/coverage are null.
Logical findings retain assessment and normalized cohort pins but require review.

## Same-snapshot scenario comparison

Scenario input uses shared snapshots and one shared nonempty case cohort, alongside
baseline_views and candidate_views. Case exactly
`{id,revision,baseline_view,baseline_view_revision,baseline_view_sha256,candidate_view,candidate_view_revision,candidate_view_sha256,snapshot,snapshot_revision,snapshot_sha256,page_size}`.
Each case binds one actual embedded snapshot, both whole view versions and a shared
page_size 1..128. This prevents silently dropping/replacing observations between sides.
Both view schemas must exactly match the snapshot. Malformed types cannot become equal
negative outcomes; structural errors withhold the whole assessment. Same view ID/revision
with different normalized definitions is an identity conflict; declare a new revision.

The comparator recomputes both ordered projections and derives both sets of page windows.
It reports exact baseline/candidate row IDs, page windows, equal and an aggregate
all_selected_outcomes_equal. Equal membership with different order is a change. Changes
to unobserved rules can leave selected outcomes equal; that proves only these cases,
not whole-view compatibility, database equivalence, actual UI or pagination behavior.
Empty snapshots may match with one empty window each; the case cohort itself is nonempty.

## Pins, privacy, errors and evidence limits

Pins hash normalized sorted-key compact ASCII JSON plus one LF. Identity cohorts,
columns, predicates and snapshot rows normalize by ID. Sort priority, projection IDs
and page row order remain semantic. Raw input_sha256 hashes exact input bytes instead.
Reports have PASS/REVIEW_REQUIRED, fixed-code issues and complete top-level row accounting.
Structural errors withhold assessment/cohort pins. Logical mismatch retains those but
withholds qualified_scope_sha256. Qualified scope hashes the map of normalized cohort
pins; it is not an authenticated approval or proof of real data freshness/completeness.

No raw column values or predicate operands enter report diagnostics. Known column IDs,
row IDs, counts and expected windows are necessary output and can still be private.
Keep actual inputs/reports private; hashes do not anonymize. Data/record revisions are
caller declarations, not live observations or security/identity guarantees.

CLI exit 0 means PASS, 1 REVIEW_REQUIRED and 2 a fixed-code refusal. Input <=4 MiB,
output <=8 MiB, JSON depth <=32 and <=100,000 nodes. These global caps can constrain
combinations below individual cohort limits. Duplicate JSON keys, floats/nonfinite
constants and invalid Unicode refuse. Native I/O requires trusted local paths, a regular
single-link input and a fresh private output outside source; linked/ambiguous paths and
overwrites refuse. See [I/O safety](IO-SAFETY.md). The byte-pinned helper includes unused
XML functions; these tools accept JSON only. Controls are not a hostile-machine sandbox.

Every complete directory runs independently with Python 3.12/3.13 standard library.
No SQL/database execution, browser/DOM/HTML inspection, scripts, network, live clocks,
model calls, real page loads or data/view updates occur. Actual UI rendering, concurrent
database paging, operational data truth, access control, security, privacy and rights
are not established. Original private implementations and instances remain untouched.
