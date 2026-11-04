# Pareto Cutoff Planner

Apply an explicit caller cutoff to exact ranked contribution blocks without splitting ties. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B plan.py --input examples/input.json
python -B source_check.py
```

Library: `plan.check(raw_json_bytes)`. Format `outlands-pareto-cutoff-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,snapshot,ranking_sha256,cutoff}`. Snapshot has the same bounded contract as the analyzer; the planner recomputes the complete ranking and refuses a stale or false ranking pin. Cutoff is an exact decimal string in [0,1] with at most six fractional places. Zero selects no categories. For positive cutoffs, include whole ranked tie blocks until the cumulative share meets the cutoff. Report selected IDs, covered share, boundary rank and exact whole-block overshoot. A 100% cutoff may omit zero-contribution categories once full share is reached. Zero total returns REVIEW_REQUIRED without a selection.

## Limits and privacy

No fitted or universal threshold, action authority, or claim that the supplied cohort is complete. Inputs and reports from real work may reveal IDs, totals, shape metadata, or artifact pins; keep them private. A matching hash is not an authenticity or rights proof. [Input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md) give the remaining boundaries.
