# OUTLANDS | Forecast Error Analyzer

Match supplied forecasts and outcomes with complete accounting and exact error summaries. Independent CLI/library; Python 3.12/3.13 standard library only,
[MIT licensed](LICENSE), copyright TheOutlandsDev.

## Fictional examples

From this tool directory:

```text
python -B forecast_errors.py --input examples/input.json
python -B forecast_errors.py --input examples/needs-review.json
```

The first returns PASS/exit 0; the second REVIEW_REQUIRED/exit 1. Only invented
records/contracts are supplied. No private original implementation, model,
history, business rule, mapping, source path, user/customer record, credential,
operational configuration or third-party asset is included. Private originals
are not opened, imported, modified or executed. Combined packaging is deferred.


## Forecast/outcome contract

Library: `forecast_errors.analyze(raw_json_bytes)`. Exact input fields:
`format: outlands-forecast-errors-v1`, `forecasts`, `outcomes`. Each forecast has
`id`, `revision`, `series`, `origin`, `target`, `predicted`. IDs/series are symbolic
identifiers; revision is an exact integer 1..1,000,000. Origin/target are ordinal
integers 0..1,000,000,000 with horizon `target-origin` in 1..365. Predicted is a
bounded decimal string. These ordinals do not establish when a forecast was made
or whether it used future information.

One explicit revision per forecast ID is permitted in a comparison. Repeated
identical normalized records count as duplicates, not extra score weight.
Changed content or multiple revisions under that ID conflict; all members of
the group are withheld. The tool never guesses a latest revision. Multiple
distinct forecast IDs may refer to the same observed series/period, including
different horizons; they contribute separately, without independence claims.

Each outcome is `{series, period, value}`; value is a decimal string or null
(pending). Outcome identity is series/period. Conflicting values, including
pending plus observed for the same identity, are withheld. Every supplied
accepted outcome must be used; missing/pending matches and unused outcomes
require review. One bad row, conflict or coverage issue withholds **all** overall
and per-horizon metrics. No partial cohort is silently scored. Exact duplicates
alone do not block scoring. At least one forecast is required; outcomes may be
empty, in which case the unresolved cohort requires review.

Error is predicted minus observed. For n qualified forecast rows, mean error is
sum(error)/n; MAE is sum(abs(error))/n; MSE is sum(error squared)/n. RMSE is the
square root of MSE, approximated to 12 decimal places using a local 60-digit
decimal context and round-half-even. All other ratios are exact reduced integer
fractions represented as **numerator/denominator decimal strings**, so large
bounded squared errors remain interoperable without integer-parser overflow.
These are equally weighted forecast-row summaries, not model selection,
uncertainty estimates, real accuracy evidence or proof of prediction provenance.

The invented errors are 2, -2 and 1: mean 1/3, MAE 5/3, MSE 3 and RMSE
approximately 1.732050807569. Horizon groups remain explicit. No forecasts are
generated or trained here. The existing public baseline evaluator remains
unchanged; integration tests score its actual predictions on invented integers.


## Shared parsing and file limits

At most 1,000 rows per supplied list. Each list's input rows equal accepted unique
records + duplicate rows + conflicting rows + rejected rows. Conflicting groups
include all members, including repeated variants. Row positions are one-based
logical list positions. Malformed row structures/values produce fixed rejection
codes without echoing supplied values; malformed/ambiguous top-level JSON fails
entirely. No silent truncation or partial derived summaries after an issue.

Identifiers match `[a-z][a-z0-9_-]{0,47}`. Decimal values are strings, absolute
value <= 1,000,000,000,000, at most six fractional places; no exponent, whitespace,
leading plus, leading zero ambiguity, nonfinite value or numeric/boolean coercion.
Negative zero and trailing decimal zeros normalize for duplicate comparisons.
JSON refuses duplicate keys, floats/nonfinite numbers, invalid Unicode, excess
depth (32)/nodes (100,000), strings over 4,096 characters and unknown fields.
The selected file is at most 4 MiB. Reports serialize as ASCII JSON, at most 8 MiB.
Counts remain JSON integers; exact fractions use decimal-integer strings.

See [checked Windows/POSIX I/O](IO-SAFETY.md), [origins](ORIGINS.md) and
[validation](VALIDATION.md). The CLI reads only the explicit ordinary single-link
input. No tree discovery, environment expansion, service, network, clock,
process execution or source-system query. Inputs/parents must be trusted and
quiescent; guards do not promise hostile-filesystem containment.

Default output is private stdout JSON. `--out` exclusively creates a new external
private report under an existing parent, outside the source tree. No directory
creation or overwrite. Failed writes can retain partial/unconfirmed output;
inspect privately and select a new path. Windows ACLs inherit from the parent;
no confidentiality guarantee. Shell redirection does not inherit --out guards.
Source pins, body-value omission and JSON escaping do not anonymize data, verify
rights or authorize publication. Aggregates, policy labels, IDs and hashes can
still disclose private information. No real-world effectiveness is qualified.

Exit 0 PASS; 1 REVIEW_REQUIRED; 2 fixed refusal; 130 interruption. Argument errors
omit supplied paths/values. These are offline descriptive tools, not deployment,
production acceptance, automatic remediation or statistical reliability proof.

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
