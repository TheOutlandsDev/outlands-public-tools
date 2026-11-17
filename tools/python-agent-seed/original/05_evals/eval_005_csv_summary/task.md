# Eval 005: CSV summary refactor

## Task

Refactor `starter/csv_summary.py` to produce a safe, typed CSV summarizer.

## Requirements

- Function name: `summarize_scores`.
- Accept `str | Path`.
- Read UTF-8 CSV with headers `name` and `score`.
- Return `ScoreSummary(count: int, average: float, maximum: int)` as a frozen dataclass.
- Ignore blank rows.
- Raise `ValueError` for missing columns, non-integer scores, or no valid rows.
- Use only the standard library.
