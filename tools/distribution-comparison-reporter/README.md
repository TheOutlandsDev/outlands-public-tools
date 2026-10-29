# OUTLANDS | Distribution Comparison Reporter

Compare fixed-bin marginal distributions with explicit missing and outside buckets. Independent CLI/library; Python 3.12/3.13 standard library only,
[MIT licensed](LICENSE), copyright TheOutlandsDev.

## Fictional examples

From this tool directory:

```text
python -B distributions.py --input examples/input.json
python -B distributions.py --input examples/needs-review.json
```

The first returns PASS/exit 0; the second REVIEW_REQUIRED/exit 1. Only invented
records/contracts are supplied. No private original implementation, model,
history, business rule, mapping, source path, user/customer record, credential,
operational configuration or third-party asset is included. Private originals
are not opened, imported, modified or executed. Combined packaging is deferred.


## Fixed-bin marginal comparison

Library: `distributions.compare(raw_json_bytes)`. Exact fields:
`format: outlands-distribution-comparison-v1`, `fields`, `reference`, `current`.
Declare 1..16 unique fields. Numeric fields have name/kind/boundaries with 2..33
strictly increasing decimal-string boundaries; categorical fields have
name/kind/categories with 1..32 unique symbolic identifiers. The same supplied
policy is used for both sides; nothing is fitted from reference/current values.
The canonical normalized policy has its own hash, separate from the raw input pin.

Each row has `id`, `values`, with exactly the declared field names. Each value
is a decimal string for numeric, a symbolic identifier for categorical, or null.
Row identity is id independently within each side. Normalized duplicates count
once; conflicting groups withhold every member. Rejected/conflicting rows or
an empty accepted side withhold **all** comparisons. Side counts retain all rows.

Numeric bins are [edge_i, edge_i+1), except the final bin includes its upper
endpoint. Separate below/above/missing buckets account for all other valid values.
Categorical buckets use declared order plus explicit unknown/missing buckets;
unknown observed labels are counted without being echoed. Missing/outside/unknown
values are valid accounting categories and are never silently dropped. Bucket
counts sum to accepted unique records on each side.

For each field, p/q are reference/current bucket shares. Delta is q-p and total
variation distance is one half of sum(abs(q-p)), including all buckets. Fractions
are exact reduced decimal-integer string pairs. The invented example has distance
1/2 for both fields. Equal all-missing cohorts have zero bucket distance; that
does not establish useful or complete data. These are **marginal**, not joint,
distributions; correlation or relationship shifts may be missed.

No hypothesis test, p-value, automatic drift threshold, cause attribution,
sampling/feature provenance verification, model update or operational decision.
Comparisons describe the declared binning and supplied records only. Policy labels,
boundaries, counts, shares and fingerprints can remain private information.


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
