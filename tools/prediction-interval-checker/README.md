# OUTLANDS | Prediction Interval Coverage Checker

Describe declared interval coverage, width and misses without fitting or calibration claims. Independent CLI/library; Python 3.12/3.13 standard library only,
[MIT licensed](LICENSE), copyright TheOutlandsDev.

## Fictional examples

From this tool directory:

```text
python -B intervals.py --input examples/input.json
python -B intervals.py --input examples/needs-review.json
```

The first returns PASS/exit 0; the second REVIEW_REQUIRED/exit 1. Only invented
records/contracts are supplied. No private original implementation, model,
history, business rule, mapping, source path, user/customer record, credential,
operational configuration or third-party asset is included. Private originals
are not opened, imported, modified or executed. Combined packaging is deferred.


## Supplied interval contract

Library: `intervals.analyze(raw_json_bytes)`. Exact fields:
`format: outlands-interval-coverage-v1`, `nominal_coverage`, `intervals`, `outcomes`.
Nominal coverage is a decimal-string proportion strictly between 0 and 1,
not a percentage. Each interval has id/revision/series/origin/target and decimal
`lower`, `upper`. Require lower <= upper; zero-width intervals are allowed.
The tool never swaps, clips, widens or fits supplied bounds.

Outcomes are `{series, period, value}`, where null means pending. Identity,
revision, duplicate/conflict and complete-coverage rules match those described
in metrics_core.py: one explicit revision per interval ID; exact normalized
duplicates count once; no latest revision selection. Every accepted outcome must
be used. Missing, pending, conflicting, rejected or unused records withhold all
metrics. Output counts use the shared `forecasts` label for interval records.

Coverage includes **both endpoints**: lower <= observed <= upper. Mean width is
sum(upper-lower)/n. Outside distance is lower-observed when below, observed-upper
when above, otherwise zero; mean outside distance includes all n records. Counts
covered/below/above sum to n. Observed coverage, nominal coverage and their signed
difference, widths and distances are exact reduced fractions with decimal-string
numerators/denominators. Overall and per-horizon groups are reported.

The invented example covers two of three outcomes, has mean width 2, mean outside
distance 1/3 and coverage-minus-nominal -2/15. This is descriptive arithmetic on
supplied intervals. It does not establish calibration, confidence/probability
validity, independent observations, representative sampling or future coverage.
Multiple intervals may reuse the same observed outcome and are counted as rows.
No statistical significance test, fitted interval or coverage guarantee is given.


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
