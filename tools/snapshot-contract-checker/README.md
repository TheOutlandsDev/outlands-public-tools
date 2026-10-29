# Snapshot Contract Checker

Check a caller-supplied manifest, a separately supplied pinned policy and explicit
artifact buffers. Python 3.12/3.13, standard-library runtime, MIT TheOutlandsDev.
Fresh generic implementation with invented declarations; no original deployment,
source mapping, endpoint, database or operational record is included.

Run from this tool directory:

```text
python -B snapshot.py --manifest examples/manifest.json --policy examples/policy.json --item records examples/records.txt
```

The fictional example returns exit 0/PASS at the inclusive 3,600-second freshness
boundary. It observes exact bytes and hashes for one two-record declaration, with
three declared source records reconciled as two accepted and one duplicate.
`--item ID FILE` is repeatable; select every item exactly once. Manifest and policy
schemas contain identifiers rather than paths. No declared path/URL is followed,
directory is enumerated, host clock is read or source system is contacted.

Library: `snapshot.check(manifest_bytes, policy_bytes, {'records': artifact_bytes})`.
It uses only supplied buffers. The CLI uses checked reads for explicitly selected
local files. No sibling tool installation is required.

## Contracts and interpretation

See the complete [manifest](examples/manifest.json) and [policy](examples/policy.json).
Both use exact fields. Manifest: `outlands-snapshot-v1`, snapshot ID, version,
capture time, item ID/size/hash/declared record counts, and declared reconciliation.
Policy: `outlands-snapshot-policy-v1`, exact raw manifest SHA-256, expected version,
explicit as-of time, maximum age and expected item IDs/declared record counts.
The version is an opaque lowercase identifier, not semantic-version ordering.
Hashes are lowercase SHA-256. Timestamps are exact valid UTC
`YYYY-MM-DDTHH:MM:SSZ`; numeric limits are strict integers, excluding booleans.

The checker reports manifest-pin/version mismatches, future captures, stale age,
expected-set differences, file-size/hash differences and declared count conflicts.
`input_records = accepted_records + duplicate_records + rejected_records`, and
the declared accepted total must equal the sum of item record declarations.
An artifact byte hash is observed; **record counts inside opaque artifacts are
not independently parsed or verified**. Matching false declarations can pass;
the result explicitly retains `record_counts_independently_verified: false`.
Rejected records do not themselves fail this declaration checker when accounting
is consistent. Any downstream acceptance policy must review that separately.

A copied or maliciously replaced manifest and matching policy are not authenticated
by a hash. Supply a trusted pin through an independent review process. Capture
time, source completeness and policy suitability remain caller assertions. A
PASS establishes the documented relationships, not source authority or anonymity.

Limits: 4 MiB per selected file, 16 items, 16 MiB combined artifact buffers,
one million declared records per item, 16 million reconciliation counts and
366 days maximum freshness allowance. Zero-second allowance requires the capture
and as-of times to match. JSON is bounded to depth 32/100,000 nodes; duplicate
keys, floating-point literals, nonfinite numbers and undeclared fields fail.
The CLI reads artifact files sequentially into retained buffers; there is no
atomic multi-file capture or revalidation of paths after that completed read.

## Results

Private JSON contains identifiers, hashes, observed byte sizes, declared counts,
age and issue codes. Inputs and reports can identify a private project. Default
stdout creates no report file. Optional `--out NEW_PRIVATE_REPORT.json` exclusively
creates a new external report; existing files are refused. See
[I/O boundaries](IO-SAFETY.md), [origins](ORIGINS.md), [validation](VALIDATION.md).
Exit 0 PASS; 1 review required; 2 invalid input/refused I/O; 130 interruption.
No target update, deletion, database write or automatic retry occurs.
