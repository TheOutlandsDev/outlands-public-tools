# OUTLANDS | Meter Reading History Checker

Check supplied usage readings and explicit reset boundaries without collecting live readings or changing counters. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and invented HVAC equipment/service examples.

Run from this complete tool directory:

```text
python -B meters.py --input examples/input.json
python -B meters.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out takes an
absolute fresh-report destination outside the source tree under an existing trusted
parent. No real equipment, private application, operational records or accounts needed.

## Contract and interpretation

Library `meters.check(raw_json_bytes)`. Input exactly `{format,meters,events}`,
format `outlands-meter-history-v1`. At least one accepted meter is required.
Meter is `{id,unit,usage_origin,initial_at,initial_reading}`. Initial_at is an ordinal
0..10^9; initial_reading is a whole counter value 0..10^12. Unit and usage_origin
are caller-selected symbolic labels, not a physical device identity or calibration.

Event is `{id,meter_id,at,kind,reading,previous_reading}`. At is ordinal 0..10^9,
reading 0..10^12; meter_id must exist. Kind sample requires previous_reading=null.
Kind reset requires an explicit old-counter previous_reading 0..10^12 as well as
the new displayed reading. Every event must be strictly after the prior event/
initial baseline; distinct IDs at the same ordinal are ambiguous. Row order is
irrelevant; exact repeated event IDs count once. No implicit rollover or reset.

For a sample, reading must be >= prior display; add the difference to usage. For
a reset, previous_reading must be >= prior display; add that difference, then use
reading as the new baseline. The new baseline itself is never added as usage.
This accounts for usage before the declared reset even without a separate sample.
New baselines may be nonzero or higher than old values; the reset is explicit.

Snapshots report id,unit,usage_origin,observed_at,total_usage,display_reading,
reset_count,sample_count. Total usage starts at zero at the declared initial
baseline; it is not lifetime usage. Empty events is a valid baseline snapshot,
not evidence of a fresh device observation. Decreases, ties, bad references,
conflicting/rejected rows or invalid chronology withhold all snapshots.

The invented blower counter starts at 10, samples 15, resets from old value 20 to
0, then samples 2: usage=(15-10)+(20-15)+(2-0)=12 demo-cycles. Ordinals and units
have no implied calendar, time conversion or equipment operating meaning. No
device connection, reading collection, reset or independent counter proof occurs.

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
