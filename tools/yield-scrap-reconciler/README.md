# OUTLANDS | Yield & Scrap Reconciler

Reconcile selected per-specimen dispositions and exact cohort fractions without quality targets or production claims. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and fictional HVAC inspection records.

Run from this complete tool directory:

```text
python -B yields.py --input examples/input.json
python -B yields.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out needs an
absolute destination for a fresh report outside the source tree under an existing
trusted parent. No private application, real equipment or operational records needed.

## Contract and interpretation

Library `yields.check(raw_json_bytes)`. Input exactly `{format,cohort,dispositions}`,
format `outlands-yield-scrap-v1`. Cohort rows are `{id}` and must be nonempty.
Disposition is exactly `{id,specimen_id,disposition}`, where disposition is one of
first_pass_good, reworked_good, scrap or pending. Every selected specimen requires
exactly one selected disposition. Missing records are never implicitly pending.

Exact repeated snapshots under one ID count once. Distinct disposition IDs for one
specimen are ambiguous, even with equal outcomes; these records are selected states,
not a history. Orphans, conflicts, rejected rows or missing dispositions withhold
all summary counts and fractions. Actual rework events belong in the separate
history checker. A reworked_good specimen contributes exactly one good unit.

Counts satisfy cohort = first_pass_good + reworked_good + scrap + pending and
good = first_pass_good + reworked_good. Every fraction uses the entire selected
cohort denominator, including pending: first_pass_yield=first_pass_good/cohort,
eventual_yield=good/cohort, scrap_fraction=scrap/cohort, pending_fraction=pending/cohort.
Each report retains original numerator/denominator and a reduced exact_fraction
string such as 1/2, 0/1 or 1/1. No rounded percentages or floating-point division.

Pending states return REVIEW_REQUIRED but retain all provisional counts/fractions;
closed_cohort is false. For a closed structurally consistent cohort, PASS only means
reconciliation, even if every unit is scrap. No quality/yield target is supplied or
judged. The four-unit HVAC example has two first-pass good, one reworked good and one
scrap: first-pass 2/4 (1/2), eventual 3/4 and scrap 1/4. No actual population completeness,
inspection coverage, manufacturing output or equipment approval is established.

## Shared accounting, CLI and privacy limits

All IDs and unit labels match `[a-z][a-z0-9_-]{0,47}`. Each list has at most 1,000
rows. Exact normalized identity snapshots count once plus duplicate_rows; conflicting
groups withhold every member, including repeated identical members within the group.
Every list satisfies
`input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows`.
Cross-reference findings do not reclassify structurally accepted rows. Diagnostics
use fixed codes and 1-based logical positions; row 0 denotes a cohort/pair issue.
Rejected values are omitted. No latest status, revision or event is inferred.

One explicit JSON input <=4 MiB. Duplicate keys, unknown fields, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers
outside +/-10^18 are refused. Integer fields reject booleans and numeric strings.
Decimal values are supported only in the stated string schema. Output is escaped
ASCII JSON <=8 MiB. Invalid outer contracts or list/product bounds refuse entirely;
valid scoped findings retain or withhold results as specified above. Raw input
SHA-256 covers exact supplied bytes. Pins establish consistency, not authenticity.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted quiescent parents; no hostile-process filesystem sandbox or OS
quota. Default output is private stdout JSON. Optional --out takes an absolute new
report destination under an existing external parent outside the source tree.
No overwrite, parent traversal or mkdir. Failed writes may retain partial/unconfirmed
output; inspect privately and use a fresh path. Windows inherits parent ACLs without
a confidentiality guarantee. Shell redirection lacks --out protections. Exit 0 PASS,
1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption; errors omit supplied paths/values.

No network, database, device, live clock, command execution, include/URI following,
environment expansion, directory discovery or automatic target action. Reports can
contain private IDs, readings, limits, counts and outcomes. The tools are not
anonymizers, publication-rights checks or independent truth/authority verifiers.
Keep actual inputs/reports private. Invented HVAC demo-units are not engineering
specifications or maintenance instructions. See [origins](ORIGINS.md) and
[validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
