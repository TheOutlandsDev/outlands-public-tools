# OUTLANDS | Bill of Materials Contract Checker

Check explicit component references, DAG structure and bounded whole-unit requirements without orders or equipment sizing. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic implementation and invented HVAC equipment/service examples.

Run from this complete tool directory:

```text
python -B bom.py --input examples/input.json
python -B bom.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional
`--out ../fictional-new-report.json` requires a trusted existing external parent
and a destination that does not exist. No real equipment or private system needed.

## Contract and interpretation

Library `bom.check(raw_json_bytes)`. Input exactly `{format,components,links,orders}`,
format `outlands-bom-contract-v1`. Component is `{id,unit}`; link is
`{id,parent_id,component_id,quantity}` (1..1,000,000 component units per parent unit);
order is `{id,component_id,quantity}` (1..1,000,000,000). Units are explicit symbolic
labels; no conversion, fractional requirements, rounding, scrap factor or substitutes.
Each identity namespace is scoped to its own list. Components and orders must be
nonempty. A direct leaf order is valid; unused components produce no requirements.

Every link/order reference must exist. Distinct link IDs declaring the same ordered
parent/component pair are ambiguous, even with equal quantities; they are not added.
Exact repeated link IDs count once. Reject cycles anywhere in the supplied graph,
including disconnected or self cycles. Stable iterative topological traversal avoids
recursive graph depth. Order quantities accumulate at their components; each edge
then contributes parent demand times its per-parent quantity. Shared children receive
all paths plus direct orders. Requirements include assemblies and leaves, sorted by
component ID, with `is_leaf`; use leaves explicitly when preparing material demand.
Derived component demand above 10^18 refuses the entire calculation with fixed
`REQUIREMENT_LIMIT`. No partial requirements are emitted.

Two fictional air-handler kits need two blower modules, two blower motors and four
panel filters under the invented declarations. A shared-component diamond test
independently checks 4*(2*5+3*7)=124 leaf units. Missing/conflicting/rejected rows,
parallel edges or cycles withhold requirements and topological order. This checks
declared arithmetic, not equipment sizing, component compatibility, approved designs,
inventory availability or procurement authority. No order is created.

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
Each list satisfies input_rows = accepted_records + duplicate_rows + conflict_rows
+ rejected_rows. Diagnostics use fixed codes and 1-based logical row positions;
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
