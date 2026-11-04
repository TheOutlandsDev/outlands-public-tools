# ISO Week Claim Checker

Check complete supplied ISO week labels against one pinned date-only cohort. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B claims.py --input examples/input.json
python -B source_check.py
```

Library: `claims.check(raw_json_bytes)`. Format `outlands-iso-week-claims-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,snapshot,cohort_sha256,claims}`. The analyzer recomputes the full cohort pin. Up to 512 unique claims declare `{id,iso_year,iso_week}`. Missing, unexpected, or mismatched claims return REVIEW_REQUIRED; duplicate identities and impossible ISO week numbers are refused. The checker does not fill missing claims or infer a timezone.

## Limits and privacy

No source completeness or authenticity proof, scheduling policy, timestamp conversion, or operational update. Real inputs and reports can expose IDs, dates, headers, counts and hashes; keep them private. Hash pins establish byte identity only. See [Python ISO calendar](https://docs.python.org/3.12/library/datetime.html), [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
