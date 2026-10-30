# OUTLANDS | Evaluation Slice Coverage Checker

Check declared evaluation slices, duplicate memberships and explicit minimum coverage without scoring models or selecting cases. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic dataset logic and newly invented HVAC equipment/fault declarations.

Run from this complete tool directory:

```text
python -B slices.py --input examples/input.json
python -B slices.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report destination outside source under an existing trusted
parent. No original data, private application, weights, provider or accounts needed.

## Contract and interpretation

Library `slices.check(raw_json_bytes)`. Input exactly
`{format,taxonomy,cohort,slices,memberships,policy}`, format
`outlands-evaluation-slice-v1`. Cohort rows are `{id,expected_label}`, with each label
in taxonomy. Slice rows are `{id,minimum_cases}`, integer minimum 0..1,000. Both
selected lists must be nonempty. Membership rows are `{id,case,slice}` with exact
declared references. Invalid/conflicting rows or unknown references withhold coverage
and all qualified pins; no partial-cohort pin is issued.

Policy is exactly `{membership_mode,require_all_cases_assigned,minimum_covered_fraction}`.
Mode is exclusive/overlap, require_all_cases_assigned is a real boolean, and the fraction
is an exact decimal string in [0,1] with at most six fractional digits. No exponent,
plus, whitespace or leading integer zeros. Trailing fraction zeros and negative zero
normalize. Fractions avoid floating-point rounding. Equality meets a minimum.

Count unique (case,slice) pairs. Repeating an identical snapshot under one membership
ID counts once as a duplicate row. Different IDs for the same pair instead create a
MEMBERSHIP_REPEATED review finding, but never inflate coverage or per-slice counts.
Exclusive mode flags a case in multiple slices; explicit overlap mode permits this
and still counts each case only once in overall coverage. Summed slice counts may
exceed cohort size in overlap mode and do not represent independent observations.

Coverage denominator is the full selected cohort, including unassigned cases. Report
covered cases, exact fraction, unassigned cases, repeated pairs, overlapping cases and
per-slice counts/label counts (including zeros). Check every slice's minimum_cases,
the overall minimum fraction and optional all-cases-assigned requirement. Any failed
criterion returns REVIEW_REQUIRED with complete coverage retained. Explicit zero
minima may permit empty slices without implying useful evaluation coverage.

cohort_sha256 hashes sorted normalized `{id,expected_label}` rows and is compatible
with the existing Candidate Evaluation Gate Planner's explicit cohort format. Taxonomy
and normalized policy pins are also reported. Passing means only eligibility for
manual comparison review. No model scoring, significance, representativeness, label
truth, holdout independence or deployment approval is established.

## Shared declarations, CLI and privacy limits

All IDs match `[a-z][a-z0-9_-]{0,47}`. Revisions are integers 1..1,000,000 (no booleans
or coercion). Taxonomy is exactly `{id,revision,labels}`, 1..32 unique label IDs,
normalized by sorting. SHA-256 strings are exactly 64 lowercase hexadecimal characters.
Dataset snapshots, used by the partition and selection tools, are exactly
`{id,revision,content_sha256,group,partition,label}`. Partition is train/validation/test;
group is an explicit equipment/entity group ID; label must be declared in taxonomy.
Hashes and group assignments are supplied assertions; no artifact bytes are opened.

Each identity-snapshot list has at most 1,000 rows. Identical normalized snapshots
under one ID count once plus duplicate_rows. Conflicting ID groups withhold every
member, including repeated identical members within that group. Each list satisfies
`input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows`.
Semantic slot/membership findings are reported separately from structural row counts.
Diagnostics use fixed codes and 1-based logical positions; row 0 means a cohort-level
finding. Rejected input values are omitted. No latest version is selected implicitly.

Pins hash compact sorted-key escaped ASCII JSON plus LF; selected record collections
sort by ID and taxonomy/policy labels sort lexically. input_sha256 instead hashes exact
raw input bytes. Pins are consistency receipts, not signatures, proof of ownership,
approval authenticity, privacy clearance or truth. Keep actual inputs/reports private.

One explicit JSON input <=4 MiB. Duplicate keys, unknown fields, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers
outside +/-10^18 are refused. Output is escaped ASCII JSON <=8 MiB. Malformed outer
contracts, policies, taxonomy and list bounds are fixed refusals. Malformed identity
rows and reference conflicts produce REVIEW_REQUIRED with qualified results withheld.
Valid review findings retain results as described in each contract.

Public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link inputs and
trusted quiescent storage. Default output is private stdout JSON. Optional --out takes
an absolute fresh destination under an existing trusted external parent outside the
source tree; no overwrite, parent traversal or mkdir. Failed writes may retain partial
or unconfirmed output: inspect privately and select a fresh path. Windows inherits
parent ACLs without a confidentiality guarantee. Shell redirection lacks these guards.
Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption. Error messages omit
supplied paths and values. These guards do not sandbox hostile concurrent processes.

No network/provider/model calls, training, content collection, dataset export, clock,
command execution, environment expansion, URI/include following or directory discovery.
Only newly invented HVAC fixtures are included. The tools do not anonymize data or
verify real identities, approvals, labels, hashes, independence or publication rights.
See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
