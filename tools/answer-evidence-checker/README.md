# OUTLANDS | Answer Evidence Checker

Check explicit citation pins and quoted spans without factual-truth claims. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic implementation and invented fixtures; no private originals reused.

Run from this complete tool directory:

```text
python -B evidence.py --input examples/input.json
python -B evidence.py --input examples/needs-review.json
```

The second command intentionally returns REVIEW_REQUIRED (exit 1).
Optional `--out ../fictional-new-report.json` requires an existing trusted parent
outside the source collection and a destination that does not exist.

## Contract and interpretation

Library: `evidence.check(raw_json_bytes)`. Exact top-level fields:
`format: outlands-answer-evidence-v1`, `documents`, `answers`.
Each answer is exactly `{id, text, citations}`; text is nonempty, at most 4,096
code points, subject to the same controls as document text. Each citation has
exactly `{source, start, end, quote}`. Source is `{id, revision, sha256}` and
must resolve exactly. Start/end are code-point offsets, 0<=start<end<=document
length, end exclusive; booleans and empty spans are refused. Quote must exactly
equal document.text[start:end], with no Unicode or newline normalization.

At most 100 answer rows and 100 citations per answer. Citation identity within
an answer is source ID/revision/pin/start/end. Duplicate spans are rejected,
including duplicates with conflicting quoted text. Different spans may overlap.
Answer identity is ID; identical normalized snapshots count once; changed answer
text, citation order or citation values under that ID conflict. One selected
snapshot per answer, no event replay or automatic latest matching. Empty answers,
missing citations, mismatched quote/pin/revision, invalid/conflicting rows or
unresolved references withhold the entire evidence list. Unused documents allowed.

The report contains answer hashes/character counts and checked reference/span/
quote-hash records; no answer body, document body or quote is emitted. It checks
only structural citation integrity. It does not parse inline citation markers,
associate citations with individual claims, require quoted text in the answer,
establish entailment, completeness, factual truth, safety or source authority.
An unrelated answer with an exact source quote can therefore PASS structure;
`claim_support_verified` and `factual_truth_verified` always remain false.
The example checks [0,17) of the invented garden document. No answer is generated
and no model/service is called. A PASS is never publication approval.

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
