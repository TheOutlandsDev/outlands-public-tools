# OUTLANDS | Lot Identity & Alias Checker

Resolve explicit aliases to declared canonical lots without duplicating stock or proving physical identity. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic implementation and invented HVAC equipment/service examples.

Run from this complete tool directory:

```text
python -B identities.py --input examples/input.json
python -B identities.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional
`--out ../fictional-new-report.json` requires a trusted existing external parent
and a destination that does not exist. No real equipment or private system needed.

## Contract and interpretation

Library `identities.check(raw_json_bytes)`. Input exactly `{format,lots,aliases}`,
format `outlands-lot-identities-v1`. See shared lot and alias schemas below.
At least one canonical lot is required; no aliases is valid. Aliases may point to
another alias or a canonical lot. Missing targets, cycles, canonical/alias ID
collisions, unit conflicts and any rejected/conflicting source row withhold the
whole identity map, canonical totals and lot-contract pin. No latest-row selection,
fuzzy matching, inferred alias, identity backfill or physical inspection occurs.

Output `identities` contains every canonical ID and alias, with canonical_lot_id,
item_id, unit and the canonical quantity. **Never sum these identity rows as stock.**
`canonical_totals` sums each accepted canonical lot once, grouped by item/unit.
Two aliases for a four-piece motor lot still represent four pieces, not twelve.
Distinct canonical lot IDs remain distinct even if all other fields agree; the
tool cannot detect duplicate physical stock recorded under different canonical IDs.
Zero canonical quantity is valid; no alias adds stock or changes the source.

The fictional service-motor-label points through motor-bin-label to motor-lot-a.
Its four motors and a separate eight-filter lot remain four and eight. The review
example introduces a cycle and intentionally withholds the complete map.
Pins establish declared-byte consistency, not authentic labels or inventory truth.

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
