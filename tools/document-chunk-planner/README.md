# OUTLANDS | Document Chunk Planner

Plan deterministic character windows with exact source pins and offsets. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic implementation and invented fixtures; no private originals reused.

Run from this complete tool directory:

```text
python -B chunks.py --input examples/input.json
python -B chunks.py --input examples/needs-review.json
```

The second command intentionally returns REVIEW_REQUIRED (exit 1).
Optional `--out ../fictional-new-report.json` requires an existing trusted parent
outside the source collection and a destination that does not exist.

## Contract and interpretation

Library: `chunks.plan(raw_json_bytes)`. Exact top-level fields:
`format: outlands-document-chunks-v1`, `documents`, `policy`.
Policy is exactly `{max_chars, overlap_chars}`: integer width 1..4,096 and overlap
0..width-1; booleans are refused. Start at zero, take [start,min(start+width,n)),
stop when end==n, otherwise advance start=end-overlap. Documents are sorted by ID;
chunk index starts at one independently per document. Every supplied code point
is covered; overlap is intentional and never contributes extra source length.
No normalization, paragraph/sentence/token splitting or model tokenizer is used.
Combining sequences and words can cross boundaries. Offsets count Python Unicode
code points, not UTF-8 bytes, UTF-16 code units or displayed graphemes. End is exclusive.

Each planned window records ID, revision, source_sha256, index, start/end,
characters, UTF-8 bytes and SHA-256 of the exact substring encoded as UTF-8.
Document bodies and chunk text are omitted. Policy has a separate canonical pin.
Maximum 4,096 chunks globally, checked before allocating output windows; exceeding
it requires review and emits no partial plan. Any document rejection/conflict
also withholds all chunks/count. The policy and its pin remain visible on review.
`ABCDEFGHIJK`, width 5, overlap 2 yields [0,5), [3,8), [6,11), with bodies
ABCDE, DEFGH, GHIJK used only in fictional tests. No chunks are written as files,
no embeddings/indexes are created and no token-budget or model-quality guarantee
is made. Only a requested fresh JSON report can be written.

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
