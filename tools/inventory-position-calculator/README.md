# OUTLANDS | Inventory Position Calculator

Calculate on-hand plus declared eligible inbound minus reserved demand from exact supplied stock snapshots. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B position.py --input examples/input.json
python -B position.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `position.check(raw_json_bytes)`.

## Contract

Input exactly `{format,stocks,inbound,reservations,as_of,horizon}`, format
`outlands-inventory-position-v1`; horizon>=as_of. Stocks must be nonempty; inbound and
reservations may be empty. Inbound exactly `{id,stock,stock_revision,stock_sha256,item,
unit,quantity,source,state,due_at}`. Reservation exactly the same fields without due_at.
Quantity is integer 1..10^12. Source is an opaque declared line ID, not an endpoint or
document to follow. Inbound state is usable, pending or cancelled; reservation state
is reserved or released. Every claim binds an exact stock snapshot and matching item/unit.

Source IDs must be unique within each claim list, even across stock buckets. Different
record IDs for one source are ambiguous: no splitting/aliasing a selected incoming or
demand line across stocks. The inbound and reservation source namespaces are separate.
Unknown/stale references, mismatched item/unit, ambiguous sources or invalid/conflicting
rows withhold the whole assessment and cohort pins. Different unlinked source IDs are
distinct declarations, not proof that the underlying business claims are distinct.

Inbound is eligible exactly when state usable and as_of<=due_at<=horizon, inclusively.
Pending/cancelled/beyond-horizon claims remain visible but excluded. Every noncancelled
overdue inbound claim requires review and is excluded; cancelled overdue claims remain
excluded without that warning. A due value is not proof of receipt or usability.
Reserved claims subtract once; released claims remain visible but do not subtract.

Require stock.at==as_of before computing its position. A stale/future stock snapshot
retains claim totals but gives inventory_position null and requires review. For current
snapshots, position=on_hand+eligible_inbound-reserved_demand; negative positions remain
visible and require review. Empty claim lists yield the current declared on-hand amount.
All logical findings retain diagnostics/cohort pins but withhold the qualified scope pin.
No physical counts, inbound authentication, implicit netting across buckets, reservations
or stock changes. On-hand must already represent received goods; this schema accepts
only caller-selected outstanding inbound, not received lines to count again.

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
