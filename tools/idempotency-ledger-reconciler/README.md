# OUTLANDS | Idempotency Ledger Reconciler

Reconcile selected operation-key, payload and result claims without executing operations or choosing a latest record. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game metadata; offline and advisory.

Run from this complete tool directory:

```text
python -B ledger.py --input examples/input.json
python -B ledger.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No original program, real cache/journal, provider, payload or account needed.

## Contract and interpretation

Library `ledger.check(raw_json_bytes)`. Input exactly `{format,operations,records}`,
format `outlands-idempotency-ledger-v1`. Operations use the shared schema. Record is
`{id,operation,operation_revision,operation_sha256,key_sha256,payload_sha256,state,
result_sha256}`. State is pending/unknown/succeeded/failed. Terminal states require a
result pin; pending/unknown require null result. Every operation revision/full snapshot,
key and payload must match the exact selected operation. Unknown/stale references,
malformed/conflicting identity rows or wrong key/payload bindings withhold the complete
assessment and all qualified scope pins. Records may be empty; operations may not.

Group by declared operation key and expose all operation IDs and selected claim IDs.
Multiple operation IDs under a key require OPERATION_KEY_ALIASES review even with the
same payload: there is no automatic canonical operation. Different payloads under that
key additionally create KEY_PAYLOAD_CONFLICT. Conflicting states/results, missing claims
for any selected operation, pending states and unknown states all require review and
leave declared_state unresolved with no selected result pin. No timeline or latest
record is inferred from list order, IDs or terminal-looking claims.

Equal declarations under different record IDs are counted as redundant claim records,
not executions. Distinct claims hash all record fields except record ID, including exact
operation binding. Repeating an identical snapshot under the same record ID is instead
tracked by duplicate_rows and never inflates selected claims. A single unambiguous
terminal declaration may PASS, whether succeeded or failed. This checks consistency
of the supplied claims, not that an operation occurred, failed, succeeded or ran once.

Report key groups, actual claim-record/distinct/redundant counts, all failed criteria,
unambiguous_terminal_claim and a result pin only for an unambiguous terminal group.
Logical conflicts retain full diagnostics and declaration pins. ledger_reconciliation_sha256
hashes `{operations_sha256,records_sha256}` only when all groups are unambiguous and
terminal. No database/ledger writes, deduplication of real operations, retry authorization,
result authentication, delivery proof or exactly-once execution claim.

## Shared schemas, arithmetic and privacy

IDs match `[a-z][a-z0-9_-]{0,47}`; revisions are integers 1..1,000,000. Hashes are
exactly 64 lowercase hexadecimal characters. Operation is exactly
`{id,revision,key_sha256,payload_sha256}`. A dependency snapshot is exactly
`{id,revision,sha256}`, sorted by ID within inputs; duplicate dependency IDs are
ambiguous even with equal snapshots. No raw keys, payloads, paths, credentials or URLs.

All at/created_at/as_of values are supplied integers 0..1,000,000,000,000 in an assumed
common ordinal convention. No date parsing, live clocks or time-zone conversion.
Deadlines may exceed the input ordinal ceiling by a bounded lifetime/delay; Python
integer arithmetic does not wrap. Integer fields reject booleans and coercion.

Identity lists have at most 1,000 raw rows. Identical normalized snapshots under one
ID count once plus duplicate_rows. Conflicting groups withhold every member, including
repeated identical members within the conflict. Each list satisfies
`input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows`.
Semantic key/slot/claim conflicts are separate from structural row counts. Fixed issue
codes use one-based logical positions; row 0 is a cohort finding. Rejected values are
omitted. No implicit latest entry, operation, dependency, receipt, policy or result.

Pins hash compact sorted-key escaped ASCII JSON plus LF. Collections sort by ID,
dependency/allowed-failure sets normalize as documented and explicit ordinals govern
history order. input_sha256 hashes exact raw input bytes. Fingerprints are consistency
receipts, not signatures, authentic cache state, collision proofs or publication rights.

One explicit JSON input <=4 MiB. Duplicate keys, unknown fields, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers
outside +/-10^18 are refused. Output is escaped ASCII JSON <=8 MiB. Malformed outer
schemas, header contracts and list bounds are fixed refusals; malformed identity rows
produce REVIEW_REQUIRED with qualified results withheld according to their scopes.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted quiescent storage. Default output is private stdout JSON. Optional
--out takes an absolute fresh destination under an existing trusted external parent
outside source; no overwrite, parent traversal or mkdir. Failed writes may retain
partial/unconfirmed output: inspect privately and choose a fresh path. Windows inherits
parent ACLs without a confidentiality guarantee. Shell redirection lacks these guards.
Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption. Errors omit supplied
paths/values. These guards do not sandbox hostile concurrent processes.

No cache/database/provider access, payload/asset reading, live collectors, clock,
sleep/backoff, command execution, dispatch, retries, environment expansion, URI/include
following or target updates. Only invented HVAC/game metadata is included. Keep actual
records/reports private. These tools do not anonymize data, prove authentic histories,
establish exactly-once execution or authorize actions/publication. See [origins](ORIGINS.md)
and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
