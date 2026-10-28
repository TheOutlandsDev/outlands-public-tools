# Five-minute workshop: Document and media inspection

## Goal and input

Create an invented VPD structure, inventory three references and check two mapped placeholders. All supplied records and files are invented.

## Requirements and one command

Use Python 3.12 or 3.13. Download this family package or the complete toolkit. No pip package, account, model, device or game is required for this workshop. Run from the extracted root, replacing the placeholder with a NEW absolute directory beneath an existing trusted private parent outside the package:

```text
python -B workshops/run.py --family documents-media --workspace NEW_ABSOLUTE_SCRATCH_DIRECTORY
```

## Decision and tradeoff

Keep explicit mapping and metadata availability separate from media integrity.

## Expected result and observed evidence

Three references, two metadata checks and NO_MAPPING_FINDINGS; report hashes match the manifest. The runner requires these conditions and writes `observed-results.json` only after the checks succeed. A receipt is an observation of this local fictional workflow; do not substitute an expected result for an executed one. Windows/Ubuntu CI runs this workshop from a fresh extraction of its family archive.

## Failure and recovery

An existing destination is refused. Unexpected exits, malformed output or failed expectations leave the newly created scratch tree for inspection and return WORKSHOP_NOT_COMPLETED. Use another new destination after reviewing the cause. Nothing is automatically purged or overwritten.

## Limits

The two empty placeholders are not playable media; editor compatibility and playback remain unverified. Keep real inputs, reports, workspaces and backups private.
