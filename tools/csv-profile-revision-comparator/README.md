# CSV Profile Revision Comparator

Compare two recomputed, pinned raw CSV profiles for header and count changes. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B compare.py --input examples/input.json
python -B source_check.py
```

Library: `compare.check(raw_json_bytes)`. Format `outlands-csv-profile-revision-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,baseline,candidate}`. Each side declares bounded CSV text and a profile SHA-256 recomputed by the standalone profiler rules. Differences in row count, header membership/order, blank/nonblank counts, distinct nonblank counts, or length bounds return REVIEW_REQUIRED. Equal profiles PASS even if underlying CSV text differs; the separate exact CSV hashes remain visible and record equality is explicitly unverified.

## Limits and privacy

No cell-level diff, semantic drift inference, type inference, source completeness, or target modification. Real inputs and reports can expose IDs, dates, headers, counts and hashes; keep them private. Hash pins establish byte identity only. See [Python CSV reader](https://docs.python.org/3.12/library/csv.html), [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
