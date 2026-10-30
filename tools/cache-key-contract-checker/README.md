# OUTLANDS | Cache Key Contract Checker

Check explicit namespaces, key versions and dependency fingerprints without reading or changing a cache. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game metadata; offline and advisory.

Run from this complete tool directory:

```text
python -B keys.py --input examples/input.json
python -B keys.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No original program, real cache/journal, provider, payload or account needed.

## Contract and interpretation

Library `keys.check(raw_json_bytes)`. Input exactly `{format,contract,entries}`, format
`outlands-cache-key-v1`. Contract is `{id,revision,namespace,key_version,dependencies}`.
Namespace is an ID, revision/key_version integers 1..1,000,000 and dependencies 1..32
unique dependency IDs normalized by sorting. No implicit namespace/version/default key.

Entry is `{id,contract_sha256,inputs,key_sha256,content_sha256}`. Hashes are opaque
64-hex declarations, not raw cache keys or actual value bytes. Inputs is 0..32 unique
dependency snapshots `{id,revision,sha256}`, normalized by ID. Unknown or duplicated
dependency IDs are rejected rows; no nested latest-version selection. Every entry's
contract pin must match the actual normalized contract. Structural/conflict/stale
contract issues withhold the complete assessment and qualified scope pins.

Required dependency IDs must all be present. Missing dependencies retain diagnostics,
but expected_key_sha256 is null: no qualified partial key is derived. For a complete
entry, derive the expected key as the normalized JSON hash of
`{contract_sha256,inputs}`. The contract pin binds all contract fields, including
namespace, version, revision and declared dependency set. Input revision/hash changes
therefore change expected key material. A mismatched validly spelled supplied key
returns REVIEW_REQUIRED, not an automatic correction.

Group entries by supplied key. Different normalized input bindings under that key,
or different content pins under it, require review. This deliberately checks an
immutable key-to-content declaration: mutable/nondeterministic value policies are
outside the contract. Different entry IDs with the same key/material/content are
visible aliases and may PASS, counted as one unique key. Group consistent means only
that its declarations agree, separately from each entry's derivation validity.

Report every expected key, missing dependency, group membership and failed criterion.
Valid logical findings retain the assessment and declaration pins; qualified_entries_sha256
is issued only if every binding passes. entries_sha256 hashes all structurally selected
entries sorted by ID. No real cache read, key write, collision-resistance proof, value
verification, content ownership or data-privacy guarantee. game-cache.json is an
invented game-build metadata example with no assets or compiler invocation.

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
