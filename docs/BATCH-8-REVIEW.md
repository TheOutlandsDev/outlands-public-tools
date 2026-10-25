# Batch 8: release and launcher preflight

Prepared 2026-10-25. This batch adds Release Preflight and completes the
[current-source pattern review](PUBLIC-SOURCE-REVIEW-2026-10-25.md). The owner
selected TheOutlandsDev-only attribution for two original-code licenses. Their
MIT grants and third-party notices are preserved; exact source manifests were
refreshed.

## Source boundary

Read-only review covered the owner's server updater, component overlay updater,
launcher wrapper, and Python application launcher methods. These combine live
vendor downloads, process checks/control, installation, rollback, logging,
environment configuration, and monitoring startup. Original scripts, parameters,
hardcoded paths, URLs, configurations, telemetry and downloaded content remain
private. Original scripts and application tests were not run.

The public utility is newly implemented from a neutral specification: verify
an externally pinned local inventory, compare selected current files, check a
separately pinned launcher specification, and return recovery guidance. It
reads selected local bytes and writes only an explicitly requested new private
report. No game/plugin code, package implementation or runtime asset is copied.
Authorship rests on the owner's personal-work statement and this fresh original
implementation; this does not independently prove ownership of all historical
private sources.

## Validation

Windows/Python 3.12.7 discovered 28 new fixture methods: 26 passed, two native
link-creation cases were skipped, and none failed in the completed run. Fixtures
cover pins, JSON keys/contracts, paths and limits, file lists, changed inputs,
planned actions, report privacy/no replacement, launcher arguments and an actual
CLI invocation. Its payload would fail if executed; it was only hashed.

The first test attempt could not create child fixtures in the sandbox-provided
temporary directory; fixtures were redirected to a bounded private workshop
directory. Tests then exposed inconsistent creation-time metadata across
Windows stat APIs. Stability comparisons use file identity, size and modification
time consistently with the existing transfer tool; observed changes still cause
refusal.

Native game/server execution, deployment, application-consistent backup, network
shares, hostile concurrent writers, alternate streams, Windows permissions and
power-loss recovery remain unverified. Static launcher checks do not establish
startability or safe arguments. Private data, configuration, history and source
outside the selected current tree remain uncleared.
