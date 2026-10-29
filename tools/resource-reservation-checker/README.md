# OUTLANDS | Resource Reservation Conflict Checker

Check declared resource reservations for availability and capacity conflicts without scheduling. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and fictional resources/events; no private implementation reused.

Run from this complete tool directory:

```text
python -B reservations.py --input examples/input.json
python -B reservations.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional
`--out ../fictional-new-report.json` needs a trusted existing external parent and
a destination that does not exist. No private application or real resource needed.

## Contract and interpretation

Library: `reservations.check(raw_json_bytes)`. Exact fields:
format (`outlands-resource-reservations-v1`), resources, reservations.
Each reservation is exactly `{id,resource_id,start,end,units}`. ID identifies one
selected snapshot. Interval is half-open [start,end); units is an integer 1..1,000,000.
The resource must exist and its normalized availability must cover the whole span.
At least one accepted resource is required; zero reservations is a valid idle scope.

Capacity uses an event sweep: add units at each start, subtract at each end, aggregate
all deltas at the same ordinal, then inspect the following positive-width span.
An end coinciding with another start therefore does not create an overlap. Multiple
reservations may overlap within capacity; a single oversized booking is also a
capacity conflict. Physical timing/capacity is not independently verified.

For valid scoped rows, report each resource's unique reservation count, peak units
and every over-capacity span with used units. Capacity findings return REVIEW_REQUIRED
while retaining the complete diagnostic summary. Conflicting/rejected rows, missing
resources or availability violations withhold the summary, rather than evaluating
an incomplete accepted subset. Identical repeated booking IDs count once and never
inflate demand. Unreferenced valid resources appear with zero peak/count.
The example's adjacent [0,6) one-unit and [6,12) two-unit bookings fit capacity 2;
moving the second start to 3 produces a three-unit conflict on [3,6).
No utilization/OEE, optimizer, automatic rescheduling, reservation lock, calendar
connection, physical resource control or execution approval is provided.

## Shared declarations and accounting

IDs, capability tags and unit labels match `[a-z][a-z0-9_-]{0,47}`. There are no
person names, machine addresses, endpoints, paths or credential fields. Interval
boundaries/event times are exact ordinals 0..1,000,000,000 with no implicit calendar,
time zone, timestamp format or elapsed-time unit. Positive-width intervals are
[start,end); terminal event instants use the explicitly documented inclusive bounds.
Booleans, numeric strings, floats and automatic coercion are refused for integers.

Resource is exactly `{id,capacity,capabilities,availability}`. Capacity is integer
1..1,000,000. Capabilities has 0..32 unique symbolic tags, normalized by sorting.
Availability has 0..32 exact `{start,end}` intervals, sorted by start/end. Overlapping
availability intervals are invalid; adjacent intervals merge into one contiguous
span. Empty availability means unavailable, never unrestricted. The resource
contract pin hashes sorted normalized resource objects using sorted-key compact
ASCII JSON plus LF; representation-equivalent adjacent spans/tags share that pin.
Input SHA-256 separately covers exact raw JSON. Pins are consistency, not authority.

Task and reservation units are positive integers <=1,000,000. Other quantities have
their explicit bounds above. Arithmetic uses exact integers, never floating point.
Each list has at most 1,000 rows. Normalized identical identity snapshots count once
plus duplicate_rows; conflicting groups withhold every member, including repeated
identical members within the group. No latest-status or latest-revision selection.
Every list satisfies input_rows = accepted_records + duplicate_rows + conflict_rows
+ rejected_rows. Bad rows retain fixed codes and 1-based logical positions; rejected
values are omitted. Row 0 denotes a cohort/conflict-span issue. Cross-reference
findings do not reclassify structurally accepted rows.

Reservation capacity conflicts, assignment ineligibility and flow arithmetic
differences intentionally retain diagnostic results for valid scoped declarations.
Structural/conflicting/reference errors withhold those results. Any invalid duration
history withholds the entire cohort's durations/totals. Invalid outer contracts,
list bounds or malformed JSON refuse entirely. PASS is not authorization, proof of
complete records, actual capacity/qualification/quantities or operational safety.

## CLI and privacy limits

One explicit JSON input <=4 MiB. Unknown fields, duplicate JSON keys, floats/nonfinite
values, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and integers outside
+/-10^18 are refused. Output is escaped ASCII JSON <=8 MiB. No directory discovery,
include/URI following, environment expansion, service/database/calendar/clock access,
network connection, process execution, optimizer or automatic target action.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted, quiescent parents; no hostile filesystem/process sandbox. Default
output is private stdout JSON. Optional --out exclusively creates a new external
report beneath an existing parent outside the source tree; no overwrite or mkdir.
Failed writes may retain partial/unconfirmed output; inspect privately and choose
a fresh path. Windows inherits parent ACLs without a confidentiality guarantee.
Shell redirection lacks --out protections. Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed
refusal, 130 interruption; supplied paths/values are omitted from errors.

Reports include IDs, interval bounds, capacities, findings and quantity/duration
totals. These can be private information. Fictional fixture selection makes this
source release generic; the tools are not anonymizers or publication-rights checks.
Keep real inputs/reports private. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
