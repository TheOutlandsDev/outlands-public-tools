# Grouped Aggregate Reconciler

Independent offline MIT source tool by TheOutlandsDev. Uses bounded strict JSON declarations and fictional examples only. Run `python -B aggregates.py --input examples/input.json` from this folder. Library: `aggregates.check(raw_bytes)`.

Format: `outlands-grouped-report-aggregates-v1`. Definitions have exact `id`, `revision`, `columns`, `group_by`, and `measures`. Supported measure operators are `count_rows`, `count_values`, `sum`, `min`, and `max`. The latter three accept integer or decimal fields. Nulls are excluded from value measures; an all-null numeric result is null. Groups have one to four nondecimal key fields. Inputs are bounded to 4 MiB and 512 rows per snapshot. Hash pins bind the normalized embedded definitions and snapshots.

The tool only checks supplied rows and declarations. It does not run SQL, access a database or network, establish source completeness, or change a target. Reports contain supplied IDs and values: keep real inputs and reports private.
