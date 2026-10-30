# OUTLANDS | Rework History Checker

Validate a narrow declared inspect/rework/scrap protocol and derive selected dispositions without process actions. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and fictional HVAC inspection records.

Run from this complete tool directory:

```text
python -B rework.py --input examples/input.json
python -B rework.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out needs an
absolute destination for a fresh report outside the source tree under an existing
trusted parent. No private application, real equipment or operational records needed.

## Contract and interpretation

Library `rework.check(raw_json_bytes)`. Input exactly `{format,units,events}`,
format `outlands-rework-histories-v1`. Unit is `{id}`; accepted units must be nonempty.
Event is `{id,specimen_id,at,attempt,kind}`. Specimen must reference a supplied unit.
At is integer ordinal 0..1,000,000,000, not a clock/calendar. Attempt is integer
1..1,000. Kinds are inspect_pass, inspect_fail, rework or scrap. Lists have at most
1,000 rows each; no external histories are discovered.

This version intentionally implements one small declared protocol:

| State | Allowed next event | Attempt rule | Result |
| --- | --- | --- | --- |
| new | inspect_pass / inspect_fail | 1 | passed / failed |
| failed | rework | same failed attempt | awaiting_reinspection |
| awaiting_reinspection | inspect_pass / inspect_fail | previous attempt + 1 | passed / failed |
| failed | scrap | same failed attempt | scrapped |

Passed/scrapped are terminal. Repair without a failed inspection, repeated repair
without reinspection, skipped/wrong attempt numbers, repeated terminal events or
direct scrap of a new/passed unit are invalid. This is a fictional generic contract,
not a reconstruction of a private route, repair policy or arbitrary workflow graph.

Events sort chronologically per unit, independent of row order. Distinct event IDs
at one ordinal in the same history are ambiguous; identical snapshots under one ID
count once. Different units may use the same ordinals. Every unit needs a terminal
history; open, empty or failed-only histories require review. Any invalid/conflicting/
orphan row, tie, transition or incomplete unit withholds the whole cohort's histories,
derived dispositions and totals. No incomplete accepted subset is reported as good.

A valid unit derives first_pass_good after one passing inspection, reworked_good
after a later passing attempt, or scrap after its declared scrap event. Output
dispositions use the unit ID as their record ID and match the Yield & Scrap schema;
the caller explicitly selects the cohort when handing them over. Histories retain
inspection/rework counts and first/last ordinal, not a duration or actual work proof.
Totals sum attempt/rework counts. Outcomes are supplied assertions, not recomputed
measurements. No inspection, repair, scrap, device operation or route execution.

## Shared accounting, CLI and privacy limits

All IDs and unit labels match `[a-z][a-z0-9_-]{0,47}`. Each list has at most 1,000
rows. Exact normalized identity snapshots count once plus duplicate_rows; conflicting
groups withhold every member, including repeated identical members within the group.
Every list satisfies
`input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows`.
Cross-reference findings do not reclassify structurally accepted rows. Diagnostics
use fixed codes and 1-based logical positions; row 0 denotes a cohort/pair issue.
Rejected values are omitted. No latest status, revision or event is inferred.

One explicit JSON input <=4 MiB. Duplicate keys, unknown fields, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers
outside +/-10^18 are refused. Integer fields reject booleans and numeric strings.
Decimal values are supported only in the stated string schema. Output is escaped
ASCII JSON <=8 MiB. Invalid outer contracts or list/product bounds refuse entirely;
valid scoped findings retain or withhold results as specified above. Raw input
SHA-256 covers exact supplied bytes. Pins establish consistency, not authenticity.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted quiescent parents; no hostile-process filesystem sandbox or OS
quota. Default output is private stdout JSON. Optional --out takes an absolute new
report destination under an existing external parent outside the source tree.
No overwrite, parent traversal or mkdir. Failed writes may retain partial/unconfirmed
output; inspect privately and use a fresh path. Windows inherits parent ACLs without
a confidentiality guarantee. Shell redirection lacks --out protections. Exit 0 PASS,
1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption; errors omit supplied paths/values.

No network, database, device, live clock, command execution, include/URI following,
environment expansion, directory discovery or automatic target action. Reports can
contain private IDs, readings, limits, counts and outcomes. The tools are not
anonymizers, publication-rights checks or independent truth/authority verifiers.
Keep actual inputs/reports private. Invented HVAC demo-units are not engineering
specifications or maintenance instructions. See [origins](ORIGINS.md) and
[validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
