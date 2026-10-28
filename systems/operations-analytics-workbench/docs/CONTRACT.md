# Explicit scenario and input contracts

The [invented scenario](../examples/sample-scenario.json) and
[completion batch](../examples/sample-events.json) define the runnable examples.
There is no original schema, policy, dataset or historical output in these files.

| Section | Declared information |
| --- | --- |
| `format`, `project_id`, `title` | `outlands-operations-scenario-v1`, bounded ASCII identity and display title. |
| `snapshot_utc`, `window` | Explicitly zoned timestamps; nonempty start-inclusive/end-exclusive window ending at or before the snapshot. |
| `capacity` | Demand units, aggregate headcount, cycle minutes, shift/break/unavailable minutes and productive-fraction assumption. |
| `process` | Planned/running/downtime minutes, ideal cycle minutes, total/good units and positive cycle samples. |
| `inventory` | One stock cohort per case: on-hand, allocations, asserted usable inbound, lead/review days, safety stock, usage, order multiple and receipt time. |
| `dispatch` | Versioned declared policy and candidates with readiness/hold/downstream-capacity assertions. Scores are not probabilities. |
| `active_lots` | Snapshot queue/buffer/hold categories, declared units and entry/hold times. |
| `completions` | Explicit selected events: source, event_id, family, positive whole units and zoned occurrence time. |
| `planning_reference` | Optional checked receipt/totals from the supported planning report. It always remains independently unverified. |

Case identities are unique within each area; active lot and event identities are
also unique in their explicit sets. Inputs reject unknown fields, duplicate JSON
keys, invalid UTF-8, non-finite numbers and ambiguous types. Integer quantities
reject strings, floats and booleans. Decision flags require actual JSON booleans.
Numeric assumptions accept at most six decimal places, with field-specific
positive/nonnegative bounds. Numeric strings are not accepted. Fractions use
Decimal internally; output ratios are ordinary finite JSON numbers.

Limits: 4 MiB per control/report buffer; JSON depth 64; 500 cases per area,
500 active lots, 2,000 completion events selected per scenario, 2,000 cycle
samples per process case, 100 stored projects, 200 revisions per project,
10,000 total accepted event identities and 5,000 review records. Native I/O caps
stores at 64 MiB. Count inputs are at most one billion; headcount is at most
100,000; declared time windows in capacity/process fields are at most 527,040
minutes. Calculated capacity/minimum-headcount results over one billion are
refused. Input limits are refusals, not silent truncation into a successful plan.

Capacity has no finite positive-demand staffing solution when productive time is
zero; the result is null. Empty process denominators remain null. Process time
must partition exactly at the accepted decimal precision; output cannot exceed
the declared ideal-cycle assumption. Cycle P90 uses linear interpolation at
`0.9 * (sample_count - 1)`; an empty sample has null cycle statistics.

Inventory assumes confirmed inbound is usable within its replenishment horizon.
It is not forecasting, valuation, multi-cohort accounting or supplier placement.
Dispatch weights are nonnegative, sum exactly to one, and use positive horizons.
Blocked candidates remain blocked regardless of their hypothetical score. Ties
sort by score descending, due time, then identity. Categories and thresholds are
declared policy, not measured manufacturing authority.

Completion timestamps normalize to fixed-width UTC with microsecond precision.
Window `[start, end)` includes exactly-start events and excludes exactly-end
events. Future observations and inconsistent holds are refused. Snapshot state
and period completions are distinct measures; reconciliation uses one canonical
selected event set. Throughput is per calendar hour, not net machine run time.

## Review command

Use actual hashes from your private current `plan` output. These are invented
placeholders:

```json
{
  "project_id": "sample-operations",
  "revision_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "domain": "capacity",
  "case_id": "base",
  "expected_version": 0,
  "status": "reviewed",
  "actor": "sample_reviewer",
  "note": "Fictional assumption review"
}
```

Domains: capacity/process/inventory/dispatch. Status: noted/needs_review/reviewed.
Aliases are bounded to 80 characters and notes to 1,000. Stale scenario/review
versions are refused. Every new scenario revision starts with its own review
scope; old reviews remain in private history. Review is an assertion, not a
signature, validation of operating policy or permission for physical action.
