# OUTLANDS | Safe File Mover source review

Selected source comprises an experimental Python CLI/engine, SQLite journal, optional Tk GUI, packaging declaration, ignore rules, documentation and fictional tests. No application data, logs, journal database, original source history, installer, dependency implementation or retained recovery copy is included. Licensing is unassigned.

## Corrections in this source adaptation

- Fixed-code CLI argument errors; no-argument invocation shows help instead of implicitly opening a GUI. Valid command output and runtime errors still contain paths and must remain private.
- Fresh POSIX journal directories/database/lock storage use owner-only requested modes, independent of a permissive umask. Existing shared/foreign-owned files are refused without chmod. State symlinks, database/lock links and applicable rollback-journal paths receive explicit checks. Environment-selected state preserves lexical components for those checks.
- Staging files/directories start with private modes before basic source metadata is applied. Regular source opens use descriptor identity checks and available no-follow/nonblocking flags; reads/copies reject observed growth.
- Destination content is rechecked after the final pre-delete callback before purging a managed copy. Mismatches retain the managed purging path/journal intent rather than deleting it.
- A named-stream fixture uses a neutral fictional name. Stream-preservation behavior remains part of the retained source; no claim of Windows acceptance follows.

These are source-only public adaptations. The private dev repository and original snapshot are unchanged. Required notices were not removed. Original source mappings/hashes remain private; owner-reported personal creation with AI assistance is not independent proof of exclusive authorship. Adaptation/tests/docs were AI-assisted.

## Fixture results

A fresh isolated Python 3.12.7/Linux run discovered **66 unittest methods: 54 passed, 12 Windows-only skipped, zero failures/errors**. Eighteen methods were added. Sixteen targeted regressions failed/errored against the prior sanitized copy before the fixes and passed against the candidate; no-argument help and environment-state checks supply additional coverage. The original GUI was not launched for the baseline comparison.

Tests use only temporary fictional trees, including destructive move/purge and recovery tests. Child execution uses resource bounds and fail-closed network syscall denial with a blocked-socket selfcheck. Candidate source/test bytes were unchanged by testing. Remote behaviors use mocks/local data; no live network share was used. Windows named-stream and filename skips remain explicit and are not successful tests.

## Limits

No GUI runtime, Windows/macOS acceptance, actual SMB operation, production-data backup, crash/power-loss durability or full metadata preservation is established. Native flush requests and matching hashes do not establish hardware/server persistence. Existing journals are trusted operational state, not untrusted input; parent paths must remain trusted and quiescent. Mode checks are not a complete ACL audit. There is still a gap between verification and a destructive action, so external writers remain outside the supported boundary. Do not move live databases/service state with this experimental tool.

Read [the tool README](../tools/safe-file-mover/README.md) before using a disposable preview. Keep real outputs private. See [LICENSING.md](../LICENSING.md); public visibility does not assign an open-source license or grant general reuse rights.
