# OUTLANDS | Fixed-Bin Reliability Reporter

Describe supplied probability/outcome fractions in explicit fixed bins without fitting, choosing bins or establishing calibration. Independent MIT CLI/library for Python 3.12/3.13, standard library only.
Fresh generic logic and newly invented HVAC/game metadata; offline and descriptive.

Run from this complete tool directory:

```text
python -B bins.py --input examples/input.json
python -B bins.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
No original program, fitted parameter, model, provider, private record or account needed.

## Contract and interpretation

Library `bins.check(raw_json_bytes)`. Input exactly `{format,contract,cohort,predictions,
outcomes,bins}`, format `outlands-reliability-bins-v1`. Binary schemas/reference rules
are shared with the error calculator. No outcome intersection scoring or partial
aggregate: missing/unknown evidence withholds all bin metrics and the report pin.

Bins is at most 32 raw identity rows `{id,lower,upper}`, exact unit decimal strings.
At least one selected bin is required. Bounds normalize, and bins sort numerically by
lower/upper then ID. Require strictly positive widths, no overlaps and exact domain
coverage from zero to one. Gaps, overlaps and nonpositive widths return REVIEW_REQUIRED
with bin diagnostics retained but metrics/report_sha256 null. Nested overlaps are
analyzed against the covered union, without inventing gaps inside a wider interval.
Conflicting/rejected bin rows withhold bin_assessment and bins_sha256 entirely.

Membership is [lower,upper), with probability one included in the final bin ending at
one. Valid bins assign every complete expected case exactly once. Per bin report case
IDs, count, positives, exact mean probability, supplied positive-outcome fraction,
signed gap = positive fraction - mean probability, and absolute gap. Empty bins are
visible and informational: all rates/gaps are null, never 0/0; they do not imply
adequate coverage. There is no hidden minimum count or significance threshold.

Weighted absolute bin gap is exactly sum over nonempty bins of
`(bin cases / full cohort cases) * absolute gap`. This is a defined descriptive
quantity, not confidence, significance or calibration proof. It changes with caller
bin choices; bins are never fitted or selected. The three-bin HVAC fixture has gap
1/4; a single [0,1] bin on those same declarations has gap 1/8.

Binary scope pins remain independent when a bin contract is invalid. Conversely, a
valid bin contract/pin may remain visible when binary references fail. bins_sha256
receipts structurally valid normalized bin rows, including logical partition findings;
it does not qualify a partition. report_sha256 is issued only for complete metrics
and valid bins, hashing `{evaluation_sha256,bins_sha256}`. assessment describes binary
evidence coverage; bin_assessment describes the separate partition. Calibration,
label truth and cohort independence remain unverified in every case.

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
