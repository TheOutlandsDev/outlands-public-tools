# HTML Table Revision Comparator

Compare two pinned selected HTML grids by dimensions, cell text, header flags, and span anchors. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B compare.py --input examples/input.json
python -B source_check.py
```

Library: `compare.check(raw_json_bytes)`. Format `outlands-html-table-revision-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,baseline,candidate}`. Each side declares `{html,table,grid_sha256}` and is independently parsed by the same bounded grid rules. Supplied grid pins must match the recomputed grid. Equal grids PASS; changed coordinates and dimension changes return REVIEW_REQUIRED. Candidate HTML is never written or applied.

## Limits and privacy

No rendered-layout comparison, semantic importance ranking, browser execution, source completeness, or target modification. Real input and reports may expose table cells, board structure, IDs or pins; keep them private. Hash pins establish byte identity only. See [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
