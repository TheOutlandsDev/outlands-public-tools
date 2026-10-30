# OUTLANDS | Maintenance Due Planner

Calculate advisory due states from supplied intervals, explicit as-of ordinals and declared cumulative usage without scheduling. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and invented HVAC equipment/service examples.

Run from this complete tool directory:

```text
python -B due.py --input examples/input.json
python -B due.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out takes an
absolute fresh-report destination outside the source tree under an existing trusted
parent. No real equipment, private application, operational records or accounts needed.

## Contract and interpretation

Library `due.check(raw_json_bytes)`. Input exactly
`{format,as_of,maximum_meter_age,meters,plans}`, format `outlands-maintenance-due-v1`.
As_of and maximum_meter_age are integers 0..10^9; no live clock is read.
Snapshot is `{id,unit,usage_origin,observed_at,total_usage,source_sha256}` with
observed_at 0..10^9 and total_usage 0..10^15. Source pin is a declared lowercase
64-hex SHA-256; this tool does not read source artifacts or verify that digest.

Plan is exactly `{id,asset_id,last_service_at,time_interval,meter_id,meter_unit,
usage_origin,last_service_usage,usage_interval}`. Last_service_at is ordinal
0..10^9. Time_interval is null or positive integer <=10^9. Usage_interval is null
or positive integer <=10^12; at least one interval is required. If usage is selected,
meter_id/unit/origin must exactly match a snapshot, and last_service_usage is integer
0..10^15 in that cumulative origin. Otherwise all four meter-related fields must
be null. Time-only plans need no snapshots. No intervals are inferred or recommended.

All snapshots must be no later than as_of. Service baselines cannot be in the
future. A selected snapshot must be at/after last_service_at and its cumulative
usage cannot precede last_service_usage. Structural/conflicting/rejected rows,
missing references, unit/origin mismatch or these inconsistent baselines withhold
all plan assessments. Extra supplied snapshots are validated, not silently ignored.

Time threshold = last_service_at + time_interval; usage threshold =
last_service_usage + usage_interval. Equality means due. A snapshot is fresh when
as_of-observed_at <= maximum_meter_age. Stale usage gives due_by_usage=null, even
if its stored amount exceeds threshold. A known time or fresh usage trigger yields
due; otherwise stale required usage yields unknown; otherwise not_due. Either due
or stale uncertainty returns REVIEW_REQUIRED and retains all scoped assessments.
A known time-due result survives stale usage uncertainty. Remaining distances are
signed diagnostics; stale remaining_usage is not an estimate of current usage.

The HVAC fixture declares next time 14 and usage 15, with as_of 8 and observed
usage 12, so it is not_due. Invented interval changes exercise exact due boundaries.
Units/origins, service baselines and asset bindings are assertions, not authenticated
history or suitable maintenance policy. No calendar registration, forecasting,
automatic reschedule, work order creation, service or equipment action occurs.

## Shared accounting, CLI and privacy limits

Identifiers and unit/origin labels match `[a-z][a-z0-9_-]{0,47}`. Each list has at
most 1,000 rows. Integers reject booleans, numeric strings and floating point.
Normalized identical snapshots under one ID count once plus duplicate_rows;
conflicting identity groups withhold every member, including repeated identical
members in that group. Every list satisfies
`input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows`.
Cross-reference findings do not reclassify structurally accepted rows. Fixed codes
and 1-based logical positions identify problems; row 0 denotes a cohort finding.
Rejected values are omitted. No latest identity, status, revision or policy is chosen.

One explicit JSON input <=4 MiB. Duplicate keys, unknown fields, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 or JSON integers
outside +/-10^18 are refused. Output is escaped ASCII JSON <=8 MiB. Invalid outer
contracts or list/requirement bounds refuse entirely. Valid scoped findings retain
or withhold results as specified above. Input SHA-256 hashes exact supplied bytes;
normalized order pins cover only their explicit snapshot fields, not authenticity.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted quiescent parents; no hostile-process filesystem sandbox or OS
quota. Default output is private stdout JSON. Optional --out takes an absolute new
report destination under a trusted existing external parent outside the source tree.
No overwrite, parent traversal or mkdir. Failed writes may retain partial/unconfirmed
output; inspect privately and choose a fresh path. Windows inherits parent ACLs without
a confidentiality guarantee. Shell redirection lacks --out protections. Exit 0 PASS,
1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption; errors omit supplied paths/values.

No network, database, device, live clock, command execution, URI/include following,
environment expansion or directory discovery. Actual IDs, readings, intervals, parts,
outcomes and reports can be private; the tools are not anonymizers or publication-
rights checks. PASS does not independently verify records, suitable service policy,
operator authority, physical work or equipment safety. Fictional HVAC demo-cycles
and ordinals are teaching values, not manufacturer instructions. Keep actual inputs
and reports private. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
