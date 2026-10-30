# OUTLANDS | Score & Abstention Policy Checker

Reproduce decisions from recorded scores and explicit abstention policy without inference or confidence claims. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and newly invented HVAC or game-development examples.

Run from this complete tool directory:

```text
python -B scores.py --input examples/input.json
python -B scores.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out takes an
absolute fresh-report destination outside the source tree under an existing trusted
parent. No private application, original prompts, real records, weights or accounts needed.

## Contract and interpretation

Library `scores.check(raw_json_bytes)`. Input exactly `{format,policy,cases}`,
format `outlands-score-abstention-v1`. Policy is exactly
`{id,revision,labels,minimum_score,minimum_margin,tie_policy}`. Revision is
1..1,000,000, labels has 2..32 unique IDs. Thresholds and scores are exact decimal
strings in [0,1], with optional minus only for normalized negative zero, at most
six fractional digits, no exponent/plus/whitespace/leading integer zeros. Trailing
fraction zeros and negative zero normalize. Fractions avoid floating point and
ambient Decimal-context rounding. Scores need not sum to one; no probabilities,
softmax, calibration or real-world confidence are inferred.

Case is exactly `{id,scores,declared_label}`. Scores has exactly one `{label,value}`
for every policy label. Declared_label is a policy label or null, where null means
an explicitly recorded abstention, not an omitted prediction. Cases must be nonempty.
Missing/duplicate/unknown score labels, bad decimals, unknown declared labels or
conflicting/rejected rows withhold all decisions and summary.

Rank scores by exact value. Margin is highest minus second highest, including
zero on a tie. Equality meets each threshold; lower score or margin requires
abstention. Tie_policy is explicitly abstain (any top tie abstains) or lexical
(smallest tied label may win, subject to score/margin criteria). No input-order
tie breaking. Report all abstention reasons. A required, correctly declared
abstention can PASS; no label is forced. Wrong declared decisions return
REVIEW_REQUIRED while retaining all computed/declaration diagnostics.

Results contain computed/declared labels, agreement, highest-scoring label set,
exact normalized top score/margin, tie flag and abstention reasons. Summary counts
cases, abstentions and mismatches. Policy pin covers the normalized complete policy.
PASS is reproduction of that declared policy, not label truth, confidence,
inference, authorization or good policy selection.

The HVAC example has two selected labels and one abstention. An additional
`examples/game-events.json` fixture classifies an invented NPC event and preserves
an explicit tied-score abstention. No game assets, real telemetry or models.

## Shared declarations, CLI and privacy limits

IDs and labels match `[a-z][a-z0-9_-]{0,47}`. Taxonomy is exactly
`{id,revision,labels}`, with revision integer 1..1,000,000 and 1..32 unique labels,
normalized by sorting. There is no inferred label meaning. Every pin uses normalized
compact sorted-key escaped ASCII JSON plus LF, except input_sha256 which covers
the exact raw input bytes. Pins are consistency receipts, not signatures or truth.

Identity-snapshot lists (mappings, cases, cohort and predictions) have at most 1,000
rows. Identical normalized snapshots count once plus duplicate_rows. Conflicting groups withhold every member, including
repeated identical members within that group. Each record list satisfies
`input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows`.
Other structured lists use their explicit schema bounds/uniqueness rules above.
Source references do not reclassify structurally accepted rows. Fixed diagnostics
use 1-based logical positions; row 0 denotes a cohort/contract issue. Rejected values
are omitted. No latest version, prediction, prompt or mapping is selected implicitly.

One explicit JSON input <=4 MiB. Duplicate keys, unknown fields, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers
outside +/-10^18 are refused. Integer fields reject booleans/numeric strings; decimal
values are accepted only in their stated string schemas. Output is escaped ASCII
JSON <=8 MiB. Malformed outer contracts, prompt/policy schemas and list bounds refuse
entirely. Valid scoped findings retain or withhold results as documented above.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted quiescent storage; no hostile-process filesystem sandbox or OS
quota. Default output is private stdout JSON. Optional --out takes an absolute fresh
report destination under an existing trusted external parent outside the source tree.
No overwrite, parent traversal or mkdir. Failed writes may retain partial/unconfirmed
output; inspect privately and choose a fresh path. Windows inherits parent ACLs without
a confidentiality guarantee. Shell redirection lacks --out protections. Exit 0 PASS,
1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption; errors omit supplied paths/values.

No network/provider/model calls, weights, corpus collection, database, live clock,
command execution, URI/include following, environment expansion or directory discovery.
Actual prompts, labels, scores, judgments, hashes and reports can be private. These
tools are not anonymizers, prompt-safety checks, rights checks or independent authority/
quality verifiers. Keep actual inputs/reports private. Only newly invented HVAC and
game-event fixtures are included. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
