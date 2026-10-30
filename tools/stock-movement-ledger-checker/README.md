# OUTLANDS | Stock Movement Ledger Checker

Reconcile declared opening balances and ordered receipt/issue/adjustment histories without updating stock. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B movements.py --input examples/input.json
python -B movements.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `movements.check(raw_json_bytes)`.

## Contract

Input exactly `{format,stocks,movements,as_of}`, format `outlands-stock-movements-v1`.
Stocks must be nonempty; movements may be empty. Movement exactly `{id,stock,
stock_revision,stock_sha256,ordinal,at,kind,quantity}`. Ordinal is integer 1..1,000.
Kind is receipt, issue or adjustment. Receipt/issue quantities are integers 1..10^12;
adjustments are nonzero signed integers in +/-10^12. Every movement binds the full
selected opening stock snapshot, including its item/unit, quantity and opening ordinal.

For each stock, sort by ordinal; require contiguous ordinals from 1, nondecreasing at
values and no movement before its opening snapshot. Equal at values use explicit
ordinal order. Different IDs for one stock/ordinal slot are ambiguous. Unknown/stale
references, gaps, reversed chronology and malformed/conflicting rows withhold the whole
assessment and cohort pins. History is complete only as declared from this selected
opening snapshot; real-world completeness is not established.

At as_of, apply receipt +quantity, issue -quantity and signed adjustment quantity.
Every applied negative intermediate balance requires review even if later receipts
restore a positive closing balance. Future movements are visible, not applied, and
require review. A future opening gives closing_quantity null and no applied movements.
All validly scoped history rows report their delta, applied flag and balance_after;
unapplied rows have balance_after null. Idle histories preserve a current opening.
Logical findings retain diagnostics/cohort pins but not qualified_scope_sha256.
No physical stock verification, transaction posting, replay against a store or updates.
game-stock.json is invented crafting-token accounting metadata without game assets.

## Shared boundaries and report interpretation

Stock exactly `{id,revision,item,unit,on_hand,at}`. On_hand is a nonnegative integer
0..10^12; negative derived ledger balances are diagnostics, not accepted physical stock
snapshots for the next tool. Stock IDs represent explicit selected buckets; no location,
identity, alias or cross-bucket consolidation is inferred. Item/unit are symbolic IDs,
never unit conversion or supplier/customer catalog access.

IDs everywhere match `[a-z][a-z0-9_-]{0,47}`. Revisions are integers 1..1,000,000.
Booleans are not integers. At/as_of/due_at/horizon are explicit ordinal integers
0..10^12, not collected clock values or automatically interpreted dates/timezones.
All hashes are 64 lowercase hexadecimal characters and bind normalized selected
snapshots. Every schema is exact: all fields required, no unknown fields/defaults,
free-text notes, URLs, paths, account data, includes or environment expansion.

Each identity list has <=1,000 raw rows. Identical normalized snapshots for one ID
count once; conflicting groups exclude every member. Complete accounting is input_rows
= accepted_records + duplicate_rows + conflict_rows + rejected_rows. Malformed rows
produce fixed side/row/code diagnostics without echoing rejected values. Structural,
reference, identity and ledger-protocol errors withhold assessment and cohort pins.
Logical findings retain diagnostics as documented, without successful qualified scope
pins. Empty required cohorts cannot pass vacuously. Bad outer schemas, header ordinals
and list bounds are fixed refusals. All arithmetic uses exact integers, no floats or rounding
except the explicit upward order-multiple rule. Derived sums may exceed input quantity caps.

Pins hash compact sorted-key escaped ASCII JSON plus LF. Cohorts hash normalized selected
records sorted by ID. input_sha256 hashes exact raw bytes. Qualified_scope_sha256 binds
report format, all named cohort pins and supplied as_of/horizon where present. Pins are
consistency receipts, not signatures, authentic stock, usable inbound, distinct real
business claims, delivery evidence, privacy, rights or action authority. Reports expose
supplied IDs/hashes: keep actual inputs/reports private. These tools do not anonymize,
sanitize records or prevent a caller from inventing misleading identities/declarations.

One explicit JSON input <=4 MiB; duplicate keys, floats/nonfinite numbers, invalid Unicode,
depth >32, >100,000 nodes, strings >4,096 and JSON integers outside +/-10^18 are refused.
Output is escaped ASCII JSON <=8 MiB. Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md)
require ordinary single-link inputs and trusted quiescent storage. Default output is
stdout JSON. --out requires an absolute fresh destination under an existing trusted
external parent outside source; no overwrite, traversal or mkdir. Failed writes may
retain partial/unconfirmed output; inspect privately and choose a fresh path. Windows
inherits parent ACLs without a confidentiality guarantee. Shell redirection lacks these
guards. Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption. Errors omit
supplied paths/values. Guards do not sandbox hostile concurrent processes.

No live inventory/database/provider access, original document opening, collectors,
clock collection, commands, URI/include following, purchases, reservations, stock
updates, shipment execution or target changes. Independent directories have no sibling
runtime imports or third-party runtime packages. Only fictional HVAC/game metadata is
included. Original private implementations, schemas, policies, records, paths, credentials,
addresses and opsec details were not consulted or selected. See [origins](ORIGINS.md)
and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
