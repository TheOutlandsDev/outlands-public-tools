# OUTLANDS | Material Allocation Coverage Checker

Check supplied demand and canonical-lot reservations for shortage, excess and overreservation without allocating stock. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic implementation and invented HVAC equipment/service examples.

Run from this complete tool directory:

```text
python -B allocations.py --input examples/input.json
python -B allocations.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional `--out` takes
an absolute destination path to a new report under a trusted existing parent
outside the source tree. Parent traversal (`..`) is refused. No real equipment
or private system is needed.

## Contract and interpretation

Library `allocations.check(raw_json_bytes)`. Input exactly
`{format,lots,aliases,demands,allocations}`, format `outlands-material-allocations-v1`.
Lot/alias schemas are shared below. Demand is `{id,item_id,unit,quantity}` and
allocation is `{id,demand_id,lot_id,quantity}`, quantities 1..10^12. At least one
demand and canonical lot are required. Empty allocations is a valid scoped review
that reports unmet demands. No eligible lot search or automatic reservation occurs.

Every demand/lot reference must exist; alias references resolve to canonical lots.
The demand item and unit must exactly match that lot's item/unit. Missing references,
invalid inventory, conflicting/rejected rows or item/unit mismatch withhold **both**
demand and lot summaries. The lot-contract pin is retained only if the inventory
declarations alone are structurally valid, even when allocations are invalid.

For valid scoped declarations, demand allocated is the sum of its allocations;
shortage=max(0,required-allocated), excess=max(0,allocated-required). Canonical lot
reserved sums all allocations through its canonical ID **and every alias**;
unreserved=available-reserved (possibly negative), excess=max(0,reserved-available).
Shortages, demand excess and lot overreservation return REVIEW_REQUIRED and retain
the complete diagnostic summaries. No incomplete accepted subset gets a PASS.
Exact repeated allocation IDs count once; different IDs are separate additive
claims, even if the demand, lot and quantity agree. Multiple demands may share a
lot, and one demand may span multiple matching lots.

The HVAC example reserves two motors through a label chain and four filters,
leaving two motors/four filters. The review example reserves five motors from a
four-motor lot and also exceeds the two-motor demand. This is a declared snapshot;
no FIFO, expiry, location priority, substitutions, chronology or live stock checks.
Reservations, inventory and work orders are never changed.

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
