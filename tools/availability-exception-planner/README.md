# OUTLANDS | Availability Exception Planner

Subtract explicit closure unions from pinned working windows without updating calendars. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B availability.py --input examples/input.json
python -B availability.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `availability.check(raw_json_bytes)`.

## Contract

Input exactly `{format,calendars,closures}`, format `outlands-availability-exceptions-v1`.
Calendars must be nonempty; closures may be empty. Closure exactly `{id,calendar,
calendar_revision,calendar_sha256,start,end}`. It binds the entire normalized selected
calendar. Unknown/stale references and malformed/conflicting identities withhold the
entire assessment and cohort pins. Different closure IDs may legitimately overlap.

Clip each closure against its calendar's working windows and report clipped windows
and clipped_units. A closure with no positive-width intersection requires review,
retaining diagnostics/cohort pins but no qualified_scope_sha256. A partial intersection
is permitted and visibly clipped. End-touching intervals have no positive intersection.
The total number of closure/window intersections is capped at 4,096; a larger expansion
is a fixed CLOSURE_INTERSECTION_LIMIT refusal, without partial results.

For each calendar, union all its declared closures and subtract that union from its
working windows. Report available_windows, original_units, removed_units, remaining_units
and all selected closure IDs. Overlaps remove time once; per-closure clipped_units may
sum to more than the union removed_units. Conservation is original=removed+remaining.
No closures preserves the windows; full closure yields empty availability, never
unrestricted time. No calendar reads/updates, implicit holidays or timezone conversion.
game-availability.json uses invented game-build availability metadata only.

## Shared declarations and limits

Calendar exactly `{id,revision,windows}`, with 0..32 exact `{start,end}` half-open
positive-width intervals. Sort by start/end, reject overlaps (including duplicate spans),
merge adjacent spans. Empty windows means unavailable. Each selected calendar cohort
has at most 4,096 normalized windows; larger expansion is a fixed CALENDAR_SCOPE_LIMIT
refusal, even for unreferenced calendars. Pins use normalized calendars, so equivalent
adjacent representations share a pin; the exact raw input hash remains different.

Task exactly `{id,revision,duration,release,due}`. Duration integer 1..1,000,000; release
and due are ordinals with release<=due. A too-short due window is a logical timing
finding, not an inferred duration change. Dependency exactly `{id,predecessor,
predecessor_revision,predecessor_sha256,successor,successor_revision,successor_sha256,
minimum_lag}`. Minimum_lag is integer 0..1,000,000. Hashes bind full normalized snapshots.

Selected bundle exactly `{tasks,dependencies,calendars,plan,placements}`. Tasks and
calendars must be nonempty; dependencies/placements may be empty. Plan exactly
`{id,revision,tasks_sha256,dependencies_sha256,calendars_sha256}`; its cohort pins must
match the actual normalized cohorts. Placement exactly `{id,plan,plan_revision,
plan_sha256,task,task_revision,task_sha256,calendar,calendar_revision,calendar_sha256,start}`.
Every placement binds the full selected plan, task and calendar. The plan header pins
context, not a circular placement hash; the report scope separately pins placements.

IDs everywhere match `[a-z][a-z0-9_-]{0,47}`. Revisions are integers 1..1,000,000.
Booleans are not integers. Input start/end/release/due ordinals are integers 0..10^9,
with no live clock, time unit, calendar date, timezone, holiday or implicit conversion.
All hashes are exactly 64 lowercase hexadecimal characters. Schemas are exact: all
fields required, no unknown fields, inferred defaults, environment expansion or includes.

Each identity list has <=1,000 raw rows. Identical normalized ID snapshots count once;
conflicting groups exclude every member. Complete accounting: input_rows = accepted_records
+ duplicate_rows + conflict_rows + rejected_rows. Malformed identity rows produce fixed
side/row/code diagnostics without echoing rejected values. Invalid structural/reference/
graph scopes withhold assessment and cohort pins. Logical findings retain diagnostics
as described above without successful qualified scope pins. Empty required cohorts
cannot pass vacuously. Bad outer schemas, headers, list bounds and expansion limits are
fixed refusals. No silent dropping of unknown, malformed, conflicting or unplanned rows.

Pins hash compact sorted-key escaped ASCII JSON plus LF. Cohorts hash normalized selected
records sorted by ID. input_sha256 hashes exact raw bytes. Qualified_scope_sha256 binds
the report format and all named full cohort/plan pins. Pins are consistency receipts,
not signatures, authentic availability/duration, complete constraints, optimality,
privacy, rights or dispatch authority. Reports expose supplied opaque IDs/hashes:
keep real inputs/reports private. These tools do not anonymize or sanitize records.

One explicit JSON input <=4 MiB; duplicate keys, floats/nonfinite numbers, invalid Unicode,
depth >32, >100,000 nodes, strings >4,096 and JSON integers outside +/-10^18 are refused.
Output is escaped ASCII JSON <=8 MiB. Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md)
require ordinary single-link inputs and trusted quiescent storage. Default output is
stdout JSON. --out requires an absolute fresh destination under an existing trusted
external parent outside source; no overwrite, traversal or mkdir. Failed writes may
retain partial/unconfirmed output; inspect privately and choose a fresh path. Windows
inherits parent ACLs without a confidentiality guarantee. Shell redirection lacks these
guards. Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption. Errors omit
supplied paths/values. The guards do not sandbox hostile concurrent processes.

No calendar/provider access, collectors, commands, asset reads, clock collection,
URI/include following, database/network connections, optimization, reservations,
automatic rescheduling, dispatch or target changes. Independent directories have no
sibling runtime imports or third-party runtime packages. Only invented HVAC/game metadata
is included. Original private implementations, schedules, schemas, policies, records,
paths, credentials and operational details were not consulted or selected.
See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
