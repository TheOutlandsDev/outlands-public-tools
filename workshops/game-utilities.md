# Five-minute workshop: Game utilities

## Goal and input

Import a fictional profile, preview activation, activate its managed copy and deactivate it. All supplied records and files are invented.

## Requirements and one command

Use Python 3.12 or 3.13. Download this family package or the complete toolkit. No pip package, account, model, device or game is required for this workshop. Run from the extracted root, replacing the placeholder with a NEW absolute directory beneath an existing trusted private parent outside the package:

```text
python -B workshops/run.py --family game-utilities --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

## Decision and tradeoff

Only change the manager-owned workspace; preserve imported source bytes and retained history.

## Expected result and observed evidence

Eight commands run; orchard becomes active, then active_profile is null and original hashes still match. The runner requires these conditions and writes `observed-results.json` only after the checks succeed. A receipt is an observation of this local fictional workflow; do not substitute an expected result for an executed one. Windows/Ubuntu CI runs this workshop from a fresh extraction of its family archive.

## Failure and recovery

An existing destination is refused. Unexpected exits, malformed output or failed expectations leave the newly created scratch tree for inspection and return WORKSHOP_NOT_COMPLETED. Use another new destination after reviewing the cause. Nothing is automatically purged or overwritten.

## Limits

No real game, mod loader, game directory or gameplay compatibility is involved. Keep real inputs, reports, workspaces and backups private.
