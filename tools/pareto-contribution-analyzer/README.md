# Pareto Contribution Analyzer

Rank exact supplied category contributions with deterministic whole-tie-block cumulative shares. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B analyze.py --input examples/input.json
python -B source_check.py
```

Library: `analyze.check(raw_json_bytes)`. Format `outlands-pareto-contributions-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,snapshot}`. Snapshot has `id`, positive `revision`, and 1–512 unique `{id,category,amount}` rows in up to 64 categories. Amount is a nonnegative decimal string with at most six fractional places and value at most one trillion per row. Row order normalizes by ID for the snapshot pin. Category totals sort descending; equal totals share one rank and one cumulative share at the end of the whole tie block. Shares are exact reduced fractions. Zero total returns REVIEW_REQUIRED with undefined shares.

## Limits and privacy

No SQL, data collection, source completeness, cause attribution, or priority selection. Inputs and reports from real work may reveal IDs, totals, shape metadata, or artifact pins; keep them private. A matching hash is not an authenticity or rights proof. [Input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md) give the remaining boundaries.
