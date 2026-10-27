# Message, transport and state contracts

`Message(key, route, subject, body)` and `Acceptance(receipt)` are frozen data
classes. Keys, symbolic routes and receipts match `[a-z][a-z0-9_-]{0,63}`.
Routes are tokens, not email addresses or provider destinations; mapping a route
is the private adapter's job. No normalization or source discovery is performed.

Subject/body must be nonblank Unicode strings, limited to 160/8,192 UTF-8 bytes.
Character length is checked before stripping, scanning and encoding. Subjects
reject all C0 controls. Bodies allow only LF and TAB among C0 controls. Both
reject DEL/C1 controls, Unicode line/paragraph separators and invalid Unicode.
Text is not rendered, executed, redacted or converted to an email/MIME object.

## Outbox API

- `Outbox(max_attempts=3)` accepts an exact integer from 1–5, never boolean.
- `enqueue(message)` owns a validated copy. A new key returns true; the exact
  same message under an existing key returns false in any state. Any changed
  content/route under that key raises `IDEMPOTENCY_CONFLICT`.
- `snapshot(key)` returns frozen `Snapshot(key, state, attempts, next_attempt,
  code)`, omitting route, subject, body and receipt. Keys/counts can still be
  sensitive. Unknown/invalid keys are refused with fixed codes.
- `dispatch(transport, now, limit=10)` attempts up to `limit` eligible messages
  in enqueue order. `limit` is an exact integer from 1–64. `now` is an exact
  integer from 0–1,000,000,000,000, never earlier than the last valid dispatch.
  Equal ticks are allowed. Tick units are supplied by the caller; no clock is
  read, no waiting occurs, and no scheduler runs.
- `report_delivery(key, receipt=...)` requires an accepted entry and its exact
  stored receipt. It records `DELIVERY_REPORTED` / `CALLER_REPORTED_DELIVERY`.
  An identical repeat returns false. This is a caller assertion, not verified
  provider evidence. Pending, failed and uncertain entries cannot be promoted.

All 64 keys are retained for the instance's lifetime, including terminal keys.
There is no purge, replay, reset, persistence, restore or automatic reconciliation.
Reentrant mutating calls during dispatch raise `OUTBOX_BUSY`; snapshots can
observe `IN_FLIGHT`. Concurrent callers are unsupported. Copies at enqueue and
adapter handoff keep ordinary accidental mutation out of stored message identity;
this is not isolation from hostile Python code.

## Transport outcomes

A synchronous `Transport.send(message)` must use the message key for its own
idempotency and implement this explicit outcome contract:

| Outcome | State / fixed code | Next action |
| --- | --- | --- |
| Valid `Acceptance(receipt)` | `ACCEPTED` / `ADAPTER_ACCEPTED` | No resend; a matching caller report may be recorded |
| `RetryableNotAccepted` | `PENDING` / `RETRY_SCHEDULED` | Retry only when due and within attempt/tick limits |
| Exhausted retry or tick overflow | `FAILED` / `RETRY_EXHAUSTED` | No automatic retry |
| `PermanentNotAccepted` | `FAILED` / `DEFINITELY_REJECTED` | No automatic retry |
| Generic exception, timeout or `DeliveryUncertain` | `REVIEW_REQUIRED` / `DELIVERY_UNCERTAIN` | No automatic retry or promotion |
| Invalid return value or receipt | `REVIEW_REQUIRED` / `ADAPTER_RESULT_INVALID` | No automatic retry |
| Interruption raised during the attempt | `REVIEW_REQUIRED` / `DELIVERY_INTERRUPTED` | Re-raise the control exception; do not continue later entries |

An attempt increments its counter and becomes `IN_FLIGHT` before the callback.
After explicit retryable non-acceptance, delays are 1, 2, 4 and 8 ticks, relative
to the current attempt's `now`. At the configured final attempt, or if the due
tick would overflow the bound, the entry fails. A dispatch invokes each eligible
entry at most once; advancing `now` never replays terminal or uncertain entries.

Only definite non-acceptance may be classified retryable. A lost response after
acceptance, malformed acknowledgment, timeout or interruption may have side
effects already. Review provider state privately before any separate recovery
action. No exception/provider text is retained in snapshots.

## Fake transport and limits

`FakeTransport(outcomes=())` accepts a tuple of up to 64 scripted outcomes:
`accept`, `retry`, `reject`, `uncertain`, `accepted_then_unknown`, `interrupt`.
One script position is consumed per call; after the script it defaults to accept.
An identical previously accepted key returns cached fake acceptance; changed
content is rejected. The acceptance cache holds at most 64 messages. Public
`calls` and `accepted_keys` describe this fake's memory, never real delivery.

These are bounded reference operations, not process resource quotas, provider
rate limits, atomic crash recovery, concurrency control or delivery guarantees.
Trusted adapter code may block or perform arbitrary actions; it is not sandboxed.
