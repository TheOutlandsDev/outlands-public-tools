# OUTLANDS | Process Event Duration Analyzer

Calculate complete declared run elapsed, active and hold durations without reading a live clock. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and fictional resources/events; no private implementation reused.

Run from this complete tool directory:

```text
python -B durations.py --input examples/input.json
python -B durations.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional
`--out ../fictional-new-report.json` needs a trusted existing external parent and
a destination that does not exist. No private application or real resource needed.

## Contract and interpretation

Library: `durations.analyze(raw_json_bytes)`. Exact fields:
format (`outlands-process-event-durations-v1`), runs, events. A run is exactly
`{id,start,end}` with start<end. An event is exactly `{id,run_id,at,kind}`, where
at is a bounded ordinal and kind is start/hold/resume/finish. All events must bind
to a supplied run and lie within its inclusive event boundaries [start,end].

Event input order is irrelevant: sort each run by declared at. Distinct event IDs
at the same time are ambiguous and require review, rather than guessing order.
Identical repeated event IDs count once; changed snapshots under an ID conflict.
The first event must be start exactly at run.start, the last finish exactly at
run.end. No boundaries are inferred from a current clock or another run.

Valid state transitions are pending->active on start, active->held on hold,
held->active on resume, and active/held->finished on finish. Finishing while held
is explicitly allowed; no resume is invented. Nested holds, resume while active,
repeated starts/finishes, missing boundaries and events after finish require review.
Accumulate the duration between consecutive events under the previous active/held
state. Active+hold must equal end-start. Zero-width runs and same-time events are
refused/flagged rather than silently contributing zero durations.

At least one accepted run is required. Any run/event/reference/order issue withholds
all durations and totals. The example has elapsed 10, active 7, hold 3 and one hold.
Totals sum individual run durations; overlapping runs can make summed elapsed larger
than actual wall-clock makespan, which is not calculated. No machine telemetry,
clock authority, causal analysis, live monitoring or actual work completion is proved.
No event history is modified, replayed or automatically closed.

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
