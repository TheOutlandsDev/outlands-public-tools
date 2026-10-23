# OUTLANDS | Safe File Mover

Experimental source showcase for a journaled file mover. It records a content manifest, copies to staging, verifies SHA-256 content, commits without replacing an existing destination and retains the original under a managed recovery name by default. This reviewed source candidate includes CLI, engine, SQLite journal, optional Tk GUI and synthetic tests. It is not a production backup acceptance result.

**Move, restore, abandon and purge change files. Purge permanently deletes retained data.** Start with disposable fictional copies and keep an independent backup of anything important. Publication of source does not authorize an operator to move other people's data.

## Runtime and a disposable preview

Python `>=3.12.7,<3.13` is declared. There are no third-party Python runtime dependencies. The optional GUI needs working Tk/Tcl; packaging uses the declared setuptools backend. No installer, executable, interpreter, dependency implementation or real input is bundled. The review used existing Python 3.12.7 on Linux without building or installing anything.

From this tool directory, create a fictional `example-input` file/directory and a separate existing `example-output` directory. Choose a fresh, trusted **local** state directory outside the source tree:

```text
python -m safe_file_mover --help
python -m safe_file_mover --state-dir ./example-state plan ./example-input ./example-output
```

`plan` reads/hashes the source and checks the proposed destination; it does not create state or write journal records. It is not a snapshot or a reservation. No arguments show static help; GUI startup requires an explicit `gui` command. Malformed arguments return status 2 and `Error: ARGUMENTS_INVALID` without echoing supplied values. Ordinary valid output, operation errors and history intentionally include paths; they are private operational records, not anonymized output.

After reviewing a disposable preview:

```text
python -m safe_file_mover --state-dir ./example-state move ./example-input ./example-output
python -m safe_file_mover --state-dir ./example-state list
```

The default conflict policy is `fail`. `--on-conflict rename` chooses a new destination name, and `--name` chooses a different final filename/directory name. Neither permits replacement of an existing destination. `move` performs a fresh plan and then creates staging, journal and destination records. The retained original has a generated recovery pathname rather than its original name. Preview source/destination and close programs that may write to them.

## State and temporary-copy privacy

The journal stores paths, manifests, errors and operation history. On POSIX, a fresh state directory requests mode 0700; the database and operation lock request mode 0600 regardless of a permissive umask. Existing group/other-accessible or foreign-owned state/database/lock files are refused rather than silently chmodded. Database/lock hard links, symlink state components and symlink database/rollback-journal/lock paths are refused by the corresponding checks. Existing insecure state requires a separate owner review of location, ownership, links and backup; do not delete a journal or retained recovery path to suppress a refusal.

Regular-file staging starts at mode 0600 and directory staging at 0700, before copying the source's basic metadata. Final permissions/timestamps follow the source's supported metadata; they are not forced private if the original is deliberately shared. POSIX source file opens use no-follow/nonblocking flags and verify descriptor identity; reads/copies reject observed growth beyond the recorded size. Windows permission/ACL semantics are not established by these POSIX checks.

These protections assume trusted, quiescent parents and state. They do not sandbox hostile concurrent ancestor replacement, audit every ACL or protect against an untrusted owner modifying the journal. Keep state on known local storage; automatic remote-path classification is Windows-specific and does not certify arbitrary POSIX network mounts as local. Console captures and GUI logs can also contain paths and tracebacks; keep them private and outside this repository.

## Recovery and deletion

Use the operation ID from `list` with `history`, `recover --id`, `restore`, `purge` or `abandon`. Use the same state directory for the same operation.

- `recover --all` attempts to resume interrupted operations. Inspect each returned status; a handled per-operation failure can leave that operation paused.
- `restore` returns retained content to its original path subject to verification; the destination remains in place.
- `abandon` discards an uncommitted managed staging copy after source verification.
- `purge` permanently deletes a retained recovery copy after verification. The candidate rechecks destination content after the final pre-delete callback as well as at earlier boundaries. A mismatch leaves the managed `.purging` copy and journal intent for inspection; no automatic rollback or successful recovery is implied.
- `move --delete-recovery-copy` explicitly requests automatic deletion for a local destination. It is not the default. Remote destinations reject automatic deletion; a later remote purge needs `--acknowledge-remote-risk`.

Acknowledgment and matching hashes do not prove server-side persistence. There is still a time window between the last verification and deletion; keep both copies quiescent. Power-loss, controller and server behavior are outside the fixture evidence. Never use purge to work around a failed verification.

## Data and platform limits

The engine is not a filesystem snapshot, application-consistent backup, general metadata scrubber or guarantee against hostile concurrent writers. Do not move live databases or active service state without an appropriate application-level backup procedure.

Regular files, directories and symlinks are represented; directory symlinks are not recursively traversed as trees. Mount roots, nested mount/device boundaries, Windows junctions and unsupported special types are rejected. Detected POSIX extended attributes are refused. Windows named-stream implementation/tests are retained as source, with a neutral fictional stream fixture; **Windows execution is unvalidated**. Symlink targets can themselves reveal names or refer outside the selected tree. ACLs, ownership, sparse allocation and hard-link relationships are not fully preserved across volumes. Directory commits require supported no-replace filesystem behavior. Flush calls can fail or be unsupported; matching bytes and requested flushes are not power-loss durability proof.

The optional GUI can be requested with `python -m safe_file_mover gui`. It received static source review only; no Tk window, UI smoke test or desktop file operation was run. Its confirmations/logs are not independent engine acceptance. Linux, Windows, macOS and actual SMB behavior must not be conflated.

## Recorded validation

**66 unittest methods discovered: 54 passed, 12 Windows-only methods skipped, zero failures/errors**, on isolated Python 3.12.7/Linux. The 12 skips are eleven named-stream cases and one filename-rules case; none counts as a pass. Remote behavior uses local fixtures/mocks, not a live share. Eighteen added regression methods cover argument/no-argument behavior, state/lock/storage privacy, staging modes, replaced-source symlink refusal and the final purge boundary. Sixteen targeted regressions reproduced failures/errors in the prior sanitized implementation before the correction; the remaining cases cover help and environment-selected state.

Tests run only in temporary fictional trees. File moves, restore, abandonment and destructive purge tests operate on disposable test data. Resource-bounded children used fail-closed network syscall denial and a blocked-socket selfcheck. No original program, real data, production service, GUI, live Windows/SMB or power-loss scenario was exercised.

Run from this tool directory in a private scratch environment:

```text
python -B -m unittest discover -s tests -v
```

## Provenance and licensing

The owner reports personal work created with AI assistance. The selected retained snapshot supplies the original code; public adaptations, regression tests and documentation were AI-assisted. No required copyright, attribution or license notice was removed. Source hashes preserve lineage privately; a snapshot label/hash and owner attestation do not independently prove exclusive authorship or original creation date.

Licensing remains unassigned; see [LICENSING.md](../../LICENSING.md). See [the file-mover review](../../docs/BATCH-4-REVIEW.md) for scope and limitations. No journal, runtime capture, source Git history, original operational document, installer or recovery copy is included. Required third-party notices must be retained if future material is distributed.
