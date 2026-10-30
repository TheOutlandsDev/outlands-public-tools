# OUTLANDS | Work Order Lifecycle Checker

Validate selected work-order snapshots against explicit revision and state histories without dispatch or order updates. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and invented HVAC equipment/service examples.

Run from this complete tool directory:

```text
python -B orders.py --input examples/input.json
python -B orders.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out takes an
absolute fresh-report destination outside the source tree under an existing trusted
parent. No real equipment, private application, operational records or accounts needed.

## Contract and interpretation

Library `orders.check(raw_json_bytes)`. Input exactly `{format,orders,events}`,
format `outlands-work-order-lifecycle-v1`. Order snapshot is exactly
`{id,asset_id,revision,state}`, revision 1..1,000; state open, in_progress, on_hold,
completed or cancelled. Asset ID is an opaque declaration. Accepted orders must
be nonempty. Event is `{id,order_id,revision,at,kind}`; at is ordinal 0..10^9 and
revision 1..1,000. Every event must reference a supplied order.

| Current state | Event | Next state |
| --- | --- | --- |
| new | create | open |
| open | start | in_progress |
| in_progress | hold | on_hold |
| on_hold | resume | in_progress |
| in_progress | complete | completed |
| open / in_progress / on_hold | cancel | cancelled |

Completed/cancelled are terminal; this narrow protocol has no reopen or post-close
edit action. Events sort by ordinal, independent of row order. Ordinals must strictly
increase per order, and revisions must start with create at 1 and increase exactly
by one. Different orders can share ordinals. Distinct IDs for one order/revision
or tied events are ambiguous, even if otherwise identical. Exact repeated event
IDs count once. Every selected snapshot must match its final event revision/state.

Open, running or held snapshots are valid when their complete supplied history
prefix matches. They are not reported as completed work. Missing creation/history,
revision gaps, bad transitions, conflicting/rejected rows, orphan events or snapshot
mismatch withhold every order result. No latest-row selection or revision repair.

Output retains the four snapshot fields, event_count, first_at/last_at and order_sha256.
The pin covers only the normalized four-field snapshot, compact sorted-key ASCII
JSON plus LF; raw input SHA-256 separately covers the event history. Pin consistency
does not authenticate an asset, operator or work performed. The fictional filter
order has create/start/hold/resume/complete revisions 1..5. A completed state is not
completion evidence, service authorization or physical work proof.

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
