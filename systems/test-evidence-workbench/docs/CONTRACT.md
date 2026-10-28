# Cases, trust, plans and evidence

Inputs are UTF-8 JSON with exact declared fields. The decoder refuses duplicate keys, nonfinite values and nesting beyond 64. Input/expected stdout objects additionally have depth 32, numeric magnitude at most 1e12 and canonical integral-float normalization. Expected/observed JSON comparisons use that normalization and preserve boolean/number distinctions. Labels/scripts refuse NUL/other C0 controls except tab/CR/LF and invalid Unicode. Arbitrary captured bytes are retained separately.

## Case and bundle

```json
{
  "format":"outlands-trusted-check-v1",
  "case_id":"sample-total",
  "title":"Fictional sum",
  "script":"import json\nfrom pathlib import Path\nv=json.loads(Path('input.json').read_text(encoding='utf-8'))\nprint(json.dumps({'total':sum(v['values'])}))\n",
  "input":{"values":[3,5]},
  "expected":{"exit_code":0,"stdout":{"total":8},"stderr":""},
  "timeout_ms":3000
}
```

ID matches `[a-z][a-z0-9-]{0,47}`; title is nonempty ≤120 UTF-8 bytes. Python source ≤32768 bytes; input object ≤16384 encoded bytes; expected stdout object ≤8192; stderr ≤2048 UTF-8 bytes; expected exit strict integer 0–255; timeout strict integer 100–5000 milliseconds. Full encoded definition ≤131072 bytes. Stdout must be one object; arrays/scalars, extra JSON, duplicate keys and nonfinite/oversized numbers cannot match.

`import --file` accepts `{"format":"outlands-check-bundle-v1","cases":[CASE,...]}` with 1–20 unique IDs. The entire import is transactional. Identical latest definitions are idempotent; conflicting IDs are refused. There are no path/executable/arguments/environment/credential fields. Python source may still perform arbitrary effects with the operator's permissions, so explicit trust is essential.

`save-case --file` accepts `{"definition":CASE,"expected_sha256":null}` for a new ID, or the exact latest revision SHA-256 for an update. Unchanged content is a no-op; stale hashes fail. Every revision hashes its version, parent and canonical definition. Historical revisions stay immutable. Change the ID and use null expected hash for a fork; trust does not transfer.

## Trust without execution

```json
{"case_id":"sample-total","case_sha256":"CASE_SHA256","expected_version":0,"status":"approved","actor":"sample_operator","note":"Reviewed fictional script and effects","checks":{"code_reviewed":true,"authority":true,"input_reviewed":true,"effects_reviewed":true}}
```

Replace hash placeholders with returned 64-character lowercase hashes; placeholders are not valid values. Status approved/revoked; expected version starts at zero and then matches the latest trust row. Actor ≤80 UTF-8 bytes; note ≤1000, possibly empty. All check values are strict booleans; approval needs all four true. Trust applies to the exact latest whole case revision, not just a source filename. Saving/revoking trust runs nothing. Reviewer/operator labels are unauthenticated local assertions.

## Explicit plan

```json
{"cases":[{"case_id":"sample-total","expected_sha256":"CASE_SHA256","trust_version":1}]}
```

`run --file` validates 1–8 unique current revisions and approved trust versions before materializing any script. An accepted plan captures its case/trust snapshots; later revocation blocks new plans rather than cancelling this accepted plan or its remaining cases. One suite runs at a time. Each check gets a new owned directory with exact `check.py` and `input.json` bytes, verified before launching the current interpreter with fixed isolated/no-site/no-bytecode/UTF-8 arguments. Stdin is noninteractive. No automatic restart/retry occurs.

Only SystemRoot/WINDIR where present and fresh TEMP/TMP are passed as environment values. This avoids inheriting ordinary caller variables but is not credential isolation or a filesystem/network sandbox. The check can access other files or processes with the operator's permissions. Only the immediate child is monitored/cancelled; descendants must be managed by the check itself. Run directories remain private and are retained after errors.

Observed status: completed, timeout, output_limited, cancelled, refused or not_run. Matching requires a completed child plus expected exit, normalized stdout JSON and normalized-line-ending stderr. Capture includes exact base64, bytes/SHA-256, UTF-8 validity, replacement display text, truncation and hash scope. A prefix hash never claims complete output. Counts distinguish planned, attempted, matched, unmatched and not_started. Terminal refusal/timeout evidence can be complete even when a check did not match; cancellation/not_run makes the suite incomplete.

Each artifact hashes a fresh UUID, captured case/trust snapshots and observed results. It is immutable and begins pending review. Store errors can prevent artifact persistence after execution; `saved:false` is not proof nothing ran. No replay is attempted. Runtime durations/captures/paths are private observations, never included in this application's source release.

## Evidence review and private export

```json
{"artifact_id":"ARTIFACT_ID","artifact_sha256":"ARTIFACT_SHA256","expected_version":0,"status":"approved","actor":"sample_reviewer","note":"Failure evidence reviewed; verdict unchanged","checks":{"quality":true,"privacy":true,"rights":true,"context":true}}
```

Use returned IDs/hashes. Status pending/approved/rejected, strict boolean checks, actor/note limits as above and optimistic expected review version. Approval requires complete evidence and all four assertions. It can approve evidence of failed/time-limited checks; it never changes observed verdicts or permits later code execution. Cancelled/incomplete evidence cannot be approved. Every rerun starts a separate pending review.

`export --artifact` requires the artifact's current review to be approved. New-only output contains `run.json`, pinned `cases.json`, `review.json`, exact `captures/CASE_ID/stdout.bin` and `stderr.bin` where captured, an escaped `summary.html`, then `manifest.json` written last. The manifest pins member byte lengths/hashes, artifact/review versions and count/coverage fields, with `public_release_authorized:false`. Partial output remains private; retry uses a new directory. Captured scripts/inputs/bytes may contain secrets, and no redaction/anonymization is implied. Separate source/content-rights review is required before sharing.
