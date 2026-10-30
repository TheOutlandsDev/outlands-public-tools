# OUTLANDS | Inspection Coverage Checker

Account for declared specimen/check records and their separate outcomes without inspecting equipment or verifying evidence bytes. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and fictional HVAC inspection records.

Run from this complete tool directory:

```text
python -B inspections.py --input examples/input.json
python -B inspections.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out needs an
absolute destination for a fresh report outside the source tree under an existing
trusted parent. No private application, real equipment or operational records needed.

## Contract and interpretation

Library `inspections.check(raw_json_bytes)`. Input exactly
`{format,specimens,checks,records}`, format `outlands-inspection-coverage-v1`.
Specimen is `{id}`; check is `{id,rule_id,rule_revision}` with revision 1..1,000,000.
Both required cohorts must be nonempty. Expected scope is their full Cartesian
product, limited to 10,000 pairs. This narrow version does not model optional or
per-specimen check exemptions. Empty records is an explicit missing-coverage review.

Record is exactly `{id,specimen_id,check_id,rule_id,rule_revision,source_sha256,outcome}`.
All references must match the selected specimen/check and that check's exact rule
selection. Source pin is a declared lowercase 64-hex SHA-256, not a path, URI or
independently read artifact. Outcome is within_limits, outside_limits or not_evaluated.
No thresholds or measurement values are supplied here; results are not recomputed.

For valid scoped rows, coverage lists every expected pair and its selected record
ID/outcome or a missing entry. Summary counts expected/recorded/missing pairs and
each outcome. `records_complete` means every expected pair has one record, regardless
of outcome; `all_records_within_limits` also requires all outcomes within_limits.
Missing records, outside_limits and not_evaluated return REVIEW_REQUIRED while
retaining the complete coverage map. Thus complete records can still require review.

Distinct record IDs for the same pair are ambiguous even if outcomes match. Conflicts,
rejected rows, orphan references or wrong rule selections withhold the entire map
and summary. Normalized identical snapshots under one ID count once. Caller-declared
pins can be arbitrary valid digests; source_bytes_verified remains false. This checks
record coverage, not physical inspection, acceptance authority or truthful outcomes.
The HVAC example covers two invented air handlers and two demo checks each.

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
