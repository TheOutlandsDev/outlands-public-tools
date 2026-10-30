# OUTLANDS | Worker Lease History Checker

Check supplied ownership, renewal, expiry and takeover histories at an explicit as-of ordinal. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B leases.py --input examples/input.json
python -B leases.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `leases.check(raw_json_bytes)`.

## Contract

Input exactly `{format,items,lease_events,as_of}`; format `outlands-worker-leases-v1`.
Items and lease events use the shared shapes and temporal rules below. Items must be
nonempty; lease_events may be empty to report missing history. Unknown/stale item pins,
ordinal gaps, reversed times, alias slots or rejected/conflicting records withhold the
entire assessment and all scope pins. Validly shaped but logically invalid histories
retain diagnostics and pins, with no qualified scope.

assessment.items contains id, current_owner or null, highest_declared_acquire_token
and ordered history rows `{id,action,at,applied,failed_criteria}`. current_owner includes
worker, token, until and acquire_event only when the supplied history has a live owner
at as_of. Ownership may legitimately be absent after expiry/release. A wholly missing
history is a finding, not proof that work is free/unowned. Logical failures are not
applied, but an in-range rejected acquire still advances the highest declared token.
Future events are visible findings and do not update ownership or that counter.
ownership_windows gives the derived half-open windows; renewals extend and releases
truncate the same window. On a review result, these are partial diagnostics only.
items_sha256, lease_events_sha256 and as_of_sha256 bind the declarations. No clock,
lease store, worker identity, actual lock or externally enforced fencing is verified.

## Shared records, temporal semantics and trust limits

Work items are exactly
`{id,revision,kind,handler,handler_revision,handler_sha256,input_sha256,input_contract_sha256,result_contract_sha256,metadata}`.
metadata is 0..32 distinct symbolic IDs, sorted for normalization. Hashes and metadata
are declarations, not payload/schema inspection or proof a handler exists. Each item
ID has one selected revision; different revisions under the same ID conflict. A new
job/revision requires explicit rebinding of all dependent full snapshot references.

Lease events are exactly
`{id,item,item_revision,item_sha256,ordinal,at,action,worker,token,until}`.
action is acquire, renew or release. token is an integer 1..10^12; at/as_of are integers
0..10^12 in a caller-declared common ordinal time basis. until must be >at and <=10^12
for acquire/renew, and null for release. No implicit units, wall-clock or timezone.
Per-item ordinals are unique, contiguous from 1, <=1000, with nondecreasing times;
ties are resolved by ordinal for lease replay. Every item snapshot reference is exact.
Symbolic worker IDs describe fictional ownership claims, not authenticated machines.

Ownership windows are half-open `[start,end)`: an owner is inactive at end. Acquisition
requires no current live owner and a token strictly greater than every prior in-range
declared acquisition token for that item, including failed overlapping acquisitions.
There is no shared cross-item token counter. Renewal requires the same live worker/token
and strictly extends end. Release requires that same live owner and truncates end to
its event time. Renewing at expiry cannot resurrect ownership. Gaps between leases
are allowed. Future events are ignored for state/counter updates and require review.
At a release/expiry time, delivery/result/ack/commit ownership checks use the exclusive
boundary; no intra-time ordering is inferred for those claims. Empty-duration released
windows confer no time-based ownership. These rules are deliberately narrow.

Deliveries are exactly `{id,item,item_revision,item_sha256,ordinal,at,worker,token}`.
Per-item delivery ordinals are unique/contiguous from 1, <=1000, with nondecreasing at.
Other rows' at/token fields use the same limits. Each delivery binds the full item.
Lease histories are recomputed inside each independent consumer, not trusted from a
supplied PASS flag. Acknowledgement/result consumers withhold complete assessment
if any selected lease history has findings. They do not repeat handler/required-metadata
validation; run Work Item Contract Checker separately with the same item cohort pin.

IDs match `[a-z][a-z0-9_-]{0,47}`, revisions are integers 1..1,000,000, SHA-256 values
are 64 lowercase hex. Booleans never substitute for integers. Identity lists have at
most 1,000 rows. Identical normalized ID rows count once; conflicting groups exclude
every member, with complete accepted/duplicate/conflict/rejected-row accounting.
Different IDs claiming a unique ordinal/source slot are ambiguous, not silently chosen.
Hashes use ASCII JSON with sorted keys, compact separators and a trailing LF, normalized
set-like metadata sorted and cohort rows sorted by ID. input_sha256 hashes exact file
bytes. qualified_scope_sha256 is present only with no findings. Structural ambiguity
withholds complete assessment/scope pins; logical findings retain diagnostics/pins.
Fixed parser/outer-shape/size/time refusals are errors, not partial assessments.

All records are caller assertions; these tools establish no authenticity, complete
history, privacy, rights, runtime outcome, enforced ownership or authority. Overall
REVIEW_REQUIRED remains binding even where individual rows are consistent. Reports
expose supplied IDs, numeric declarations and hashes. Keep actual inputs/reports
private. Fingerprints are not anonymization/encryption: low-entropy values can be
guessed. These tools are not sanitizers or secret scanners.

One explicit JSON input <=4 MiB; strict parsing rejects duplicate keys, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and integers outside
+/-10^18. Output is escaped ASCII JSON <=8 MiB. Default stdout; --out requires an
absolute fresh external file under an existing trusted parent outside source. No
overwrite, traversal or mkdir. Ordinary single-link input and trusted quiescent storage
required. [Public Windows/POSIX I/O guards](IO-SAFETY.md) preserve POSIX no-follow/parent
descriptors and native Windows reparse/hardlink/change checks; they do not sandbox
hostile concurrent writers or guarantee inherited parent ACL confidentiality. Failed
writes can leave partial/unconfirmed output: inspect privately and select a fresh
filename. Shell redirection lacks these guards. Exit 0 PASS, 1 REVIEW_REQUIRED,
2 fixed refusal, 130 interruption. Errors omit supplied paths/values.

Independent standard-library directories have no sibling runtime imports. No payload,
handler or artifact opening, clock collection, worker discovery/contact, network/broker
access, acknowledgements, dispatch, retries, database writes, job execution or result
commits. payloads_opened, handler_executed, artifact_bytes_verified, worker_contacted,
ownership_enforced, jobs_executed, queue_changed, records_changed, results_committed
and target_changes_performed are false. No real customer/user data, private source,
paths, credentials, endpoints or operational configuration was selected. Only invented
HVAC/game metadata and reviewed public MIT helpers are included. See [origins](ORIGINS.md)
and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
