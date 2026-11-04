# HTML Table Grid Extractor

Extract one explicitly selected bounded HTML table into a rectangular cell and span grid. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B extract.py --input examples/input.json
python -B source_check.py
```

Library: `extract.check(raw_json_bytes)`. Format `outlands-html-table-grid-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,html,table}`. `html` is a UTF-8 string of at most 4096 bytes. Only direct `table`, `tr`, `td`, and `th` tags and cell `rowspan`/`colspan` attributes are supported; text outside cells must be whitespace. Select table index 1..16 explicitly. The complete document is parsed, and the selected table must form a rectangular grid with at most 128 rows, 32 columns, 1024 source cells, and 256 characters per cell. Spanned cells retain one-based anchor coordinates. The grid hash pins selected decoded content and geometry.

## Limits and privacy

No browser rendering, CSS, scripts, external resources, malformed-HTML repair, visibility inference, table identity, or source completeness proof. Real input and reports may expose table cells, board structure, IDs or pins; keep them private. Hash pins establish byte identity only. See [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
