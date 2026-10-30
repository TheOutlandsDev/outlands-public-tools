# OUTLANDS | Service Completion Contract Checker

Reconcile tasks, parts accounting and declared evidence against exact work-order snapshots without service approval or operational updates. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and invented HVAC equipment/service examples.

Run from this complete tool directory:

```text
python -B completion.py --input examples/input.json
python -B completion.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out takes an
absolute fresh-report destination outside the source tree under an existing trusted
parent. No real equipment, private application, operational records or accounts needed.

## Contract and interpretation

Library `completion.check(raw_json_bytes)`. Input exactly
`{format,orders,contracts,tasks,parts,evidence}`, format `outlands-service-completion-v1`.
Order is the four-field snapshot `{id,asset_id,revision,state}` described in the
lifecycle tool. Every selected order needs exactly one contract. No lifecycle
events are supplied/recomputed here; pin matching is not proof of a valid history.

Contract is `{id,order_id,order_revision,order_sha256,required_tasks,required_evidence,
expected_parts}`. Revision must exactly match the supplied snapshot. Recompute the
snapshot's sorted-key compact ASCII JSON plus LF SHA-256 and require that pin.
Required_tasks and required_evidence are 0..32 unique symbolic tags, sorted during
normalization. Expected_parts is 0..32 unique item IDs, each exactly
`{item_id,unit,installed_quantity}` with quantity 0..10^12. Total requirements across
contracts are capped at 10,000. Empty requirements are allowed and establish only
consistency with that explicitly empty contract, not physical completion.

Task is `{id,order_id,order_revision,task_id,outcome}`, outcome done, blocked or
not_done. Part account is `{id,order_id,order_revision,item_id,unit,issued,installed,
returned,scrapped}`, all amounts whole integers 0..10^12. Evidence is
`{id,order_id,order_revision,kind,sha256}`, with a declared lowercase 64-hex digest.
All records must match the selected order revision and a declared requirement;
part units must match. Distinct IDs for one requirement or multiple contracts for
one order are ambiguous. Orphans, wrong pins/revisions, undeclared requirements,
conflicts or rejected rows withhold all assessments. No incomplete subset qualifies.

For valid scoped declarations, require completed order state, one done task per
required task, one record per evidence kind, and one account per expected item.
Parts must satisfy issued = installed + returned + scrapped and installed must
equal the expected installed_quantity. Missing/unfinished tasks, missing records,
noncompleted orders or parts differences return REVIEW_REQUIRED with every order's
complete diagnostic assessment retained. The fictional fixture issues two panel
filters, declares one installed and one returned, and asserts two completed tasks.

Output completed_under_contract is a consistency result on supplied declarations.
Evidence bytes are never opened or authenticated. Parts conservation does not prove
actual stock or prevent the same physical parts being claimed under distinct order
IDs. No physical inspection/service, stock update, order update or approval occurs.

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
