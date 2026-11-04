# ISO Week Cohort Analyzer

Assign supplied date-only rows to exact ISO weeks and count each week. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B analyze.py --input examples/input.json
python -B source_check.py
```

Library: `analyze.check(raw_json_bytes)`. Format `outlands-iso-week-cohort-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,snapshot}`. Snapshot has a symbolic ID, positive revision, and 1..512 unique `{id,date}` rows. Dates are canonical YYYY-MM-DD in Gregorian years 1900..2099. The tool reports each row's ISO year-week/weekday and sorted weekly counts plus Monday/Sunday dates. The snapshot pin normalizes row order. ISO years can differ from calendar years at the boundary.

## Limits and privacy

No timestamps, timezone inference, live calendar, missing-date interpolation, data completeness, or source update. Real inputs and reports can expose IDs, dates, headers, counts and hashes; keep them private. Hash pins establish byte identity only. See [Python ISO calendar](https://docs.python.org/3.12/library/datetime.html), [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
