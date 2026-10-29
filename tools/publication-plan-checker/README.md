# OUTLANDS | Publication Plan Checker

Check an exact reviewed artifact selection without copying or publishing. Independent CLI/library; Python 3.12/3.13 standard-library runtime,
[MIT licensed](LICENSE), copyright TheOutlandsDev.

## Fictional walkthrough

From this tool's directory:

```text
python -B publication.py --plan examples/plan.json --manifest examples/manifest.json --review examples/review.json --item reconciliation examples/reconciliation.json --item result examples/result.json
```

The invented example returns PASS/exit 0. Source texts and JSON fixtures are
synthetic, with fixed invented identifiers and dates; no private original code,
records, templates, source mappings, operational configuration, user data, paths,
credentials or third-party assets are included. Original applications are not
opened, imported, modified or executed. Combined packages/browser apps are deferred.


## Exact selection and review declarations

Library: `publication.check(plan_raw, manifest_raw, review_raw, selected_buffers)`.
The manifest is the builder's bare `outlands-run-artifact-manifest-v1`. The plan
is `outlands-publication-plan-v1` with plan/run IDs, raw manifest/review SHA-256
pins and `items`: unique `{id, sha256, public_name}` objects. Only those selected
artifact buffers are supplied/read; unselected manifest artifacts are not opened.
There is no path or destination root in the plan and no directory traversal.

Review: `outlands-publication-review-v1` with review/run IDs, manifest pin and an
exact matching selected item set. Each item includes ID/hash/public_name,
`decision` (allow/hold), `rights_reviewed`, `privacy_reviewed`, `context_reviewed`.
Assertions are exact booleans. All must be true and decision allow for plan
consistency. A hold cannot be cleared by true assertions. A renamed output,
changed selection, altered artifact or stale review/manifest pin requires review.
Review identity is a symbolic label, not an authenticated person or signature.

Public names are proposed portable ASCII basenames (1..80 characters), unique
ignoring case. Paths, separators, alternate streams, traversal, trailing dots,
reserved Windows device names and encoded/Unicode names are refused. No output
artifact with that name is created. The checker does not redact source paths
embedded inside artifact bytes, detect secrets, determine IP rights or establish
whether review declarations are true. Artifact roles do not grant permissions.

PASS means **declared plan consistency only**. The report always retains
`publication_authorized: false`, `privacy_independently_verified: false`,
`rights_independently_verified: false`, `target_changes_performed: false`.
It never copies, renames, moves, deletes, sends, uploads or publishes artifacts.
The optional private JSON report is the only output file. A real publication
requires a separate review of the exact selected contents and an authorized
publication action. This module cannot replace that review or sanitize real data.


## Shared limits, I/O and privacy

At most 16 selected artifacts, 4 MiB each and 16 MiB combined. IDs match
`[a-z][a-z0-9_-]{0,47}`; hashes are lowercase SHA-256. Manifest declared totals
also cannot exceed 16 MiB. JSON refuses duplicate keys, floats, nonfinite numbers,
invalid Unicode, excess depth (32)/nodes (100,000), strings over 4,096 characters,
integers beyond the supported bounds and unknown contract fields.

CLIs read explicit regular single-link files using the pinned public Windows/POSIX
guards. No path is read from a manifest, review, receipt or artifact body. Use
trusted quiescent files/parents. Selections are sequential bounded snapshots,
not an atomic capture or a guarantee against a hostile/privileged filesystem.
See [I/O boundaries](IO-SAFETY.md), [origins](ORIGINS.md), [validation](VALIDATION.md).

Output is private ASCII JSON on stdout, or `--out` creates a **new external report**
under an existing parent. Source-tree output and overwrite are refused; no
directory is created. Failed writes can retain partial/unconfirmed output. No
automatic cleanup or same-path retry; choose a new path after private inspection.
Windows inherits parent ACLs, without a confidentiality guarantee. Shell stdout
redirection does not inherit these guards. Reports, symbolic IDs, public-name
proposals, counts, hashes and relationships can still disclose private information.
Hash agreement and path omission do not anonymize an artifact or authorize sharing.

Exit codes: 0 PASS; 1 REVIEW_REQUIRED; 2 fixed refusal; 130 interruption. Errors
omit supplied values and paths. No source/environment discovery, live query,
process execution or target action occurs. Read each tool's specific evidence
limits above. Parser bounds are not OS resource quotas or an execution sandbox.

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
