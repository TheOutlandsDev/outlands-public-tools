# OUTLANDS | Retrieval Evaluation Calculator

Calculate exact retrieval metrics from supplied rankings and binary judgments. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic implementation and invented fixtures; no private originals reused.

Run from this complete tool directory:

```text
python -B retrieval.py --input examples/input.json
python -B retrieval.py --input examples/needs-review.json
```

The second command intentionally returns REVIEW_REQUIRED (exit 1).
Optional `--out ../fictional-new-report.json` requires an existing trusted parent
outside the source collection and a destination that does not exist.

## Contract and interpretation

Library: `retrieval.calculate(raw_json_bytes)`. Exact top-level fields:
`format: outlands-retrieval-evaluation-v1`, `documents`, `queries`, `k`.
k is an exact integer 1..100. Each query has exactly `{id, ranked, relevant}`;
ranked/relevant are ordered lists of exact `{id, revision, sha256}` document
references, each at most 100 entries. All references, even rankings below k,
must resolve to the actual selected document text and revision. A repeated
document ID within either list is rejected, including differing pins/revisions.
The same document may appear in both lists. Different queries may reuse documents.

Query identity is ID. Exact identical repeats count once; changed ranking order
or content under one ID conflicts. Relevant-list order also participates in
snapshot identity, although its metric meaning is a binary set. No automatic
latest revision, deduplication within rankings, inferred negatives or relevance
labels are supplied by this tool. At most 100 query rows. Zero queries or a query
with zero relevance judgments requires review and withholds every metric.
An empty ranking with nonempty relevance is valid and scores zero.

For the first min(k,returned) ranks, hits are exact matching relevant references.
Precision@k = hits/k even when fewer than k results were supplied. Recall@k =
hits/total declared relevant. Reciprocal rank@k = 1/first relevant rank, or zero
when none occurs by k. Macro precision, macro recall and mean reciprocal rank
give equal weight to unique accepted queries. All ratios are reduced exact
decimal-string numerator/denominator pairs; no floating point arithmetic.
The example at k=2 gives macro precision 1/2, macro recall 3/4 and MRR 3/4.
Any rejected/conflicting row or reference issue withholds all per-query/global
metrics. Unused documents are allowed. No retrieval, embedding, search service,
ranking generation, graded relevance, statistical inference or actual model
quality is qualified. Supplied judgments may be incomplete or incorrect.

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
