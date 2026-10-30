# OUTLANDS | Correction Lineage Checker

Check pinned before/after snapshots, successor revisions and complete declared correction chains without editing records. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic code and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B corrections.py --input examples/input.json
python -B corrections.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects a
fresh absolute private report outside source under an existing trusted parent.
Library entry: `corrections.check(raw_json_bytes)`.

## Contract

Input exactly `{format,snapshots,corrections}`; format `outlands-correction-lineage-v1`.
Snapshot exactly `{id,record,revision,artifact_sha256}`. Snapshot ID identifies a
particular revision; record ID groups its declared history. Corrections exactly
`{id,before,before_revision,before_sha256,after,after_revision,after_sha256}`.
Both reference pins hash the entire selected snapshot, including its snapshot ID,
record ID, revision and artifact declaration. Artifact hashes are never opened.

Snapshots must be nonempty; corrections may be empty. Different snapshot IDs for one
record/revision are ambiguous. Different correction IDs sharing a before or after
snapshot are ambiguous: no fork/merge policy or preferred branch is invented. Every
edge must bind known exact snapshots, stay within one record, increase revision by
exactly one and change the artifact pin. Unknown/stale references, ambiguous slots,
self/reverse/non-successor/cross-record edges and unchanged artifacts withhold the
entire assessment and cohort pins. Reverting to an earlier artifact in a later
consecutive revision is permitted, with an explicit edge for every step.

For structurally unambiguous histories, sort each record by revision and require a
full consecutive sequence starting at 1 plus exactly one parent correction for every
revision above 1. Missing roots, revision gaps or missing parent edges retain diagnostic
record/snapshot/correction lists and cohort pins, but no review_scope_sha256. Revision
1 alone needs no correction. This is a complete-history declaration contract, not a
partial-history mode or proof that every real revision was supplied. No record content
diff, correction application, conflict resolution, database write or authenticity claim.

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
