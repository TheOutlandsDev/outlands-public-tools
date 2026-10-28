# Backup & Recovery: prove the restore, preserve the source

An original public demonstration using invented files. This is a personal,
AI-assisted project, not employer software or an operational backup service.
Connor directed the project and selected this recovery demonstration; the source,
packaging and qualification scripts are available for inspection.

## Who it helps

Someone reviewing a small, quiescent file tree needs evidence that a backup can
recover the original bytes. A copied folder or an index-only backup does not
establish that result. This workbench records verified independent snapshots,
restores into fresh directories, and keeps failed jobs visible for review.

## Reproduce one useful workflow

Download the [Windows package](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/backup-recovery-workbench-windows-v0.1.0-1),
verify `SHA256SUMS.txt`, and Extract All into a fresh directory. Python 3.14.10 and
SQLite are included. Open **Recovery Exercise.cmd**. No Python installation or
administrator access is required. The outer package is unsigned.

1. Create a snapshot of three invented files totaling 39 bytes, excluding `cache`.
   The CSV contains `sample,3`; an empty directory is retained.
2. The exercise wrapper changes only that disposable instance's source CSV to
   `sample,9`, representing a change after backup.
3. Restore the snapshot into a new folder. Independently compare every restored
   file against the retained snapshot hashes. The restored CSV contains `3`, while
   the changed source still contains `9`.
4. Damage a separate copy of the snapshot. Attempt recovery using the independently
   retained manifest pin. Expect `SNAPSHOT_CONTENT_MISMATCH`, no new restore tree,
   an unchanged original snapshot and earlier restore, and a retained failed job.
5. Reverify the original snapshot. The summary reports three completed jobs, one
   failed job, no deletion, and the preservation checks.

Every automated run gets a new private exercise instance. Selecting an existing
exercise path is refused before writes. **Recovery Demo.cmd** opens the ordinary
local browser interface; its separate demo instance persists across restarts.
The application never edits source contents; the exercise wrapper deliberately
edits its own invented CSV to demonstrate recovery after a source change.

## Decisions and tradeoffs

- **Fresh destinations:** recovery creates a new tree instead of overwriting the
  source. The operator must inspect and deliberately adopt recovered files.
- **Independent pins:** a trusted manifest hash must be retained independently.
  A hash supplied only by an untrusted backup is not an independent trust source.
- **Conservative retention:** candidates are advisory. Failed verification and
  missing current restore proof protect records; the app never reclaims space.
- **Separate metadata and payloads:** an index backup preserves journal metadata
  but omits file payloads. Complete snapshot folders are required for recovery.
- **Explicit failures:** interrupted and failed jobs retain their outputs and
  require review. They are never automatically replayed, adopted or deleted.

## What the qualification observes

The Windows release's `acceptance.json` records the exact package/source pins,
actual results, and hashes of three actual Chromium captures using invented data.
The release gate requires:

- Seven packaging boundary tests, including refusal of existing exercise state.
- All 62 original core methods on bundled Python 3.14.10: 61 pass, with the
  POSIX-only FIFO check skipped. All six required Windows native link fixtures run.
- Eleven fresh-package acceptance checks: isolated CMD execution without system
  Python, original source inventory, core suite, scripted recovery, existing-state
  refusal, original CLI reopening, actual browser restore and damage refusal,
  narrow keyboard layout, persistence/shutdown, and no writes into the package.
- Windows and Ubuntu produce identical Windows ZIP, receipt and initial checksums.
  Ubuntu's build comparison does not claim Linux execution of the Windows runtime.

The public source ZIP is fixed at `4ac04985ff6a914095503f4f9a63c67806e57a50`.
Its original Python 3.12/3.13 qualification is separate from this Windows runtime
qualification. Public releases retain hashes and limitations; generated instances,
input trees, journals, databases, local paths and raw logs remain private. Captures
show only invented actors/selectors, generated identifiers and fictional outcomes.

## Boundaries

This is a bounded, quiescent primary-byte copy format: 256 files, 4 MiB per file
and 32 MiB per tree, with portable names. It does not supply atomic live snapshots,
hot database consistency, permission/timestamp/alternate-stream restoration,
encryption, signed attestation, scheduling, archive extraction or deletion.
Trusted inputs and parents are assumed. These checks do not establish power-loss,
hardware reliability, hostile concurrent-filesystem resistance or production
recovery readiness. Manual Explorer use on a separate Python-free PC is not part
of the hosted CMD/browser qualification.

See the [quick start](../downloads/windows/backup-recovery-workbench/START-HERE.txt),
[release notes](../downloads/windows/backup-recovery-workbench/RELEASE.md),
[original application limits](../systems/backup-recovery-workbench/README.md),
and [portfolio recovery replay](https://connor-oshea-outlands.thatrobotguy.chatgpt.site/#backup-recovery-case).
