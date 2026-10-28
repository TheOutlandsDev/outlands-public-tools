# Five-minute workshop: Desktop diagnostics

## Goal and input

Export two deterministic samples from the explicit Resource Monitor demo provider. All supplied records and files are invented.

## Requirements and one command

Use Python 3.12 or 3.13. Download this family package or the complete toolkit. No pip package, account, model, device or game is required for this workshop. Run from the extracted root, replacing the placeholder with a NEW absolute directory beneath an existing trusted private parent outside the package:

```text
python -B workshops/run.py --family desktop-diagnostics --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

## Decision and tradeoff

Mark warm-up values as unavailable and label fictional data instead of collecting host metrics.

## Expected result and observed evidence

Mode is demo; there are two samples and the second fictional CPU value is 24.6. The runner requires these conditions and writes `observed-results.json` only after the checks succeed. A receipt is an observation of this local fictional workflow; do not substitute an expected result for an executed one. Windows/Ubuntu CI runs this workshop from a fresh extraction of its family archive.

## Failure and recovery

An existing destination is refused. Unexpected exits, malformed output or failed expectations leave the newly created scratch tree for inspection and return WORKSHOP_NOT_COMPLETED. Use another new destination after reviewing the cause. Nothing is automatically purged or overwritten.

## Limits

No live metric, device, capture session, browser dashboard or background server is started. Keep real inputs, reports, workspaces and backups private.
