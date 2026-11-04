# CSV Column Profiler

Summarize bounded raw CSV headers, blank counts, cardinalities, and cell lengths without mapping. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B profile.py --input examples/input.json
python -B source_check.py
```

Library: `profile.check(raw_json_bytes)`. Format `outlands-csv-column-profile-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,csv_text}`. Text is at most 4096 UTF-8 bytes. Strict Python CSV parsing supports 1..32 unique symbolic headers and 1..512 rectangular data rows. Blank means exactly an empty cell; no trimming, type inference, header detection, or field-map selection occurs. Per-column counts include blank, nonblank, distinct nonblank, minimum and maximum nonblank character lengths. The profile hash covers summary shape and counts, while the separate CSV hash covers exact text bytes.

## Limits and privacy

No data type inference, disclosure protection, source completeness, row identity, import, or raw cell values in the report. Real inputs and reports can expose IDs, dates, headers, counts and hashes; keep them private. Hash pins establish byte identity only. See [Python CSV reader](https://docs.python.org/3.12/library/csv.html), [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
