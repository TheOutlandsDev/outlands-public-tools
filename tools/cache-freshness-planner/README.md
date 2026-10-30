# OUTLANDS | Cache Freshness Planner

Evaluate supplied cache snapshots and exact dependency invalidations at an explicit as-of ordinal without reading a clock or mutating caches. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game metadata; offline and advisory.

Run from this complete tool directory:

```text
python -B freshness.py --input examples/input.json
python -B freshness.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No original program, real cache/journal, provider, payload or account needed.

## Contract and interpretation

Library `freshness.check(raw_json_bytes)`. Input exactly `{format,policy,entries,
invalidations,as_of}`, format `outlands-cache-freshness-v1`. Policy is `{id,revision,
lifetime}`, lifetime integer 0..1,000,000,000. As_of is an explicit ordinal, not a live
clock. Entry is `{id,revision,key_sha256,content_sha256,created_at,inputs}` with 1..32
unique dependency snapshots. This tool does not recompute key derivation; the separate
key checker supplies that explicit review step.

Invalidation rows are `{id,dependency,dependency_revision,dependency_sha256,at}`.
Every invalidation must reference an exact dependency snapshot present somewhere in
the selected entry cohort, including future-dated declarations. No silent dropping of
unrelated records. Different entry IDs for the same cache key are ambiguous even when
metadata matches; select one snapshot explicitly rather than choosing latest. Unknown
references, conflicting/rejected rows and slot ambiguity withhold the full assessment
and qualified scope pins. Entries are nonempty; invalidations may be empty.

expires_at = created_at + lifetime. For created_at<=as_of, age=as_of-created_at and
the entry is expired exactly when as_of>=expires_at. Lifetime zero means immediately
expired. A future creation returns future_creation with age null, never fresh. A matching
invalidation is applicable when at<=as_of and remains effective for that exact
dependency snapshot even if a cache entry is declared created afterward. A different
dependency revision is not invalidated merely by sharing its ID.

Report every applicable invalidation ID, expiry flag, age, deadline and failed criteria.
State precedence is future_creation, invalidated, expired, fresh; all applicable findings
remain visible even when one state takes precedence. Nonfresh entries require review.
Only fresh declarations have eligible_for_manual_read_review=true, which is not cache
read authorization. Future invalidations are declarations not yet effective at as_of.
Full selected policy/entry/invalidation pins remain visible for logical freshness
findings. No clock collection, eviction, refresh, purge, cache access or policy update.

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
