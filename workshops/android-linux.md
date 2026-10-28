# Five-minute workshop: Android and Linux inspection

## Goal and input

Compare comment-only and changed fictional Linux fstab records. All supplied records and files are invented.

## Requirements and one command

Use Python 3.12 or 3.13. Download this family package or the complete toolkit. No pip package, account, model, device or game is required for this workshop. Run from the extracted root, replacing the placeholder with a NEW absolute directory beneath an existing trusted private parent outside the package:

```text
python -B workshops/run.py --family android-linux --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

## Decision and tradeoff

Match unique mount targets while preserving field differences and order changes.

## Expected result and observed evidence

Comment-only comparison is NO_SCOPE_FINDINGS; changed options/order requires REVIEW_REQUIRED. The runner requires these conditions and writes `observed-results.json` only after the checks succeed. A receipt is an observation of this local fictional workflow; do not substitute an expected result for an executed one. Windows/Ubuntu CI runs this workshop from a fresh extraction of its family archive.

## Failure and recovery

An existing destination is refused. Unexpected exits, malformed output or failed expectations leave the newly created scratch tree for inspection and return WORKSHOP_NOT_COMPLETED. Use another new destination after reviewing the cause. Nothing is automatically purged or overwritten.

## Limits

No mount, flash, device connection, actual configuration change or successful boot is claimed. Keep real inputs, reports, workspaces and backups private.
