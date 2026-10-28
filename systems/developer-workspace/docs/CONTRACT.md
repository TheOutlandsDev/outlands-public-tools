# Neutral projects and private requests

All inputs use UTF-8 JSON and exact declared fields. Outer JSON refuses duplicate keys, nonfinite numbers and nesting beyond 64. Text preserves its exact supplied UTF-8 representation and newlines. File order is canonicalized by path; revision hashes include version, parent hash and canonical definition. Limits are bytes, not just characters.

## Project import

```json
{
  "format": "outlands-developer-project-v1",
  "project_id": "sample-project",
  "title": "Fictional project",
  "files": [{"path": "src/sample.py", "content": "value = 1\n"}]
}
```

An import is an explicit text bundle, not an inventory of an automatically traversed directory. IDs match `[a-z][a-z0-9-]{0,47}`. Titles are nonempty and at most 120 UTF-8 bytes. File count 1–200; each content at most 65536 UTF-8 bytes, total at most 1048576. NUL/other C0 controls except tab/CR/LF and invalid UTF-8/surrogates are refused. Empty file content is allowed.

Paths have 1–8 slash-separated ASCII segments, each 1–64 characters, total at most 240. Segments start alphanumeric and continue alphanumeric, underscore, hyphen or dot; trailing dots, hidden names, Windows device basenames, separators/drive/stream syntax and case-insensitive path or file/directory collisions are refused. Directory names `node_modules`, `__pycache__`, `runtime`, `private`, `outputs` are refused. Accepted suffixes: `.py`, `.pyw`, `.json`, `.xml`, `.rdl`, `.sql`, `.md`, `.txt`, `.js`, `.mjs`, `.cjs`, `.html`, `.css`. Suffix acceptance is not privacy clearance.

## Edit and delete

Save this request to a new explicit inbox JSON file; replace `EXPECTED_PROJECT_SHA256` with the exact hash returned by `show`. The placeholder is not an accepted hash.

```json
{"project_id":"sample-project","expected_sha256":"EXPECTED_PROJECT_SHA256","path":"src/sample.py","content":"value = 2\n","operation":"save"}
```

`edit --file inbox/edit.json` uses the latest expected project hash, creates a full immutable revision and returns its new hash/version. Identical content is a no-op. A new path adds a file. Delete uses `"operation":"delete","content":null`; deleting a missing or last file is refused. There is no in-place overwrite of earlier source. A new import cannot replace an existing ID with different content.

## Validate

```json
{"project_id":"sample-project","expected_sha256":"EXPECTED_PROJECT_SHA256"}
```

`validate --file inbox/validate.json` captures the latest pinned revision and waits for its owned child. API validation starts asynchronously and exposes an opaque job ID; only that owned job may be cancelled. One job is active at a time; at most 20 recent in-memory jobs remain. Results include per-file relative paths/hashes, pass/fail/unchecked status, fixed diagnostic codes and limited parser locations. Diagnostics omit raw exception messages, source lines, process IDs and runtime paths. Python offsets and XML columns retain their parser conventions; do not compare them as a universal column scheme.

Completed checks report counts, `passed`, `all_files_checked` and `code_executed:false`. A syntax/preflight success never means runtime behavior was tested. Unsupported text formats remain unchecked. Cancellation/budget/refusal produces a saved non-approvable artifact where persistence succeeds; a store error can instead return `saved:false`. Each run has a distinct UUID in its hashed payload, so review never transfers automatically between reruns. Interrupted jobs are not replayed.

## Review

```json
{"artifact_id":"RETURNED_ARTIFACT_ID","artifact_sha256":"RETURNED_ARTIFACT_SHA256","expected_version":0,"status":"approved","actor":"sample_reviewer","note":"Fictional static review; runtime unverified","checks":{"quality":true,"privacy":true,"rights":true,"context":true}}
```

Replace ID/hash placeholders with returned values. Status is pending/approved/rejected. Expected review version starts at zero, then matches the latest saved row. Labels at most 80 UTF-8 bytes and notes at most 1000; the note may be empty. Check values are strict booleans. Approval requires all four assertions and completed checks with no failed files. It can include explicitly unchecked files after manual review. Approval does not authenticate a reviewer or grant sharing rights. Stale version/hash submissions fail without discarding browser notes.

## Private export

`export --artifact RETURNED_ARTIFACT_ID` requires the latest review of that artifact to be approved. It exports exactly the pinned historical project revision, not whichever editor/latest revision happens to be visible. A new random report directory contains `project-source.zip` followed by `receipt.json`. Failures retain partial private output for inspection; retries use a new directory and never replace files.

The ZIP has `source/` text files, `project.json`, `validation.json`, `review.json` and `manifest.json`. The manifest pins every other member's bytes/SHA-256, exact source/artifact/review versions, unchecked coverage and `public_release_authorized:false`. ZIP metadata uses fixed 2020 dates and regular 0644 entries; supplied contents/notes still remain private. The receipt pins the ZIP itself. Metadata hashes are integrity checks rather than signatures or secret redaction. There is no automatic upload, Git operation, test execution or publication step for caller projects.
