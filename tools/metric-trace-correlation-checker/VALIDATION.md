# Validation and interpretation limits

telemetry-trace-checks qualifies Python 3.12/3.13 on Windows and Ubuntu. Required native
fixtures cover read/hash, fresh write/readback, hardlink-input refusal, linked-parent
refusal, changed-input detection and overwrite refusal. Only opposite-platform methods
may skip; local volume skips are not native proof.

Known-answer/adversarial checks cover metric kinds/units, label scopes, unique series,
exact definition pins, decimal normalization, counter/gauge limits and histogram bounds;
required/optional snapshot gaps, non-latest point slots, bucket totals, empty sums,
strict kind payloads, inclusive run bounds and bounded series/run coverage; exact trace
references, expected span ownership, missing/extra/partial traces, zero duration,
multiple roots, parent cycles/cross-scope references, asynchronous children and declared
run bounds; exact selected point/span links, half-open correlation windows, point-time
equality, cross-run refusal despite equal clock labels, source recomputation, unselected
points, multiple distinct links and invalid extra links despite valid coverage. Every
identity cohort tests complete duplicate/conflict/rejected-row accounting. Shared
strict JSON/I/O tests preserve source protection, no overwrite and fixed errors.

Actual standalone acceptance copies each complete tool separately, verifies source
pins, runs CLIs, writes fresh reports, refuses overwrite/source output and checks raw
input hashes, unchanged inputs, fixed errors and absence of action artifacts. Connected
invented HVAC report metadata binds identical definition/series/run/point/trace/span
cohorts across four CLIs. A game-build definition example and AI/software trace example
contain no assets/models/credentials or actual telemetry. The correlation tool rejects
forged PASS fields and recomputes both source contracts. An explicit teaching adapter
supplies fictional span boundaries and declared start/finish events to the existing
public Process Event Duration Analyzer, including missing-finish refusal. Those events
are invented claims, not evidence of real execution or hold-free work. Its engine is
not duplicated or imported into the new tools.

Synthetic qualification does not establish real measurements, synchronized clocks,
trace completeness, metric/trace causation, actual duration or production health.
Original private code, business/telemetry schemas, real captures/logs, customer/user
records, identities, paths, credentials, endpoints and deployment details were not
consulted or selected. No collection, exporters, service access or target changes occur.
