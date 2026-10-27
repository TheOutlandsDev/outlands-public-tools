# OUTLANDS | Offline Notification Outbox Reference

A bounded, memory-only notification outbox with duplicate/conflict checks,
explicit retry decisions and uncertainty handling. Python 3.12/3.13, standard
library only, [MIT licensed](LICENSE).

This is fresh generic code and invented messages. It contains no original
application implementation, private template, address, route mapping, provider
configuration, credential or delivery record. The included transport is a fake;
no SMTP, email provider, network, file, clock or process adapter is supplied.

## Run the fictional example

From the collection root:

```text
python -B tools/notification-outbox/demo.py --demo
```

`FICTIONAL_OUTBOX_DEMO` shows duplicate suppression, a safe retry after definite
non-acceptance, adapter acceptance and a matching caller delivery report. A
second fake accepts a message then loses its response: the outbox retains
`REVIEW_REQUIRED` and never automatically replays it. `real_delivery_verified`
is false. No operator input or service is read and no application output files
are written. Use `-B` to prevent interpreter bytecode caches too. No arguments
or `--help` show static help; unknown arguments return a fixed error code.

## Library use

From this tool directory:

```python
from outbox import FakeTransport, Message, Outbox

box = Outbox(max_attempts=3)
notice = Message("notice", "sample_route", "Fictional summary", "Invented result.")
assert box.enqueue(notice)
assert not box.enqueue(notice)

fake = FakeTransport(outcomes=("retry", "accept"))
assert box.dispatch(fake, now=0)[0].next_attempt == 1
assert box.dispatch(fake, now=1)[0].state == "ACCEPTED"
assert box.report_delivery("notice", receipt="fake_receipt")
assert box.snapshot("notice").state == "DELIVERY_REPORTED"
```

`DELIVERY_REPORTED` records a matching caller assertion. The module never
queries a provider or verifies real delivery. Acceptance alone is not delivery.
Unknown outcomes are not automatically retried, even when the fake's internal
cache proves it accepted the message.

Only an adapter's explicit `RetryableNotAccepted` assertion permits a retry.
Generic exceptions, timeouts, invalid results and uncertain acceptance require
review. An adapter that misclassifies a potentially accepted operation as
retryable can cause duplicates; this module cannot verify its assertion.
`PermanentNotAccepted` records definite rejection without retry. No reset or
automatic reconciliation API is included.

All state and idempotency keys live only in this instance. Restarting it loses
them. Terminal entries continue to count against its 64-key capacity. The
reference is for one synchronous caller, not a durable transactional service or
an exactly-once delivery guarantee. A callback reentrancy guard is not a thread
lock. Transport calls have no timeout or sandbox.

See [contracts and states](FORMAT.md), [design rationale](ARCHITECTURE.md),
[validation](VALIDATION.md) and [privacy limits](SECURITY.md). Real messages,
keys, routes, receipts and snapshots remain private application data.
