# Five-minute workshop: File, backup and workflow

## Goal and input

Review a valid declared backup chain and a deliberately missing parent. All supplied records and files are invented.

## Requirements and one command

Use Python 3.12 or 3.13. Download this family package or the complete toolkit. No pip package, account, model, device or game is required for this workshop. Run from the extracted root, replacing the placeholder with a NEW absolute directory beneath an existing trusted private parent outside the package:

```text
python -B workshops/run.py --family files-workflows --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

## Decision and tradeoff

Validate ancestry before treating a proposed restore order as usable; preserve uncertainty about actual backup contents.

## Expected result and observed evidence

The valid chain is DECLARED_CHAIN_CONSISTENT; the missing parent is REVIEW_REQUIRED. The runner requires these conditions and writes `observed-results.json` only after the checks succeed. A receipt is an observation of this local fictional workflow; do not substitute an expected result for an executed one. Windows/Ubuntu CI runs this workshop from a fresh extraction of its family archive.

## Failure and recovery

An existing destination is refused. Unexpected exits, malformed output or failed expectations leave the newly created scratch tree for inspection and return WORKSHOP_NOT_COMPLETED. Use another new destination after reviewing the cause. Nothing is automatically purged or overwritten.

## Limits

No backup body is opened and no actual restore, retention deletion or storage scan is performed. Keep real inputs, reports, workspaces and backups private.
