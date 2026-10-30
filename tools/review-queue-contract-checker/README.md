# OUTLANDS | Review Queue Contract Checker

Check explicit queue membership, snapshot bindings, required role coverage and declared blockers. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic code and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B queues.py --input examples/input.json
python -B queues.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects a
fresh absolute private report outside source under an existing trusted parent.
Library entry: `queues.check(raw_json_bytes)`.

## Contract

Input exactly `{format,policy,items,entries}`; format `outlands-review-queue-v1`.
Policy is `{id,revision,required_roles}` with 1..32 unique role IDs sorted for pins.
Items use the selected snapshot schema described below. Entry is exactly
`{id,item,item_revision,item_sha256,stage,covered_roles,blockers}`. Stage is an opaque
ID, never interpreted as completion. Covered_roles and blockers are 0..32 unique IDs
normalized by sorting; covered roles must be a subset of policy roles.

There is at most one entry ID per item. Unknown items, stale revision/full-snapshot
pins or competing entries withhold the whole assessment and cohort pins. Items must
be nonempty; entries may be empty. No latest revision/queue selection or queue discovery.

For each item, report its entry/stage, exact missing roles and blockers. A missing
entry, missing coverage or any declared blocker requires review; diagnostics and full
selected cohort pins remain visible but review_scope_sha256 is null. A complete,
unblocked declaration is ready_for_manual_review, never proof that review occurred.
No reviewer identity, approval event, source document or evidence bytes are consulted.
The separate Approval Scope Checker can inform an explicit operator-authored adapter;
there is no automatic trust or runtime coupling between tools. game-review.json is
an invented game quest review declaration with no game assets or scripts.

## Shared boundaries and report interpretation

Selected item/node snapshot exactly `{id,revision,artifact_sha256}`. IDs everywhere
match `[a-z][a-z0-9_-]{0,47}`; revisions are integers 1..1,000,000, not booleans.
Hashes are 64 lowercase hexadecimal characters. They are opaque caller declarations,
not content reads. Policy IDs/revisions follow the same rules. All fields are required;
unknown fields are refused. No inferred defaults, free-text notes, paths or user records.

Each identity list has <=1,000 raw rows. Structurally normalized identical snapshots
with one ID count once; conflicting snapshots exclude every member of that ID group.
Malformed rows are rejected with fixed side/row/code diagnostics without echoing their
values. Complete accounting: input_rows = accepted_records + duplicate_rows +
conflict_rows + rejected_rows. Invalid scope/reference/identity structure withholds
assessment and cohort pins. Logical incompleteness described above retains diagnostics
but never a successful review_scope_sha256. Empty required cohorts cannot pass vacuously.

Pins hash compact sorted-key escaped ASCII JSON plus LF. Sets normalize by sorting;
cohorts hash selected normalized records sorted by ID. input_sha256 hashes exact input
bytes. Qualified review_scope_sha256 binds the named full-cohort/policy pins, plus
as_of in Approval Scope Checker. Pins are consistency receipts, not signatures,
authentic reviewers/history, artifact verification, privacy or publication rights.

One explicit JSON input <=4 MiB; duplicate keys, floats/nonfinite numbers, invalid
Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers outside +/-10^18
are refused. Output is escaped ASCII JSON <=8 MiB. Invalid outer schemas, header
policies and list bounds are fixed refusals. Reports expose supplied opaque IDs/hashes:
keep actual inputs/reports private. These tools do not anonymize or sanitize records.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted quiescent storage. Default report is stdout JSON. Optional --out
requires an absolute fresh destination under an existing trusted external parent
outside source; no overwrite, parent traversal or mkdir. Failed writes may retain
partial/unconfirmed output; inspect privately and choose a fresh path. Windows inherits
parent ACLs without a confidentiality guarantee. Shell redirection lacks these guards.
Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption. Errors omit supplied
paths/values. The guards do not sandbox hostile concurrent processes.

All operations remain offline/advisory. No document/asset dereferencing, live collectors,
clock, account/directory lookup, databases, command execution, URI/include following,
environment expansion, approval dispatch or target changes. Independent directories
have no sibling runtime imports. Only invented HVAC/game metadata is included.
Original private code, records, policies, configurations, credentials, paths and opsec
details were not consulted or selected. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
