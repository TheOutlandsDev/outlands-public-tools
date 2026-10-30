# OUTLANDS | Training Selection Contract Checker

Reconcile pinned training selections against explicit approvals, exclusions and label policy without exporting or training. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic dataset logic and newly invented HVAC equipment/fault declarations.

Run from this complete tool directory:

```text
python -B selection.py --input examples/input.json
python -B selection.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report destination outside source under an existing trusted
parent. No original data, private application, weights, provider or accounts needed.

## Contract and interpretation

Library `selection.check(raw_json_bytes)`. Input exactly
`{format,taxonomy,records,approvals,exclusions,selections,policy}`, format
`outlands-training-selection-v1`. Records use the complete shared dataset snapshot.
Policy is `{id,revision,allowed_labels}`, 1..32 unique labels declared in taxonomy.
Its pin hashes the normalized complete policy, including ID and revision.

Every link has `{id,record,record_revision,record_sha256}`. record_sha256 hashes the
complete normalized target record, including its label/group/partition, not just its
declared content hash. Approvals additionally require `{policy_sha256,taxonomy_sha256,
decision}`; decision is approve/reject. Selections additionally require policy_sha256.
Exclusions additionally require an identifier reason. All references must match the
current target's exact revision and snapshot hash. Approval taxonomy and approval/
selection policy pins must match the actual normalized contracts. All links are
validated, including unused approvals/exclusions; stale entries are not ignored.

Different approval IDs for the same record or different selection IDs for the same
record are ambiguous. Multiple explicit exclusion reasons may target a record.
Malformed/conflicting rows, ambiguous slots, stale/unknown references or pin mismatches
withhold the complete assessment and all qualified pins. Records and selections must
be nonempty. There is no latest approval, latest record or implicit approval.

For a structurally qualified selection, require partition=train, label allowed by
policy, exactly one declared approval with decision=approve, and no exclusion.
Exclusion wins over approval. Failed criteria return REVIEW_REQUIRED and retain
per-selection findings, selected/eligible counts and false eligibility. If all pass,
eligible_for_manual_export_review is true and selected_records_sha256 hashes complete
selected source snapshots sorted by record ID. Otherwise that selected pin is null.
records_sha256 hashes all selected source records; taxonomy/policy pins cover their
contracts. These are consistency receipts, not authenticated approvals, label truth,
holdout independence, rights clearance or export authorization. No dataset is exported,
sampled, read from content paths, modified, trained or promoted.

## Shared declarations, CLI and privacy limits

All IDs match `[a-z][a-z0-9_-]{0,47}`. Revisions are integers 1..1,000,000 (no booleans
or coercion). Taxonomy is exactly `{id,revision,labels}`, 1..32 unique label IDs,
normalized by sorting. SHA-256 strings are exactly 64 lowercase hexadecimal characters.
Dataset snapshots, used by the partition and selection tools, are exactly
`{id,revision,content_sha256,group,partition,label}`. Partition is train/validation/test;
group is an explicit equipment/entity group ID; label must be declared in taxonomy.
Hashes and group assignments are supplied assertions; no artifact bytes are opened.

Each identity-snapshot list has at most 1,000 rows. Identical normalized snapshots
under one ID count once plus duplicate_rows. Conflicting ID groups withhold every
member, including repeated identical members within that group. Each list satisfies
`input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows`.
Semantic slot/membership findings are reported separately from structural row counts.
Diagnostics use fixed codes and 1-based logical positions; row 0 means a cohort-level
finding. Rejected input values are omitted. No latest version is selected implicitly.

Pins hash compact sorted-key escaped ASCII JSON plus LF; selected record collections
sort by ID and taxonomy/policy labels sort lexically. input_sha256 instead hashes exact
raw input bytes. Pins are consistency receipts, not signatures, proof of ownership,
approval authenticity, privacy clearance or truth. Keep actual inputs/reports private.

One explicit JSON input <=4 MiB. Duplicate keys, unknown fields, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers
outside +/-10^18 are refused. Output is escaped ASCII JSON <=8 MiB. Malformed outer
contracts, policies, taxonomy and list bounds are fixed refusals. Malformed identity
rows and reference conflicts produce REVIEW_REQUIRED with qualified results withheld.
Valid review findings retain results as described in each contract.

Public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link inputs and
trusted quiescent storage. Default output is private stdout JSON. Optional --out takes
an absolute fresh destination under an existing trusted external parent outside the
source tree; no overwrite, parent traversal or mkdir. Failed writes may retain partial
or unconfirmed output: inspect privately and select a fresh path. Windows inherits
parent ACLs without a confidentiality guarantee. Shell redirection lacks these guards.
Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption. Error messages omit
supplied paths and values. These guards do not sandbox hostile concurrent processes.

No network/provider/model calls, training, content collection, dataset export, clock,
command execution, environment expansion, URI/include following or directory discovery.
Only newly invented HVAC fixtures are included. The tools do not anonymize data or
verify real identities, approvals, labels, hashes, independence or publication rights.
See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
