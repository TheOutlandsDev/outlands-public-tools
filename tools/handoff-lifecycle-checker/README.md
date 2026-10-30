# OUTLANDS | Handoff Lifecycle Checker

Validate complete declared transfer histories and receipt references without transfers, delivery proof or stock checks. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic implementation and invented HVAC equipment/service examples.

Run from this complete tool directory:

```text
python -B handoffs.py --input examples/input.json
python -B handoffs.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional `--out` takes
an absolute destination path to a new report under a trusted existing parent
outside the source tree. Parent traversal (`..`) is refused. No real equipment
or private system is needed.

## Contract and interpretation

Library `handoffs.check(raw_json_bytes)`. Input exactly
`{format,unit,handoffs,events,receipts}`, format `outlands-handoff-lifecycle-v1`.
Unit is one symbolic label for the whole cohort. Handoff is
`{id,lot_id,quantity,from_bucket,to_bucket}`; quantity 1..10^12, endpoints distinct
symbolic bucket IDs. Lot ID is an opaque declaration here: this tool does not
resolve aliases, inspect inventory or verify unit/item compatibility. Select a
canonical ID explicitly from a separately reviewed identity result if needed.

Event is `{id,handoff_id,at,kind}`. `at` is ordinal 0..1,000,000,000, with no clock,
calendar or implied duration unit. Sort by at, independent of input order; distinct
event IDs at the same ordinal within one handoff are ambiguous. Exact repeated
event IDs count once. Every selected handoff requires a complete terminal history:

| Current state | Event | Next state |
| --- | --- | --- |
| pending | prepare | prepared |
| prepared | dispatch | dispatched |
| dispatched | accept | accepted |
| prepared or dispatched | cancel | cancelled |

All other transitions, missing terminal events, ties, orphan events or conflicting/
rejected rows invalidate the cohort. Open/in-progress histories are intentionally
not accepted as complete. Different handoffs may use the same event ordinals.

Receipt is `{id,handoff_id,event_id,quantity}`. Each accepted handoff needs exactly
one accepted receipt record referring to its own accept event with the exact
handoff quantity. A cancelled handoff must have no receipts. Missing references,
wrong event kinds/handoffs, different receipt quantities or multiple distinct
receipts invalidate the whole cohort. Every invalid history withholds all handoff
summaries and accepted/cancelled quantity totals. One valid handoff cannot conceal
another invalid one. Distinct handoff IDs are separate declarations.

The fictional service-kit bench receives two declared motors with an invented
receipt. The negative example changes that receipt quantity. Receipt validity is
structural consistency, not independent delivery evidence, actual stock coverage,
authorization or proof of service completion. Accepted totals count each handoff
once; no transfer, inventory deduction, dispatch, notification or signature occurs.

## Shared declarations and accounting

Identifiers and unit labels match `[a-z][a-z0-9_-]{0,47}`. No person, customer,
address, endpoint, path, credential or free-text note fields are defined. Quantities
are exact whole-unit integers; booleans, numeric strings and floats are refused.
No unit conversions or manufacturing/service policies are inferred.

Canonical lot is exactly `{id,item_id,unit,quantity}`, quantity 0..10^12. Alias is
exactly `{id,target_id}`. Canonical IDs and alias IDs share one namespace. All
canonical lots for one item must use the same unit. Alias chains are explicit,
bounded and iterative; no recursion or latest revision/status selection. The
lot-contract SHA-256 hashes sorted canonical lot objects and sorted alias objects
under `{lots,aliases}`, sorted-key compact escaped ASCII JSON plus LF. Input order
does not affect that pin; different chain declarations do. Raw input SHA-256
separately hashes the exact supplied bytes. Neither pin proves truth or authority.

Each list has at most 1,000 rows. Structurally identical snapshots under the same
ID count once plus duplicate_rows. Conflicting identity groups withhold **every**
member, including repeated identical members within the conflicting group.
Each list satisfies
`input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows`.
Diagnostics use fixed codes and 1-based logical row positions;
row 0 is a cohort issue. Rejected values are omitted. Cross-reference findings do
not reclassify structurally accepted rows. There is no implicit latest winner.

## CLI, file handling and privacy limits

One explicit JSON input <=4 MiB. Duplicate JSON keys, unknown fields, floating/
nonfinite numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 or
JSON integers outside +/-10^18 are refused. Escaped ASCII output <=8 MiB. Invalid
outer contracts or list bounds refuse entirely; row/reference/history problems
return REVIEW_REQUIRED with the documented result withholding rules. PASS is never
execution authorization, privacy clearance or independent verification of claims.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted, quiescent storage; no hostile-process filesystem sandbox or OS
resource quota. Default output is private stdout JSON. Optional --out exclusively
creates a fresh report under an existing external parent outside the source tree;
no overwrite or mkdir. Failed writes may retain partial/unconfirmed output; inspect
privately and choose a fresh path. Windows inherits parent ACLs without a privacy
guarantee. Shell redirection lacks --out protections. Exit 0 PASS, 1 REVIEW_REQUIRED,
2 fixed refusal, 130 interruption; supplied paths/values are omitted from errors.

No directory discovery, URI/include following, environment expansion, network,
database, clock, process execution or automatic target action. Real IDs, amounts,
declarations and reports can be private. These tools are not anonymizers or rights
checks. Only invented HVAC inputs are included; keep actual operational inputs and
reports private. See [origins](ORIGINS.md), [validation](VALIDATION.md) and the
collection's fictional-example guide in docs for the forward-looking HVAC theme.

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
