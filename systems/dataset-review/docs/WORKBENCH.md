# Workbench contracts

An explicit private workspace has `workspace.json` format
`outlands-dataset-workbench-v1`, `database/review.sqlite3`, `inbox`, `exports`,
`backups` and an owned empty `.session-lock`. The canonical legacy database schema
and `user_version` remain unchanged. No migration runs.

`status` returns a logical content hash over ordered groups, aliases, records,
provenance and review rows. It includes reviewer notes/times; it is private metadata,
not authentication or an attestation. A review or group/split/provenance change
invalidates earlier request pins. HTTP JSON refuses duplicate keys, nonfinite values,
depth above 64, unknown fields and bodies above 4 MiB. Legacy JSONL parsing remains
unchanged; these are separate contracts.

New CLI mutation commands take `--request` with these exact JSON shapes:

```json
{"expected":"CURRENT_STATE_SHA256","file":"inbox/sample-records.jsonl"}
```

`review`:

```json
{"expected":"CURRENT_STATE_SHA256","id":"RECORD_SHA256","decision":"approved","actor":"sample_reviewer","note":"Fictional evidence review","checks":{"quality":true,"privacy":true,"rights":true,"context":true}}
```

`export` and `backup`:

```json
{"expected":"CURRENT_STATE_SHA256"}
```

Replace hash placeholders with current returned hashes. Reviewer and note bounds
remain 128/4096 characters with nonblank values; approval needs four exact booleans.
All decisions/notes remain local assertions. Neither review nor export publishes.

The API binds only to literal `127.0.0.1`, checks a single exact Host and session
token, and requires a single exact Origin, JSON Content-Type, bounded decimal length
and no transfer encoding for POST. Duplicate headers/query parameters and unknown
fields are refused. Scripts use a nonce CSP, text rendering and no external assets.
There are no arbitrary file reads, output paths, SQL, command or process routes.
Shutdown is available even when a write reply is uncertain. Owned HTTP workers drain
before the session marker is released.

Exports contain `approved.jsonl` and final `manifest.json`, with exact byte counts,
SHA-256, store pin and `public_release_authorized:false`. Replacing existing output
is refused. Backups use fresh SQLite destinations, checked schemas, logical head
agreement and readback hashes; only database content is included. Failed new outputs
remain private. Fixed errors omit exception values and absolute paths. A response
or post-operation failure does not imply rollback; refresh and inspect before retry.

View bounds: 2,000 groups/records, 4,000 aliases, 20,000 provenance and 5,000 review
rows; record pages are at most 250 entries, search at most 200 characters. Interface
imports/reviews validate view limits before commit. The legacy CLI retains its prior
contract. One operator and stable trusted storage are required. Stop every interface
before legacy CLI, source-store copy or recovery. No universal privacy detector,
hostile concurrency boundary, real rights clearance or restore automation is added.
