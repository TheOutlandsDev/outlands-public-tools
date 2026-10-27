# Offline Notification Outbox Reference

This batch adds fresh generic in-memory notification state handling, a fake
transport, invented messages and authored format/design/privacy notes. No
historical email-service implementation, actual template, recipient, route
mapping, credential, provider configuration, delivery record or operational
policy is exported.

The core retains bounded idempotency keys, rejects conflicting content, retries
only explicit definite non-acceptance, and records acceptance separately from a
matching caller delivery report. Generic exceptions, timeouts, invalid results
and uncertain/interrupted outcomes require review without automatic replay.
Control exceptions during the callback are re-raised after recording uncertainty.
The report state is a caller assertion, never independently verified delivery.

The module has no file, network, process, wall-clock or service adapter. It is
one synchronous caller and in-memory state, with explicit capacity/retry/tick
bounds. No persistence, concurrency, exactly-once delivery or automatic recovery
is claimed. Actual messages, keys, routes, receipts and snapshots remain private.

The dedicated Windows/Ubuntu Python 3.12/3.13 workflow requires all 45 fictional
methods without skips, the actual fake-transport demo and documentation checks.
An independent standalone state oracle and exact selected-source audit support
publication review. No historical application bodies or operational inputs are
needed. MIT covers the selected original additions; callers' inputs and separately
supplied runtimes retain their own terms. Existing repository identity/history
outside these selected files is not cleared by this batch.

See [usage](../tools/notification-outbox/README.md),
[state contract](../tools/notification-outbox/FORMAT.md),
[rationale](../tools/notification-outbox/ARCHITECTURE.md),
[validation](../tools/notification-outbox/VALIDATION.md) and
[privacy limits](../tools/notification-outbox/SECURITY.md).
