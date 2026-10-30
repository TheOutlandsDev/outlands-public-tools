# OUTLANDS | Candidate Evaluation Gate Planner

Compare supplied baseline/candidate predictions on one declared cohort against explicit review criteria without deployment. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic code and newly invented HVAC or game-development examples.

Run from this complete tool directory:

```text
python -B gates.py --input examples/input.json
python -B gates.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out takes an
absolute fresh-report destination outside the source tree under an existing trusted
parent. No private application, original prompts, real records, weights or accounts needed.

## Contract and interpretation

Library `gates.check(raw_json_bytes)`. Input exactly
`{format,labels,cohort,baseline,candidate,policy}`, format
`outlands-candidate-evaluation-gate-v1`. Labels is the shared taxonomy contract.
Cohort rows are `{id,expected_label}`, labels in that taxonomy; at least one case
is required. These expected labels are assertions, not independently verified truth.

Baseline/candidate are exactly `{id,revision,prompt_sha256,decision_policy_sha256,
cohort_sha256,taxonomy_sha256,predictions}`. IDs must match and candidate revision
must be newer (1..1,000,000). Prediction rows are `{id,label}`, one per exact cohort
case ID, label in the taxonomy or null for explicit abstention. Missing rows are
not abstentions. Extra, missing, rejected or conflicting rows withhold all metrics
and gate assessment. Exact duplicate snapshots under one ID never inflate counts.

Recompute cohort_sha256 from sorted normalized embedded `{id,expected_label}` rows,
compact sorted-key ASCII JSON plus LF. Taxonomy pin hashes its normalized object.
Both model headers must exactly match these actual supplied scopes. If the cohort
itself is invalid/empty, its output pin is null, never a qualified partial-cohort pin.
Prompt/policy hashes are declared 64-hex pins; no artifact files are read or authenticated.

Policy is `{minimum_accuracy,maximum_regression,maximum_abstention_increase,
required_prompt_sha256,required_decision_policy_sha256}`. Fractions are exact decimal
strings in [0,1], max six fractional digits. Candidate prompt/policy pins must match
the required pins. Scope/identity/revision/pin mismatches withhold the assessment;
valid metric criteria failures retain the full metrics and failed-criteria list.

Every metric denominator is the entire selected cohort, including abstentions:
correct + incorrect + abstained = cohort, accuracy=correct/cohort and
abstention=abstained/cohort. Ratios preserve numerator/denominator and reduced
exact_fraction strings; deltas may be negative. Candidate accuracy must be >= the
minimum; baseline_accuracy-candidate_accuracy <= maximum_regression; candidate
abstention-baseline_abstention <= maximum_abstention_increase. Equality passes.
No rounding, threshold fitting, significance or holdout-independence claim.

The invented HVAC cohort has baseline 1/3 and candidate 2/3 accuracy, both with
one abstention. A passing result is only eligible_for_manual_review. Permissive
caller criteria can even admit two all-abstaining reports; no quality is implied.
Deploy_authorized, release_performed and training_performed remain false. The
planner neither calls a model nor trains, publishes, promotes or deploys anything.

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
