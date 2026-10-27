# Configuration and library contracts

Configuration is UTF-8 JSON of at most 65,536 bytes, with exactly `version: 1`
and `jobs`. One to 16 jobs are accepted; IDs must be unique. Duplicate JSON keys,
nonstandard numeric constants, unknown fields, booleans in integer parameters
and invalid method/history combinations are refused with fixed codes.

Each job has exactly these fields:

| Field | Contract |
| --- | --- |
| `id`, `route` | Symbolic `[a-z][a-z0-9_-]{0,63}` tokens; route is not an address |
| `input_format` | `csv` or `jsonl` |
| `method` | `last`, `mean` or `seasonal` |
| `horizon` | Integer 1–32 |
| `window`, `season`, `min_history` | Integers 1–256 |
| `max_attempts` | Integer 1–5 |

Minimum history must satisfy the selected method's window/season requirement.
Input paths, credentials, queries and provider destinations are deliberately not
configuration fields. A run receives its input separately. Replacing configured
jobs preserves every run's original job snapshot. It does not migrate old runs.

## Run identity and gates

`Stack.run(job_id, key, raw_bytes)` accepts at most 65,536 bytes. The shared public
ingestion core enforces exact `series, period, value` CSV/JSONL contracts and a
maximum of 256 records/32 accepted series. A clean batch, one contiguous ordinal
series and sufficient history are mandatory before forecasting/evaluation.
The baseline methods and prefix-only one-step scores retain their public rules.

A run key is a canonical token. Identity is bound to the canonical job snapshot
and SHA-256 of original input bytes. An identical existing key returns its saved
summary without recomputation or notification. Changed bytes/configuration under
that key are a conflict, even when parsed values would be equivalent. A distinct
key means a distinct requested run. The workspace retains at most 128 run keys.

Runs are `RUNNING`, `COMPLETED`, `REJECTED` or `REVIEW_REQUIRED`. Ordinary input/
forecast rejection stores a fixed reason with no queued message. Raw input bytes
and input paths are absent from history. Completed results contain accepted/
duplicate counts, predicted points and `count/mae/rmse`. The queued body is a
generic canonical JSON summary of that result, with a fixed neutral subject.

## Queue behavior

The persistent queue uses run keys and original route/attempt settings. Dispatch
orders eligible keys lexicographically, so order remains stable after restart.
The injected integer tick is monotonic across valid dispatches, from 0 through
1,000,000,000,000. Dispatch limits are integers 1–64. It attempts a selected key
at most once per call; it does not wait for later due times.

The public outbox validates messages/acceptance and classifies one attempt. A
definite retryable non-acceptance uses persisted attempt counts and delays of
1, 2, 4, 8 ticks. Exhausted attempts or tick overflow fail. Permanent rejection
fails immediately. Accepted, failed, delivery-reported and uncertain states do
not automatically resend. Only `PENDING` entries become eligible.

`report_delivery(key, receipt)` requires a matching receipt from `ACCEPTED`.
It records `DELIVERY_REPORTED / CALLER_REPORTED_DELIVERY`; repeated matching
reports are idempotent. It verifies no provider evidence and cannot promote
pending, failed or uncertain state. Snapshots/status omit routes, message bodies,
receipts and results; `result` and `export` explicitly return private run data.

## Python API

From the application directory, with an explicitly selected private `workspace`:

```python
from data_services.service import Stack
from data_services.contracts import fictional_configuration, fictional_input
from data_services.components.outbox import FakeTransport

Stack.initialize(workspace)  # new directory under an existing private parent
with Stack(workspace) as app:
    app.configure(fictional_configuration())
    app.run("sample", "sample_run", fictional_input())
    app.dispatch(FakeTransport(), now=0)
    status = app.status()
```

Contexts must be closed. One synchronous caller is supported. Custom transports
are trusted executable code, not sandboxed providers. Callback mutation/recovery/
close are refused while an attempt runs. Never edit private implementation fields
or journal files to force a result. There is no automatic provider reconciliation,
purge, schema migration, replay reset or semantic deduplication across workspaces.
