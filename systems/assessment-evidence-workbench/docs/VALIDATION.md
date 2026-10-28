# Validation boundaries

Fictional tests cover strict input parsing, receipt integrity, stale edits, immutable
history replay, workflow transitions, duplicate/risk requirements, review gates,
legacy inconsistent drafts, private manifests/backups, native file boundaries and
loopback HTTP protections. Real Chromium acceptance exercises the management UI,
manual resolution, legacy separation, upload filename omission, stale draft
retention, historical refusal, review resets, literal markup, comparisons, private
exports/backups, narrow keyboard use and failed fetch handling.

The dedicated CI matrix requires Windows and Ubuntu with Python 3.12 and 3.13.
Each job runs the same source, actual Chromium suite, complete fictional CLI demo,
source inventory, deterministic packaging and documentation checks. Native hardlink
and symlink fixtures are mandatory in CI (`WORKBENCH_REQUIRE_LINKS=1`); a missing
fixture fails that job. The opposite-platform FIFO/stream test is skipped.

Local Windows checks run on a drive without native link fixture support; four
native link cases and the POSIX-only FIFO case are explicitly skipped there. These
local skips do not count as native guard proof; remote CI results must be checked
before publication. Browser dependencies and Chromium are optional test tooling.

No real engagement, original prototype runtime, target, scanner, lab, uploaded code,
container, email service or network assessment is executed. Recorded outcomes and
reviewer identities are fictional operator assertions. Tests do not establish
malware containment, encryption, authenticated collaboration, hostile concurrent
filesystem resistance, production suitability or rights to future private inputs.
