# Kanban Board State Checker

Check a bounded declared board for column positions, WIP limits, and transition references. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B board.py --input examples/input.json
python -B source_check.py
```

Library: `board.check(raw_json_bytes)`. Format `outlands-kanban-board-state-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,board}`. A board has symbolic ID, positive revision, 1..32 unique columns and 0..512 unique cards. Each column declares nullable WIP limit and distinct allowed next columns. Each card declares column, zero-based position, and blocked boolean. Positions must be contiguous and unique within each column. Exceeded WIP, duplicate positions, and gaps return REVIEW_REQUIRED with column counts. The normalized board hash includes all declarations.

## Limits and privacy

No live board read, task payload inspection, work completion inference, authorization, or mutation. Real input and reports may expose table cells, board structure, IDs or pins; keep them private. Hash pins establish byte identity only. See [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
