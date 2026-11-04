# Kanban Move Planner

Preview one pinned card move against declared transitions and target WIP capacity. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B move.py --input examples/input.json
python -B source_check.py
```

Library: `move.check(raw_json_bytes)`. Format `outlands-kanban-move-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,board,board_sha256,move}`. The planner recomputes the complete board pin and baseline validity. Move selects one card, destination column, and zero-based insertion position. A blocked card, disallowed cross-column edge, or full target requires review without a candidate pin. Valid moves reindex affected columns and produce a new revision/pin; same-column reorder is allowed. No work item is changed.

## Limits and privacy

No live synchronization, automatic dispatch, task completion decision, or authority to update a board. Real input and reports may expose table cells, board structure, IDs or pins; keep them private. Hash pins establish byte identity only. See [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
