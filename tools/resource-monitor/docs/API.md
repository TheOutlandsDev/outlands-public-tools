# Local API and sample format

The listener is `127.0.0.1` only. Use the actual port printed at startup. Every
API request requires `X-Outlands-Token` with the random capability from the
current startup URL. The token is not accepted in query strings. Static assets
are public to the local listener but contain no token or metrics.

`Host` must exactly equal `127.0.0.1:PORT`. An `Origin`, if supplied, must exactly
equal the server's `http://127.0.0.1:PORT`. No CORS grant, external host, forwarded
host or redirect is supported. This is a local capability guard, not user-account
authentication or a guarantee against malicious local software.

| GET route | Result |
| --- | --- |
| `/api/history` | Schema/mode/capacity/interval/error state and retained samples. |
| `/api/history?limit=N` | Latest N samples; one decimal value, 1 through configured capacity. |
| `/api/snapshot` | Schema/mode and latest sample, or `null` before a completed reading. |
| `/api/export.json` | Current full retained history with an attachment filename. |
| `/api/export.csv` | Same history in a fixed CSV column format. |

API operations are read-only. Unsupported methods are refused; there is no
command execution, process control, system configuration or remote-stop route.
Requests have a 2,048-character target limit, 8-KiB header budget, 16 concurrent
handler limit and two-second socket-operation timeout. A slow peer can consume
time across operations; this is not a hard total-request deadline. Shutdown
closes active listener connections.

History is a bounded in-memory object. The following example is fictional:

```json
{
  "schema": 1,
  "mode": "demo",
  "capacity": 120,
  "interval_seconds": 1.0,
  "sampling_error": false,
  "samples": []
}
```

Each sample has `schema`, `mode`, `sequence`, UTC `timestamp`, monotonic-derived
`elapsed_seconds`, `cpu_percent`, `memory`, `network` and fixed `issues` labels.
Memory contains `percent`, `used_bytes`, `total_bytes`. Network contains
`received_bytes`, `sent_bytes`, `received_bps`, `sent_bps`, and `counter_reset`.
Rates are bytes per second. Samples do not contain packet addresses, hostnames,
usernames, interface names, process names or command lines.

Unavailable numbers are JSON `null`, not a negative marker or false zero. The
first CPU sample is warm-up; rate calculation requires two valid counter
samples and positive elapsed time. A lower/reset counter yields a gap and a
new baseline. A failed overall sample sets `sampling_error`; prior history can
remain visible and is explicitly stale. JSON output refuses NaN/Infinity.

The dashboard polls once per second without overlapping its own requests.
Its charts show the latest 60 samples, while an export contains all retained
server samples. Pausing one browser view does not stop the server sampler.
No automatic log/database/export exists. API exports are at most 1 MiB.
