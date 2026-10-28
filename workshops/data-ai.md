# Five-minute workshop: Data and AI tools

## Goal and input

Compute metrics from invented confusion counts, then inspect undefined denominators. All supplied records and files are invented.

## Requirements and one command

Use Python 3.12 or 3.13. Download this family package or the complete toolkit. No pip package, account, model, device or game is required for this workshop. Run from the extracted root, replacing the placeholder with a NEW absolute directory beneath an existing trusted private parent outside the package:

```text
python -B workshops/run.py --family data-ai --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

## Decision and tradeoff

Preserve exact ratios and explicit undefined metrics without turning fixture scores into model-quality claims.

## Expected result and observed evidence

Accuracy is 17/20; the second fixture requires review with five undefined metrics. The runner requires these conditions and writes `observed-results.json` only after the checks succeed. A receipt is an observation of this local fictional workflow; do not substitute an expected result for an executed one. Windows/Ubuntu CI runs this workshop from a fresh extraction of its family archive.

## Failure and recovery

An existing destination is refused. Unexpected exits, malformed output or failed expectations leave the newly created scratch tree for inspection and return WORKSHOP_NOT_COMPLETED. Use another new destination after reviewing the cause. Nothing is automatically purged or overwritten.

## Limits

No model, corpus, training run, prediction service or label truth is evaluated. Keep real inputs, reports, workspaces and backups private.
