# Work items, worker leases and queue-review methodology

These offline tools review selected declarations. They do not run jobs, contact
workers or brokers, enforce ownership, send acknowledgements or commit results.

| Term | Plain-language meaning | Exact meaning here |
| --- | --- | --- |
| Work item | One explicitly selected job declaration | ID/revision, kind, exact handler revision/hash, opaque input and interface hashes, and a set of symbolic metadata IDs. One selected revision per ID; conflicting revisions are excluded, not treated as history. |
| Handler contract | The interface a job claims to use | A selected handler ID/revision, kind, input/result contract hashes and required metadata IDs. No handler, schema, payload or metadata value is opened or validated. |
| Metadata presence | Required labels were declared | Set membership only. Extra labels are allowed; zero required labels is valid. Missing required labels retain diagnostic assessment and pins, with no qualified scope. |
| Snapshot pin | A fingerprint of a selected normalized declaration | Sorted-key, compact, escaped ASCII JSON plus LF; metadata sets sorted; cohort rows sorted by ID. A result-record pin includes the artifact hash declaration and differs from the artifact hash itself. Raw input pin covers exact input bytes. |
| Lease | A declared temporary ownership interval | Acquire, renew and release events for an exact item snapshot. Ownership windows are half-open [start,end): the owner is inactive at end. These are recomputed declarations, not actual locks. |
| Token | An ordinal ownership claim for one item | Integer 1..10^12. Acquisition requires a value above every prior in-range declared acquisition token, including rejected overlaps. No shared cross-item counter or external fencing is verified. |
| Time and as-of | A caller-selected numeric review basis | Integers 0..10^12 in one explicit common basis. No units, wall-clock readings or timezone conversion are inferred. Future records require review; future acquisitions do not update ownership or the token counter. |
| Event ordinal | Order within one item's selected history | Unique, contiguous integers from 1 through at most 1,000, with nondecreasing times. Ties order lease replay; delivery/result/ack/commit ownership still uses the exclusive window end. |
| Renewal and takeover | Extend a live claim, or acquire after it ends | Renewal needs the same live worker/token and a strictly later end. Acquisition needs no live owner and a higher declared token. Renewal at expiry cannot restore ownership. Lease gaps are allowed. |
| Delivery | A supplied claim that work was offered | An exact item snapshot, ordinal, time, symbolic worker and token. No broker delivery is established. |
| Acknowledgement | A selected claimed delivery outcome | acknowledged, requeued or dead_lettered; exact full delivery pin; matching live owner at the claimed time. One acknowledgement identity per delivery. A requeue or dead-letter claim does not complete the item. |
| Result and commit | Separate claims about output and persistence | Result binds item, delivery, worker/token and declared input/handler/result-contract/artifact hashes. Commit binds the full result record. Both need declared live ownership at their times. No artifact bytes or actual persistence are verified. |
| Duplicate and conflict | Repeated identical declarations versus incompatible identity claims | Identical normalized ID rows count once plus duplicate_rows. Conflicting groups exclude every member. Different IDs claiming a unique slot are ambiguous. Two commit IDs for one item are all unqualified, even with equal artifact claims. |
| Qualified scope | The entire selected declaration scope has no findings | qualified_scope_sha256 exists only with no issues. Structural findings withhold the assessment and scope pins; logical findings retain diagnostics/pins but withhold qualified scope. Consistent rows never override an overall REVIEW_REQUIRED. |
| PASS | The selected tool's declaration rules were met | It does not prove complete actual history, authenticated ownership, broker activity, payload correctness, artifact bytes, durable commits or exactly-once processing. execution_authorized remains false. |
| REVIEW_REQUIRED | Findings require interpretation | CLI exit 1. Missing, stale, conflicting, late or unaccounted claims must remain visible; no automatic latest-record selection or repair. |
| Fixed refusal | The requested input cannot be assessed | CLI exit 2 for parser, outer shape, size or numeric bounds. Library operations raise the fixed refusal. |
| Independent package | One tool can be installed and called alone | Its own versioned MIT wheel, CLI, fictional demo and check(raw_json_bytes) API. An exact-version collection installs all four. |

## Apply the method

1. Select handlers and work-item revisions explicitly. Run the item-contract check
   first. Each other consumer needs the same item cohort pin but does not repeat
   handler or required-metadata validation. Hash equality does not add that assurance.
2. Select complete relevant lease history and an explicit as-of basis. Recompute
   ownership; preserve missing history, overlaps, gaps, rejected higher tokens and
   future claims. Absence of history does not mean the item is free to execute.
3. Reconcile all selected deliveries and acknowledgements. A newer consistent
   acknowledgement does not erase a former owner's late or missing outcome.
   A missing prior acknowledgement remains a finding even when expiry permits a
   higher-token redelivery. No acknowledgement or redelivery is performed.
4. Review result/commit claims separately against the same item/lease/delivery pins.
   Acknowledgement and commit checks do not consume each other's conclusions.
   A timely result cannot authorize a commit after expiry. Equal artifact hashes
   do not resolve multiple commit identities, prove bytes or establish exactly-once.

The [installed exercise](../integrations/worker-queue/exercise.py) binds all four
tools to shared fictional snapshots. It demonstrates takeover, duplicates,
missing metadata, stale references, logical versus structural findings, future
events, expired acknowledgements/commits and ambiguous commit identities.
The [component guide](../integrations/worker-queue/components.json) provides exact
APIs, formats, examples, result fields and limits for people and AI callers.
Existing source acceptance separately calls the public Retry Budget Checker and
Idempotency Ledger Reconciler with explicit fictional mappings. Those calls do
not establish a worker ran, enforce ownership or authorize retry.

Each identity list is bounded to 1,000 rows. Symbolic IDs match
`[a-z][a-z0-9_-]{0,47}`; revisions are 1..1,000,000; metadata sets have 0..32 IDs.
Strict JSON input is at most 4 MiB; the source guides define parser, output and
native Windows/POSIX I/O limits. Real job payloads, worker identities, clocks,
queues, journals, artifact paths and reports stay private. Hashes are not
anonymization, authentication, an execution permit or permission to publish.
