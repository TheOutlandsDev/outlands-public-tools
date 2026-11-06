# Document context and answer evidence methodology

These tools review supplied documents, plans, rankings and citations offline.
Select an explicit text snapshot and its revision before interpreting a result.

| Term | Plain-language meaning | Exact meaning here |
| --- | --- | --- |
| Document snapshot | One selected version of supplied text | Embedded id, integer revision, text and SHA-256 of text.encode('utf-8'); one selected revision per ID. No file or URI is followed. |
| Context manifest | A bounded list of documents and declared dependencies | Exact document references and a path-free manifest. All documents, including disconnected ones, appear in deterministic prerequisite-first waves. |
| Dependency | A caller-declared prerequisite relationship | Ordered dependent/prerequisite reference pair. Self-dependencies, cycles and unresolved/stale pins withhold the whole manifest and order. No task is executed. |
| Chunk | A planned window within the selected source text | Exact start/end, source pin and substring hash. Code-point width and overlap define reproducible windows; the report omits substring bodies. |
| Offset and overlap | Where a window starts/ends and repeats source characters | Python Unicode code points with an exclusive end, not bytes, UTF-16 units, graphemes or model tokens. Width 5 and overlap 2 over ABCDEFGHIJK gives [0,5), [3,8), [6,11). |
| Ranking | An ordered supplied list of document references | Exact ID/revision/text-pin references; all references, including ranks below k, must resolve. The calculator performs no search. |
| Relevance judgment | The caller's selected relevant documents | A binary set for scoring, supplied explicitly. Relevant-list order still contributes to record identity. Correctness/completeness of judgments is unverified. |
| Precision@k | How many selected top results are relevant | Exact hits/k, even when fewer than k results are supplied. Missing results do not shrink the denominator. |
| Recall@k | How much declared relevant material appears by k | Exact hits divided by the supplied relevant-document count. No relevance judgments withholds every metric. |
| Reciprocal rank@k and MRR | How early the first relevant result appears | 1/first relevant rank through k, otherwise zero. MRR averages accepted unique queries equally; ratios use reduced integer strings. |
| Citation evidence | A supplied answer's explicit source/span records | Exact source reference, nonempty [start,end) code-point span and matching quote. The checker does not associate citations with individual claims. |
| Pin and receipt | A content binding and its consistency report | Document/quote pins hash decoded text encoded as UTF-8. Manifest/policy pins hash sorted-key compact escaped ASCII JSON plus LF. Input pin hashes exact raw JSON. These are distinct domains, not signatures or anonymization. |
| PASS | The selected declaration rules were met | Manifest consistency, complete bounded chunk planning, valid supplied retrieval scoring, or exact citation integrity. Factual truth and claim support remain unverified. |
| REVIEW_REQUIRED | The selected scope has findings | CLI exit 1; every row is accounted for, while all derived manifest/plan/metrics/evidence for that tool are withheld. Chunk policy/pin and fixed diagnostics can remain visible. |
| Fixed refusal | The input cannot be assessed | CLI exit 2; malformed outer JSON, unknown fields, invalid policy or exceeded parser limits produce a fixed refusal rather than a partial result. Library operations raise the same refusal. |
| Independent package | One tool can be installed and called alone | Its own versioned wheel, CLI, embedded fictional demo and exact documented Python operation. The four-tool collection pins exact member versions. |

## Apply the method

1. Select at most 100 explicit document rows, each with 1..4,096 code points,
   one revision and a matching UTF-8 text pin. Preserve Unicode and newlines
   exactly; review rights and privacy separately.
2. Validate the declared dependency graph. Plan bounded character windows
   separately: every source code point is covered, overlap is intentional,
   and exceeding the global 4,096-chunk cap withholds the whole plan.
3. Supply exact rankings and binary relevance judgments. Interpret precision,
   recall and reciprocal rank under the explicit k and selected query cohort.
   An empty ranking with nonempty judgments scores zero; absent judgments
   withhold scoring. This distinction is visible in the installed exercise.
4. For an explicitly selected window, construct a citation using the original
   source snapshot and exact substring. Check its quote and pin. A structurally
   valid citation can accompany an unrelated answer; entailment and factual
   truth require separate review.

The [installed example](../integrations/document-evidence/exercise.py) connects
all four tools using invented text, demonstrates exact overlap windows and
retrieval fractions, checks a citation against the selected window hash, and
retains failed dependency/quote/revision cases without partial conclusions.
The [component guide](../integrations/document-evidence/components.json) gives
people and AI callers exact formats, imports, operation names, result fields
and example paths. Source guides retain complete accounting and I/O rules.

Reports omit bodies, but IDs, pins, offsets, counts and relationships can still
disclose private information. Actual documents, prompts, answers, judgments,
corpus exports and reports stay private. Passing a check does not approve sharing.
