# OUTLANDS | Binary Probability Error Calculator

Calculate exact squared-probability error against supplied binary outcomes with complete cohort accounting. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game metadata; offline and descriptive.

Run from this complete tool directory:

```text
python -B errors.py --input examples/input.json
python -B errors.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No original program, fitted parameter, model, provider, private record or account needed.

## Contract and interpretation

Library `errors.check(raw_json_bytes)`. Input exactly `{format,contract,cohort,predictions,
outcomes}`, format `outlands-binary-probability-error-v1`. Shared binary schemas and
reference rules appear below. Contract declares which label is positive; the other is
negative. No inferred label order, decision threshold, cost weighting or model fitting.

For a known supplied outcome, set y=1 for the declared positive label and y=0 for the
declared negative label. Per-case squared error is exactly `(p-y)^2`. Total is the sum
over the full expected cohort; mean divides by the full selected cohort size. Report
exact rational numerator, denominator and reduced exact_fraction. Do not force a label
from a probability or interpret an unknown label as negative.

Missing prediction/outcome rows and explicit null probability/outcome values return
REVIEW_REQUIRED with complete coverage and available per-case error diagnostics retained.
Missing rows have present=false; explicit unknown values remain present=true. If any
expected case is incomplete, metrics and evaluation_sha256 are null: no intersection
scoring or qualified partial aggregate. No selected cohort gives no zero-denominator
metric. Structural/reference/slot conflicts instead withhold the whole assessment
and all binary scope pins.

If complete, metrics has cases, total_squared_error and mean_squared_error. Reported
scope pins cover actual normalized contract/cohort/prediction/outcome declarations.
evaluation_sha256 hashes `{contract_sha256,cohort_sha256,predictions_sha256,outcomes_sha256}`
only for complete metrics. The invented four-case HVAC fixture has total 3/8 and mean
3/32. These are descriptive errors against asserted outcomes, not proof of truthful
labels, independent evaluation, useful probabilities or real-world model quality.

## Shared schemas, arithmetic and privacy

IDs match `[a-z][a-z0-9_-]{0,47}`; revisions are integers 1..1,000,000. SHA-256 strings
are exactly 64 lowercase hexadecimal characters. No booleans or numeric coercion.
Probabilities/bounds are decimal strings in [0,1] with at most six fractional digits,
no exponent, plus, whitespace or leading integer zeros. Trailing fraction zeros and
negative zero normalize. Floats are never accepted. Exact fractions avoid floating
point and ambient Decimal-context rounding. Output rationals include reduced n/d
strings; input probability schemas still require their documented decimal strings.

The binary contract is `{id,revision,model,model_revision,positive_label,negative_label}`,
with distinct label IDs. Cohort rows are `{id,revision}`, with at least one selected
case. Prediction rows are `{id,case,case_revision,case_sha256,model,model_revision,
probability}`. Probability is an exact unit decimal string or null for explicit unknown.
Outcome rows are `{id,case,case_revision,case_sha256,label}`; label is the declared
positive/negative ID or null for explicit unknown. Prediction/outcome lists may be empty.

Every reference must match the exact selected case revision and full `{id,revision}`
pin. Prediction model/revision must match the actual contract. Unknown labels/references
and stale pins are scope failures, not dropped rows. Different prediction IDs for one
case, or different outcome IDs for one case, are ambiguous even when equal. Structural/
reference/slot failures withhold the binary assessment and all binary scope pins.
Coverage gaps/null values instead retain diagnostics while withholding full metrics.

Identity lists have at most 1,000 raw rows, except bins <=32 and map points <=64.
Identical normalized snapshots under one ID count once plus duplicate_rows. Conflicting
groups withhold every member, including repeated identical members within the conflict.
Each list satisfies `input_rows = accepted_records + duplicate_rows + conflict_rows +
rejected_rows`. Semantic slot issues are separate from structural counts. Fixed issue
codes use one-based logical positions; row 0 is a cohort finding. Rejected values are
omitted. No implicit latest revision, class meaning, outcome, bin or map selection.

Pins hash compact sorted-key escaped ASCII JSON plus LF. Collections sort by ID except
map points sort by their numeric input; label/vector sets and decimals normalize as
documented. input_sha256 hashes exact raw input bytes. Hashes are consistency receipts,
not signatures, authentic evidence, private-data clearance or model-performance proof.

One explicit JSON input <=4 MiB. Duplicate keys, unknown fields, floats/nonfinite
numbers, invalid Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers
outside +/-10^18 are refused. Output is escaped ASCII JSON <=8 MiB. Malformed outer
schemas, header contracts and list bounds are fixed refusals; malformed identity rows
produce REVIEW_REQUIRED with qualified results withheld according to their scopes.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted quiescent storage. Default output is private stdout JSON. Optional
--out takes an absolute fresh destination under an existing trusted external parent
outside source; no overwrite, parent traversal or mkdir. Failed writes may retain
partial/unconfirmed output: inspect privately and choose a fresh path. Windows inherits
parent ACLs without a confidentiality guarantee. Shell redirection lacks these guards.
Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption. Errors omit supplied
paths/values. These guards do not sandbox hostile concurrent processes.

No model/provider calls, weights, raw dataset/prompt collection, fitting, calibration
application, threshold selection, inference, clock, command execution, URI/include
following, environment expansion or target updates. Only invented HVAC/game fixtures.
Keep actual inputs, fitted maps and reports private. These tools do not anonymize data,
verify outcome truth/independence, establish confidence/calibration or grant publication
rights. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
