# Validation boundaries

Fictional tests verify exact primary file bytes/hashes, empty directories,
exclusions, stable-source checks, limits, stale heads, source mutation, partial
copy/restore failures, corrupted payloads/manifests/markers, exclusive targets,
fresh-index pinned recovery, received-manifest traversal refusal, current retention
proof, holds, typed journal replay, reviewed metadata-only reports and index backups.

An actual owned child process is killed after a durable started event and partial
output. Tests require stale-session refusal, explicit stopped recovery, retained
partial bytes, no automatic adoption/replay and unchanged fictional source contents.
This is controlled interruption evidence, not power-loss or storage-hardware proof.

Native qualification covers six required fixtures: hardlinked input, hardlinked
metadata database, symlink input, symlink parent, a hardlinked selected source file,
and a selected source directory link. The last uses a real Windows junction through
PowerShell 7 on Windows and a directory symlink on POSIX. Local drive limitations
may skip those fixtures; CI sets `WORKBENCH_REQUIRE_LINKS=1`, so unavailable native
fixtures fail instead. Only the opposite-platform FIFO/stream-name test skips there.

Actual Chromium workflows exercise copy/restore/retention, quiescence, explicit
verification jobs, fresh restore destinations, holds, corrupt recovery proof,
retained failed jobs and drafts, stale heads, private reports, index-only backup,
review resets, literal markup, interruption review, scope refusal, failed reads,
history, narrow keyboard layout, pinned-copy recovery and owned server shutdown.

The required Windows/Ubuntu Python 3.12/3.13 matrix also runs the full fictional CLI
demo, source inventory, JavaScript syntax, documentation checks and deterministic
source packaging. The focused ZIP must be independently extracted; setup commands,
file hashes, restore receipts, report manifests, journal/index pins and trusted-copy
recovery must be walked through before publication. Optional browser tooling is
installed separately from the source package.

No real backups, saves, operating databases, customer/user files, schedules, original
archive scripts, host controls, network services or game assets are exercised.
Tests do not establish atomic live-file consistency, power-loss recovery, hardware
reliability, long-term retention, OS/permission restoration, encryption, signed
attestation, production suitability or hostile concurrent-filesystem resistance.
All future instance contents and reports remain private.
