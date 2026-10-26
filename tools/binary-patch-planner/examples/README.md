# Fictional patch examples

Run `python -B examples/generate.py --output NEW_ABSOLUTE_DIRECTORY` from the
module folder. Its parent must exist, and the destination must be new. The
generator creates four invented fixtures; it does not inspect your machine.

| Generated file | Purpose | Planner exit |
| --- | --- | --- |
| `source.bin` | Sixteen fictional bytes, `ORCHARD-DEMO-v1` followed by LF. | Input only |
| `verified-plan.json` | Two nonoverlapping equal-length edits produce `ORCHARD-TEST-v2` followed by LF. | 0 |
| `unexpected-plan.json` | Source hash matches, but one expected slice is deliberately wrong. | 1 |
| `overlap-plan.json` | Two edit ranges overlap. The plan is invalid. | 2 |

Preview writes reports only. Explicitly add `--apply-output NEW_ABSOLUTE_FILE`
with the verified plan to create a separate sixteen-byte candidate. Retain the
original and use a new report directory for every command. Existing outputs
are never overwritten. The README has full PowerShell/POSIX command examples.

No fixture is a game asset, executable, firmware image or real patch recipe.
Do not attach actual binaries/plans or identifying reports to public issues.
