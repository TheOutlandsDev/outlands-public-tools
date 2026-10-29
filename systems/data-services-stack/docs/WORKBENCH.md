# Browser workbench contracts and limits

This upgrade uses the existing public stack and newly authored generic UI,
controller and tests. No additional original private implementation, business
formula/schema/mapping, recipient, setting, credential, record, path, log or
third-party asset was selected. Existing component algorithms, journal/state
schema and native Windows/POSIX helpers remain byte-identical.

## Ownership and requests

`serve` opens one existing quiescent journal and creates a separate new report
root. The report root cannot be inside the journal, source or repository; it must
not already exist. A restart chooses another new report root. Previous reports
remain retained independently. The journal layout is unchanged and existing CLI
commands, run keys and snapshots remain compatible.

One controller lock serializes all reads and mutations. Mutations and previews
require the currently observed journal head, preventing competing browser views
from silently acting on an old state. Refresh explicitly re-reads the journal
and clears result/preview pins and review assertions. It retains editor drafts.
The underlying Stack Python API still supports one synchronous owner; do not
call it outside the controller while serving.

The HTTP service binds to `127.0.0.1` only. API POSTs require the exact Host,
Origin, session token, JSON content type, one bounded Content-Length, no transfer
encoding and an exact request shape. Reads of private API data also require these
checks. No arbitrary static file, path read, custom transport, model, shell or
remote provider endpoint exists. HTML uses a nonce-based script policy, no-store,
no-referrer and escaped/text rendering. This is a trusted local single-operator
application, not remote/multiuser authentication or protection from hostile local
processes. Keep the page and token private.

Requests are at most 262,144 bytes. Configuration and input text are each at most
65,536 UTF-8 bytes. JSON refuses duplicate keys, non-finite numbers (including
exponent overflow) and depth over 64. Existing job and ingestion bounds remain.
Native diagnostics and invalid payloads are not echoed in error codes. Previews
and explicit result/report views intentionally reveal private supplied data.

## Preview, run and history

Preview hashes the exact UTF-8 text and saved job configuration and includes the
observed head. It shows accepted records, duplicates, fixed row issues and pure
baseline estimates without committing state. Contiguous single-series and history
rules apply before a clean preview is issued. A run rechecks the supplied preview
fingerprint, head, current job and input before calling the original Stack.run.
These pins detect stale content; they are not authorization or anonymization.

Changing input, selected job or configuration draft clears the UI preview.
Unsaved configuration is never applied implicitly. Historical results retain their
own job snapshot. Repeating a key with identical input/job is idempotent; changed
bytes or settings under that key remain a conflict. The forecast graph/table and
prefix-only MAE/RMSE describe stored baseline arithmetic, not measured usefulness
on real-world data. No training or business formula is introduced.

## Fictional queue operations

Every dispatch is one explicit call at a supplied monotonic integer tick, with a
bounded attempt limit and selected FakeTransport outcome. Real provider adapters
cannot be selected through the UI. Existing durable claims occur before any fake
callback. Definite rejection can schedule a future retry; acceptance, failure,
uncertainty and caller-reported delivery do not become automatic retries.

The simulated-interruption choice uses the public fake transport interruption;
the durable outcome remains REVIEW_REQUIRED. It is not a process-kill test. The
original actual child-process kill cases separately exercise run-start, claim and
fake-acceptance recovery. An accepted receipt permits only an explicit matching
caller delivery assertion, with an acknowledgment checkbox. No provider evidence
is checked and no real email is sent.

A lost/malformed mutation response blocks further mutations until explicit refresh.
The browser never automatically repeats a POST. Refresh reconciles visible state;
it does not prove a report was absent. Inspect the selected private report root
before retrying an uncertain export. One explicit retry can create another fresh
report, never replace an existing one.

## Private reports

Only an inspected completed run can be exported through the browser. Export
requires current head/result pins, a bounded reviewer label/note and fresh exact
boolean quality/privacy/rights/context assertions. The assertions authorize this
private report only, not public release. Existing CLI export behavior is retained.

Each attempt creates a new random report directory, with run.json and review.json
written exclusively and readback/hash checked. A final manifest.json records both
file lengths/hashes, the head/result pins and explicit private/unverified flags.
At most 128 attempts are allowed per server session. A failure can retain partial
output; no success response is returned and failed attempts are not adopted.
Original source input text is absent, but results, symbolic routes and review
notes can still be sensitive. Reports are not anonymized or encrypted. They are
selected-run reports, not full journal backups or a restore/migration facility.

## Stop and recovery

Normal UI stop uses a current head. The UI refuses overlapping actions; controller
serialization and server_close wait for owned request workers before releasing
the writer lock. This is bounded-operation draining, not cancellation of an
external backend. Force termination can leave a stale lock or unfinished state.
After independently confirming every owner is stopped, use the existing command:

```text
python -B stack.py --workspace PRIVATE_WORKSPACE recover --confirm-stopped
```

There is no browser recovery button or automatic recovery. Recovery conservatively
holds unfinished work; it never replays uncertain attempts. Corrupt committed
journals remain refused. No hostile-filesystem race, power-loss durability,
arbitrary journal repair, distributed delivery or exactly-once guarantee is made.
