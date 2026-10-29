# Pinned release workflow contract

Requests are strict bounded UTF-8 JSON (optional BOM). Duplicate keys, nonfinite numbers, depth above 64 and unexpected schema fields are refused. Canonical JSON means Python `json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')`. Dictionary order/formatting is normalized; list order remains significant. SHA-256 pins are lowercase 64-character hex; artifact IDs are lowercase 32-character hex.

## Capture

The exact job envelope is `{expected_head,actor,reason,request}`. Initial head is 64 zeroes; later writes require the latest journal head. Actor (160 UTF-8 bytes) and reason (400 bytes) are local assertions, not authenticated identity. A candidate request has exactly:

| Field | Meaning |
| --- | --- |
| `parent_id` | Null or registered candidate ID; metadata lineage only |
| `label` | Nonempty literal text, at most 120 UTF-8 bytes |
| `source` | Explicit directory selector below `inbox/`, inside this private instance |
| `manifest` | `{schema_version:1,inventory:[{path,size,sha256},...]}` |
| `manifest_sha256` | Independently trusted SHA-256 of the **canonical manifest object** |
| `dependency_lock` | Null or exact `{path,text}`, matching one listed payload file |
| `launcher` | Exact `{schema_version:1,executable,working_directory,arguments}` |

The included [release 1](../examples/capture-v1.json) and [release 2](../examples/capture-v2.json) are complete invented requests. Their included pins demonstrate mechanics; obtaining a hash from the same unchecked package does not authenticate it. The app checks equality with the supplied pin, not its origin, signature or trustworthiness.

Manifest paths are portable relative ASCII slash names: 1–8 segments, at most 240 bytes total, each segment starts alphanumeric/underscore then uses alphanumeric/underscore/dot/hyphen, with no hidden initial dot, trailing dot, traversal, drive/stream syntax, backslash or Windows device names. File/directory collisions and case collisions are refused. Each package must contain exactly the listed files and their parent directories; extras, including empty directories, are refused. Limits: 1–64 files, 64 KiB per file, 2 MiB total. Only bytes are captured; executability, permissions, filesystem metadata and application consistency are not preserved or established.

Sources must be explicitly placed below the private inbox. Selectors use `inbox/` plus 1–7 segments with bounded ASCII letters/digits/underscore/dot/space/hyphen; parent traversal, device names, trailing dots/spaces, drive/stream syntax and links are refused. No package/archive extraction, PATH discovery or live installation scanning exists. Captured snapshots are copies in fresh UUID directories; changes to the original inbox do not rewrite them. Recapture with a new reviewed manifest/pin for changed inputs.

`dependency_lock.text` is UTF-8 literal text at most 64 KiB. Its exact byte size/hash must match the named manifest entry. The unchanged public narrow lock parser accepts sorted canonical names and supported version text, with one adjacent SHA-256 per package. It rejects unsupported grammar, duplicate packages, noncanonical names, controls and missing hashes. Only the one explicitly declared lock is parsed; undeclared locks are ordinary payload bytes. Comparisons preserve version-text/hash-only/add/remove/unchanged distinctions without semantic upgrade ranking, downloads, resolution, artifact verification, compatibility or advisory checks. Comment/format-only changes can leave declarations equal while the payload file remains `REPLACE`.

The launcher is data. Its entry must be a listed file, working directory `.` or an implied listed parent directory. Up to 16 literal arguments of 240 bytes each are accepted, with no control characters. No executable-format/runtime acceptance, command generation or execution is performed. Entry and launcher declarations are pinned with the candidate descriptor; the manifest pin alone does not independently authenticate launcher metadata.

## Comparison and plan

Comparison job request: exact `{baseline_id,baseline_sha256,candidate_id,candidate_sha256,policy}`. Pins refer to canonical candidate descriptors, which include label, inventory, lock declarations and launcher. A descriptor pin never substitutes for payload validation; reads reverify payload bytes and metadata. Baselines/candidates must be registered snapshots; they are not inspected live targets.

Policy has exactly five boolean assertions: `backup_confirmed`, `target_stopped_confirmed`, `readiness_confirmed`, `allow_removals`, `dependency_reviewed`. The first three false assertions always block. Candidate omissions require `allow_removals`; changed/added/removed declared locks require `dependency_reviewed`. All are operator assertions. Case-only path changes (including parent directories with different child filenames) and file/directory transitions across snapshots remain blocked regardless of policy.

File comparison reports the union of both inventories: `ADD`, `REMOVE`, `REPLACE` or `UNCHANGED`. Omissions are visible, never deleted. Status is `REVIEW_REQUIRED` when blockers exist, otherwise `READY_FOR_MANUAL_REVIEW`. Launcher changes and dependency coverage remain explicit. No policy performs a backup, verifies stopped state/readiness or establishes target safety.

Plan job request: exact `{comparison_id,comparison_sha256}`. It creates an immutable plan against that comparison's original pair, with five manual checkpoints and baseline/candidate-only rollback name lists. Every checkpoint stays `NOT_PERFORMED`; rollback backup verification and restore remain false. A baseline snapshot is not proof of an application-consistent backup or actual current installation. Plans always deny execution and public-release authorization.

## Approval, revocation and handoff

`review` uses exact `{expected_head,actor,reason,plan_id,plan_sha256,approve,checks}` without a nested request. `approve` is boolean; `checks` has exactly `quality,privacy,rights,context` booleans. Approval requires four exact true values and a ready, registered, untampered plan. Revocation accepts boolean assertions without requiring them true. The latest typed review is authoritative; every decision remains in history. Reapproval is an explicit new event.

Approval applies only to that immutable plan/snapshot pair. New captures/comparisons/plans never inherit it, including identical content. Changed snapshot bytes block inspection/approval/export; this is verification at use, not a live watcher or permanent memory of earlier tampering. Explicit historical use remains possible for its exact original bytes and current approval. Revocation blocks future exports and cannot recall external copies.

Export uses exact `{expected_head,actor,reason,plan_id,checks}` with four true review assertions and current approval. It rechecks the entire upstream chain before creating a fresh directory. Seven pinned files are `baseline.json`, `candidate.json`, `comparison.json`, `plan.json`, `approval.json`, `export-review.json`, `journal.json`; `manifest.json` is written last as the eighth file. Payload files are excluded; private selectors, lock text, arguments, filenames/hashes and notes remain in the full journal. Export is not publication clearance or an execution adapter. A failed export can leave a partial directory; no automatic adoption or deletion occurs.

## Store and capacity

One trusted operator/process owns a private instance. Exact SQLite schema, append-only triggers and typed hash-chain replay recompute descriptors/comparisons/plans and validate review transitions without file I/O or target execution during replay. On normal use, artifact reads verify completed registrations, markers, canonical bytes and payload hashes. A marker alone does not register an artifact.

Limits: 64 jobs, 256 events, 256 KiB comparison/plan report, 4 MiB guarded request/output file and 64 MiB index. Starting a job reserves a terminal-event slot. Reviews consume events; no retention, purge, migration or import/restore feature exists. Index backups include requests, decisions and lock text but omit all payload/artifact/inbox/handoff files. They cannot restore a complete instance. Near capacity, full-journal exports can exceed the output limit and be refused with partial evidence retained. Disk use for repeated explicit exports/backups is not globally quota-controlled.
