# OUTLANDS | Retry Budget Checker

Check declared attempt history against explicit attempt caps and delay rules without waiting, sending or retrying requests. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game metadata; offline and advisory.

Run from this complete tool directory:

```text
python -B retries.py --input examples/input.json
python -B retries.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No original program, real cache/journal, provider, payload or account needed.

## Contract and interpretation

Library `retries.check(raw_json_bytes)`. Input exactly `{format,policy,operations,
attempts,as_of}`, format `outlands-retry-budget-v1`. Operations use the shared schema.
Policy is `{id,revision,maximum_attempts,base_delay,maximum_delay,retryable_failures}`.
Maximum_attempts is 1..32, base_delay 0..1,000,000 and maximum_delay 0..1,000,000,000;
base_delay must not exceed maximum_delay. Retryable_failures is a unique sorted subset
of timeout/unavailable/rate-limited/transient; empty explicitly permits no retry class.

Attempt rows are `{id,operation,operation_revision,operation_sha256,policy_sha256,
ordinal,at,status,failure_class,result_sha256}`. Ordinal is 1..32. Exact operation
revision/full-snapshot pin and actual normalized policy pin must match. Failed status
requires one supported failure class and a declared result pin; succeeded requires
null failure class and a result pin; unknown requires null failure class/result pin.
Result pins are opaque receipt assertions, never opened or authenticated.

Different operation IDs sharing a key are ambiguous, preventing budget splitting.
Different attempt IDs for one operation/ordinal are also ambiguous. Require contiguous
ordinals from 1, nondecreasing at values, no receipt after as_of and no later attempt
after success, uncertainty or a failure class not permitted by policy. These protocol/
scope conflicts withhold the complete assessment and qualified scope pins; future
receipts are not filtered away. Operations are nonempty; attempts may be empty.

For failed attempt ordinal k, required delay before a successor is exactly
`min(maximum_delay, base_delay * 2**(k-1))`. There is no jitter, sleep, clock or time-unit
guessing. Equality meets the deadline. Chronologically valid early retries and histories
over the attempt cap return REVIEW_REQUIRED with all receipts/counts retained, without
truncation. Such findings disable further manual-attempt eligibility.

Report attempts, remaining budget (floor zero), early IDs, state and earliest_next_at.
No receipts means no_receipts with ATTEMPT_HISTORY_MISSING and no eligibility; absence
does not prove never executed. Unknown last outcome requires review with no deadline.
Succeeded and nonretryable failed outcomes are terminal. A retryable failed history at
its cap is exhausted; these terminal constraints can PASS consistency without allowing
another attempt. Below cap, report waiting or ready_for_manual_review at the exact
deadline. An earlier delay violation instead yields policy_review_required, even when
the next deadline has passed. Only a due, otherwise valid known-failure history is eligible for manual
attempt review. retry_authorized always remains false.

budget_review_sha256 hashes `{policy_sha256,operations_sha256,attempts_sha256,as_of}`
only for qualified history without review findings. Declaration pins remain available
for valid policy findings, but not protocol/scope conflicts. No dispatch, reservation,
budget consumption, wait, retry, service contact or exactly-once guarantee.

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
