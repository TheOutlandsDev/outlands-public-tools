# OUTLANDS | Measurement Contract Checker

Compare supplied exact decimal readings with an explicitly selected rule revision without equipment access or approval. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and fictional HVAC inspection records.

Run from this complete tool directory:

```text
python -B measurements.py --input examples/input.json
python -B measurements.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out needs an
absolute destination for a fresh report outside the source tree under an existing
trusted parent. No private application, real equipment or operational records needed.

## Contract and interpretation

Library `measurements.check(raw_json_bytes)`. Input exactly
`{format,rules,measurements}`, format `outlands-measurement-contract-v1`.
Both accepted rule and measurement cohorts must be nonempty.

Rule is exactly `{id,revision,unit,minimum,maximum,minimum_inclusive,maximum_inclusive}`.
Revision is integer 1..1,000,000; unit is a symbolic label. Bounds are finite decimal
strings with optional minus sign, canonical integer spelling and at most six
fractional digits, magnitude <=10^12. No exponent, plus sign, whitespace, leading
integer zeros, trailing decimal point, binary floats or numeric coercion. Trailing
fraction zeros and negative zero normalize (`10.000` -> `10`, `-0.0` -> `0`). Both
inclusion flags must be actual booleans. Minimum cannot exceed maximum; equal bounds
are allowed only when both inclusive. Fractions perform comparisons exactly, without
ambient Decimal-context rounding or binary floating point.

Measurement is exactly `{id,specimen_id,check_id,rule_id,rule_revision,unit,value}`.
Value follows the same decimal-string contract. Rule ID, revision and unit must
exactly match a supplied rule. One selected measurement is allowed per specimen/check
pair. Distinct IDs for the same pair are ambiguous; no latest-reading selection.
One rule ID has one selected revision; conflicting revisions are not ordered.

For valid scoped rows, report every normalized reading and within_declared_limits
with BELOW_MINIMUM/ABOVE_MAXIMUM reasons. Outside readings retain all assessments
and return REVIEW_REQUIRED. Rejected/conflicting rows, duplicate pair selections,
missing rule, revision or unit mismatch withhold the entire assessment list. The
rule-contract pin hashes sorted normalized rule objects (compact sorted-key ASCII
JSON plus LF), and is retained only when the rule cohort itself is valid/nonempty.

The invented HVAC example uses `demo-units`, a 10..20 demo flow window and a 1..3
demo fit window with an exclusive upper bound. These are arbitrary teaching values,
not airflow, pressure, electrical, dimensional or manufacturer specifications.
There is no accuracy, calibration, suitability or equipment acceptance claim.

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
