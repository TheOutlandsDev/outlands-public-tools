# OUTLANDS | Context Manifest Checker

Check supplied document pins, revisions and dependency relationships offline. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic implementation and invented fixtures; no private originals reused.

Run from this complete tool directory:

```text
python -B context_manifest.py --input examples/input.json
python -B context_manifest.py --input examples/needs-review.json
```

The second command intentionally returns REVIEW_REQUIRED (exit 1).
Optional `--out ../fictional-new-report.json` requires an existing trusted parent
outside the source collection and a destination that does not exist.

## Contract and interpretation

Library: `context_manifest.check(raw_json_bytes)`. Exact top-level fields:
`format: outlands-context-manifest-v1`, `documents`, `relationships`.
Each relationship is `{dependent: reference, prerequisite: reference}`.
A reference is exactly `{id, revision, sha256}`. Both must resolve to the supplied
document's exact ID, selected revision and actual text pin. Self-dependencies,
missing/stale/wrong pins and cycles require review. Relationship identity is the
ordered dependent/prerequisite ID pair; changed pins under one pair conflict.
Identical repeats count once. Up to 1,000 relationship rows, no hidden imports.

The graph means only caller-declared dependencies. Kahn ordering takes the sorted
ready set at each wave; it is deterministic and does not execute a prerequisite.
No relationships is valid. All documents, including disconnected ones, appear
in the order. A cycle, invalid row or unresolved reference withholds the entire
manifest, canonical manifest pin and dependency order; no partial plan is emitted.
The path-free manifest contains document IDs/revisions/hashes/character and UTF-8
byte counts plus resolved relationships. Its pin hashes canonical ASCII JSON
with sorted keys, compact separators and one trailing LF (toolkit.encode).
Raw JSON formatting changes the input pin, not the canonical manifest pin.
The example orders garden, meadow, orchard; orchard depends on garden.
Pins bind supplied text bytes after JSON decoding/UTF-8 encoding; they do not
establish source-file bytes, ownership, freshness or trustworthy relationships.

## Shared input, accounting and privacy limits

Documents are explicit embedded JSON rows `{id, revision, sha256, text}`. At most
100 document rows; one explicitly selected revision per ID. ID matches
`[a-z][a-z0-9_-]{0,47}`; revision is integer 1..1,000,000. SHA-256 is exactly 64
lowercase hexadecimal characters and must match text.encode('utf-8'). No file
path, URI, directory discovery, include, environment expansion or external fetch.
Text is 1..4,096 Unicode code points; CR/LF/tab allowed; other C0/C1/DEL controls
refused. Unicode scalar content is checked by the JSON decoder; no normalization.
Empty/whitespace usefulness is not assessed. JSON escaping does not execute text.

Rows with identical identity/content count as one accepted record plus duplicate
rows. Conflicting identity groups withhold every member, including identical
repeats within a conflicting group. A malformed row is rejected with a fixed
code and 1-based logical row position. Each list accounts for every row:
input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows.
Cross-reference errors concern accepted rows and do not reclassify row counts.
No accepted documents requires review. Any issue globally withholds derived
manifests/plans/metrics/evidence; raw accounting and fixed issue positions remain.
Top-level malformed/ambiguous JSON or policy/limit errors refuse entirely.

The input is at most 4 MiB; JSON refuses duplicate keys, floats/nonfinite numbers,
invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and integers outside
+/-10^18. Unknown fields are refused. Output is escaped ASCII JSON <=8 MiB.
Input SHA-256 pins exact raw JSON, while document pins cover decoded UTF-8 text.
Hashes do not authenticate a source, establish rights or anonymize content.
Reports omit bodies but IDs, revisions, hashes, relationships, offsets and metrics
can disclose private details. Real inputs and reports must remain private.

Only the explicitly selected ordinary single-link input is read. The CLI reuses
pinned public [Windows/POSIX file guards](IO-SAFETY.md). Trusted, quiescent parents
are required; hostile local-process/filesystem containment is not promised.
Default output is private stdout JSON. `--out NEW_EXTERNAL_REPORT` exclusively
creates a new file under an existing parent outside the source tree; no overwrite
or directory creation. Failed writes may retain partial/unconfirmed output;
inspect privately and select a fresh path. Windows inherits parent ACLs; no
confidentiality guarantee. Shell redirection lacks the --out protections.

Exit 0 PASS; 1 REVIEW_REQUIRED; 2 fixed refusal; 130 interruption. Argument and
I/O errors omit supplied paths/values. No network, clock, model loading, private
source-system access, process execution, automatic training or target updates.
Native report creation is the sole optional write; input systems are unchanged.
Source pins and a structural PASS do not authorize sharing an input/report.

See [origins](ORIGINS.md) and [validation boundaries](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
