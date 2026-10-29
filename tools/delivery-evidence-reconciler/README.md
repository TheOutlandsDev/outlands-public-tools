# OUTLANDS | Delivery Evidence Reconciler

Reconcile declared attempts and delivery assertions without replay or real-delivery claims. Independent source CLI/library; Python 3.12/3.13,
standard library only, [MIT licensed](LICENSE).

## Fictional example

From the collection root (replace the EML example placeholder with a fully
spelled existing private directory outside the source tree):

```text
python -B tools/delivery-evidence-reconciler/delivery.py --input tools/delivery-evidence-reconciler/examples/evidence.json
```

No inputs are discovered automatically. These examples contain only invented
records and reserved example.invalid addresses. No real mail, private application
source, templates, routing, endpoints, credentials or delivery records are bundled.
No provider adapter, network call, send, retry, process launch or target update.
Combined packages and browser applications are deferred.


## Contract and state interpretation

`reconcile(raw)` accepts exact `outlands-delivery-evidence-v1` JSON with
`max_attempts` (exact integer 1..5) and 1..64 messages. Each message has a unique
identifier, lowercase `content_sha256`, `attempts` (0..5) and `reports` (0..8).
Identifiers/receipts match `[a-z][a-z0-9_-]{0,47}`. Content hashes are assertions;
no body is read, no relationship to a provider record is independently verified.

Attempts have consecutive one-based `number`, nondecreasing integer `tick`
(0..1,000,000,000,000), `outcome` and `receipt`. Supported outcomes:
retryable_not_accepted, permanent_not_accepted, accepted, uncertain. Only accepted
has a receipt; others require null. An additional attempt after acceptance,
permanent non-acceptance, uncertainty or declared exhaustion requires review.
Retries after definite non-acceptance must respect public outbox delays 1,2,4,8
ticks; early retries, exhausted limits or tick overflow are flagged. A caller
misclassifying uncertain acceptance as definite non-acceptance defeats this
evidence model; the tool cannot verify the assertion.

Reports have `attempt`, `receipt`, `outcome` (delivered/bounced). Only an exact
match to recorded acceptance can become DELIVERY_REPORTED or BOUNCE_REPORTED.
Identical repeats are accounted as duplicates; conflicting/orphan reports require
review. Any uncertainty/replay/conflict stays REVIEW_REQUIRED even if a later
record claims successful delivery. Acceptance without a report stays
ACCEPTED_PENDING_EVIDENCE. Definite rejection/exhaustion is FAILED; no attempts
is PENDING; recorded retryable non-acceptance is informational only.

The report always has `real_delivery_verified: false`, `retry_permitted: false`
and `target_changes_performed: false`. It is **not** a state reset, delivery
verification, authorization to resend or proof of exactly-once operation. It
never changes the existing outbox, reads a clock or invokes any transport.
It evaluates supplied list order and caller ticks, not wall-clock provenance.


## Files, diagnostics and privacy

See [checked Windows/POSIX I/O](IO-SAFETY.md), [origins](ORIGINS.md) and
[validation](VALIDATION.md). JSON parsing rejects duplicate keys, floats,
nonfinite numbers, invalid Unicode, excess depth/nodes and unknown fields.
Declared strings are generally at most 4,096 characters. Reports serialize as
ASCII JSON. `--out` creates a new external file only; parent must exist. No
overwrite, source-tree output or automatic cleanup/retry after write failure.
Failed writes may leave retained unconfirmed output; choose a new path.
Windows ACLs inherit from the chosen directory. Inputs must be trusted/quiescent.

Exit codes: 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption.
`--help` shows static usage; errors omit supplied values/paths. Default stdout
can contain private values or fingerprints. Output hashing and JSON escaping
provide no anonymization. Structural acceptance is not permission to publish
real inputs or reports, nor a secret/content scanner. No real delivery or
mail-client rendering is qualified.

From this tool directory:

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
