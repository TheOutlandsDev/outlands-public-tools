# Validation boundaries

Fictional standard-library tests cover strict typed JSON/UTC contracts, duplicate
and conflicting observations, atomic batches, stable identities, distinct evidence,
unknown/stale/gap holds, bounded maintenance, planned-off exclusions, escalation,
reopening, acknowledgement invalidation, independent duration/denominator oracles,
replay tampering, exact schema, private manifests/backups and native I/O guards.

Actual Chromium tests exercise the complete recording replay, coverage dashboard,
incident details and acknowledgements, escalation, cached recovery refusal, stale
draft retention, historical refusal, private review/export/backup, review resets,
literal markup, recording-file filename omission, invalid batches, failed fetch
handling, comparison windows, narrow keyboard use and owned local-server shutdown.

The dedicated CI matrix requires Windows and Ubuntu with Python 3.12 and 3.13.
Each job runs core and actual-browser tests, the complete fictional CLI workflow,
JavaScript syntax, source inventory, deterministic packaging and documentation checks.
Four native hardlink/symlink fixtures are mandatory in CI (`WORKBENCH_REQUIRE_LINKS=1`)
and fail the job if unavailable. Only the opposite-platform FIFO/stream case skips.

Local Windows tests run on a drive without native link fixture support; four link
cases and the POSIX FIFO case skip there. Those skips are not native guard proof;
the remote native results must be verified before publication. Browser tooling is
optional and separately installed. The source ZIP must be independently extracted,
its manifest checked and fictional CLI/report/setup commands exercised before release.

No real host metrics, logs, incidents, operator identities, game services, network
probes, restart controllers, scanners or original application runtimes are tested.
The results do not prove live monitoring correctness, SLA compliance, incident
causation, production suitability, encryption, multi-user security, malware isolation
or resistance to a hostile concurrent filesystem editor. Future instance data and
reports remain private; export reviews do not authorize public publication.
