# Privacy and execution boundary

Included material is fresh generic code, fictional messages, tests and authored
notes. No historical service implementation, actual recipient/address, template,
route mapping, credential, endpoint, provider record, deployment setup or log is
included. The public demo sends no real email and writes no application files.

The core imports only standard-library dataclasses, regex and typing. It has no
filesystem, network, subprocess, environment-discovery or wall-clock adapter.
The CLI accepts only a demo flag and static help. Python imports trusted source
modules; use `-B` to prevent interpreter caches. Passing a custom transport is
permission for that caller-supplied code to run; it is not sandboxed or timed out.

Keep real messages, keys, routes, receipts, callback inputs, snapshots and provider
evidence private. Validation and fixed diagnostics do not anonymize content or
metadata. Exception text is not retained in entry state. An adapter can still
log, leak or mishandle data independently of the outbox.

Automatic retry trusts an adapter's definite-non-acceptance assertion. If that
assertion is false or the provider lacks reliable idempotency, duplicates remain
possible. A fresh outbox has no knowledge of earlier instances or provider state.
Unknown/interrupted attempts are withheld from replay; the reference offers no
automatic recovery or durable guarantee. Caller delivery reports are not checked
against a service and must not be presented as independently verified outcomes.

This is not production email software, a durable transactional outbox, an
exactly-once guarantee, a thread-safe queue or isolation from hostile Python
application code. Existing object references and process interruption can defeat
assumptions beyond the documented synchronous adapter outcomes. Do not publish
private data because the fictional example or contract checks pass.

Report issues with invented inputs only. Keep real messages, addresses, source
schemas, provider settings, credentials, private paths and logs out of issues.
