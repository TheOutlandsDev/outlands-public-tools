# Offline Evaluation Metrics Calculator review — 2026-10-25

This batch adds [Offline Evaluation Metrics Calculator](../tools/evaluation-metrics-calculator/README.md),
a fresh Python 3.12+ standard-library implementation from a neutral public
specification. No held AI application, private schema, corpus, conversation,
embedding, model, prompt/response, identity, configuration or actual evaluation
record was selected, read, copied or executed for this addition. Earlier source
and data holds remain. Guarded control-file input handling adapts this
collection's existing public MIT pattern.

## Arithmetic and privacy boundary

One bounded JSON object declares unique neutral class IDs and a square matrix
of nonnegative integer confusion counts. Rows are expected classes and columns
are predicted classes, in the declared class order. This is a single closed
single-label classification table, not multilabel, probabilistic, weighted or
per-person evaluation data.

The calculator reports overall accuracy and per-class support, true positives,
false positives, false negatives, precision, recall and F1. Each ratio carries
an exact unreduced formula numerator/denominator with `DEFINED`, or a null
numerator and zero denominator with `UNDEFINED`. A zero score with a positive
denominator is defined; missing denominators never silently become zero or one.
F1 is computed directly from counts, independently of whether precision or
recall is defined. There is no rounding, smoothing, averaging, threshold,
ranking, winner recommendation or quality-acceptance rule.

The metric definitions and matrix orientation were checked against the official
scikit-learn documentation linked in the README. No scikit-learn code or runtime
dependency is included, and its API/default behavior is not claimed as an
equivalence target. Fixtures and independent arithmetic checks test this
implementation's explicit representation and undefined-result policy.

The raw matrix is not included as a field in the result. That is not a privacy
guarantee: per-class counts can reconstruct a binary matrix, and IDs, supports,
counts and ratios can disclose evaluation structure or performance. Real inputs
and results remain private and need their own review before sharing. This is
not an anonymizer, secret scanner or clearance to publish evaluation data.

There is no model execution, external API, network probe, corpus/prompt/response
or individual-record ingestion, clock lookup, input modification, persistence
or report-file writer. Only the explicitly selected JSON control file is read;
the CLI writes only to stdout. Expected labels and predictions are declared
counts, not verified ground truth or observed model behavior. Arithmetic cannot
establish provenance, representativeness, data rights, leakage prevention,
independence, statistical confidence or model quality.

## Bounds and validation

The input is limited to 64 KiB and 1 to 32 classes. Every cell is an exact
integer from 0 through 1,000,000,000, excluding booleans. The total must be from
1 through 1,000,000,000,000; an empty evaluation is refused. Exact shapes/field
sets, duplicate-key/ID checks and value bounds refuse unsupported input before
arithmetic. Zero-support classes inside a nonempty table remain represented.

The fictional suite covers asymmetric orientation, exact formula components,
independent Fraction-equivalent values, transposition and class permutation,
perfect/zero/undefined metrics, absent classes, resource bounds, deep input
copies, fixed errors, guarded reads and absence of model/network/process/
clock/record/write activity. The local Windows/Python 3.12.7 utility run
discovered 34 methods: 32 passed and two unavailable native link operations
were skipped. The collection run discovered 384 methods: 365 passed and 19
were skipped, with no failures/errors. Skips are not passes.

Independent review passed 547 bounded fictional scenarios, including 500 seeded
matrices checked with exact fractions, transposition and class permutations.
The unit suite also checks 50 small matrices using an expanded fictional
observation oracle. Thirty-one fictional CLI scenarios passed; shipped example
hashes remained unchanged. Ruff checks/formatting and 184 local document checks
passed. No actual model or evaluation data was used. The dedicated workflow runs on Windows
and Ubuntu with Python 3.12/3.13 and checks documentation/JSON syntax.

The reader samples regular-file/single-link and file/ancestor identities with
link/reparse checks before/after a bounded read. Use stable trusted local
files; this is not an atomic snapshot or hostile-filesystem sandbox. Mapped
storage can involve OS network I/O, and byte limits do not interrupt blocked
calls. Formatted reader errors suppress native input detail while retaining
Python source locations.

Selected original source, tests, documentation and fictional examples use MIT
with TheOutlandsDev attribution. No third-party implementation or runtime is
bundled. Private markers, audit output, local evidence and publication receipts
stay outside the repository. Review covers this addition and changed
documentation, not held source/data families, unrelated imports, Git history,
release assets or the full private drive.

The exact 14-file publication set retains one conservative scanner finding:
an invented UNC path in a negative input test, required to fail before
filesystem access. It represents no discovered host or operational record.
The finding has a private file-hash-bound disposition. Scanner status remains
`REVIEW_REQUIRED`, with no detector disabled and zero unresolved findings after
review. There were no private-marker matches or scanner errors.
