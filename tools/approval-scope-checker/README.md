# OUTLANDS | Approval Scope Checker

Reconcile declared grants and revocations against exact item/policy pins at an explicit as-of ordinal. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic code and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B approvals.py --input examples/input.json
python -B approvals.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects a
fresh absolute private report outside source under an existing trusted parent.
Library entry: `approvals.check(raw_json_bytes)`.

## Contract

Input exactly `{format,policy,items,events,as_of}`; format `outlands-approval-scope-v1`.
Policy exactly `{id,revision,required_roles}` with 1..32 unique sorted role IDs.
Items use the selected snapshot schema. Event exactly `{id,item,item_revision,
item_sha256,policy_sha256,reviewer,role,at,action,grant}`. Reviewer and role are opaque
IDs, never names/accounts/authentication. Role must appear in the selected policy.
At and as_of are explicit integers 0..10^12, not collected clock values. Every event,
including a future one, must bind the actual normalized policy and selected item.

Action approve requires grant null. Revoke requires an exact event ID identifying an
approve event, the same item/revision/full pin/policy/reviewer/role and strictly later
at. Invalid references/pins/scope/order withhold the entire assessment and cohort pins.
Different event IDs for the same item/reviewer/role/at slot are ambiguous, even if the
claims appear equal. Identical ID snapshots count once. Multiple explicitly ordered
grants are visible individually; repeated revocations of one grant are idempotent
declarations, not real action counts. A revocation does not revoke later reapproval.

Items must be nonempty; events may be empty. A grant is active when at<=as_of and no
valid revocation of that exact grant has at<=as_of. Equality is effective. Future event
IDs remain visible and do not provide coverage. List order has no authority. Report
each item's active/revoked grant IDs and exact missing roles; missing coverage retains
assessment/cohort pins but review_scope_sha256 is null. A successful scope pin also
binds as_of. Different required roles may use the same declared reviewer: no separation
of duties or real authority policy is implied. No signatures, identity authentication,
approval execution, notification, publication or authorization to change anything.

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
