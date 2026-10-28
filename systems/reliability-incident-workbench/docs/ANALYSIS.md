# Incident lifecycle and time accounting

Stable incident identity is SHA-256 over canonical service ID, signal ID and kind
(`health` or `freshness`). Severity and note text do not participate. A fresh down
signal is critical; degraded is warning. Missing, stale or explicitly unknown facts
create warning freshness incidents. Repeating cached bad evidence updates the last
sample where it was observed but does not increase distinct occurrence counts.

Unresolved health incidents remain active/monitoring and held while evidence is
unknown or excluded. Their clean counts reset. Freshness incidents require fresh
known evidence to recover; a fresh down result can clear freshness while opening
or retaining health failure. Distinct qualifying observation timestamps advance
recovery. Repeating one cached good fact never advances twice. Evidence predating
a later missing observation, long gap or maintenance end cannot clear that held
incident. After a long gap, qualifying evidence must be newer than the preceding
snapshot. Maintenance-end evidence at the exact end is allowed.

The configured consecutive clean-evidence count moves an incident through
`monitoring` to `resolved`. Reopening increments its episode and retains a completed
episode summary. Warning-to-critical escalation increments an escalation counter;
both escalation and reopening invalidate an older acknowledgement assertion.
Acknowledging an incident never resolves or changes it.

Maintenance overrides status only inside the configured half-open interval. A
planned-off expectation excludes that service throughout the recording. Existing
incidents are held, not resolved; new runtime alerts are suppressed during excluded
samples. This does not detect unexpected actual activity of a planned-off service
or authenticate maintenance intent. Imported recordings remain operator assertions.

Time accounting is independent from recovery state. Each interval starts at one
snapshot and ends at the next. It is split at signal freshness expiry, the maximum
gap boundary, and maintenance start/end. Each subinterval is classified at its
midpoint using the preceding snapshot only. All boundaries use whole-second UTC
inputs, so durations conserve integer seconds. No final-snapshot tail is invented.

Outside exclusions, a fresh down signal proves down within this supplied model.
Otherwise any unknown required signal makes the service unknown. With all required
signals fresh and known, any degraded signal yields degraded, otherwise healthy.
Beyond the maximum gap, nonexcluded time becomes unknown even if a cached fact's
age limit would otherwise allow it. Maintenance and planned-off time remain separate
from healthy/degraded/down/unknown buckets.

For each service:

- `known_seconds = healthy + degraded + down`.
- `eligible_seconds = known_seconds + unknown`.
- `healthy_fraction_of_known_seconds = healthy / known_seconds`.
- `observation_coverage_fraction = known_seconds / eligible_seconds`.
- Maintenance/planned-off buckets are reported but excluded from both denominators.
- Empty denominators return null. Degraded time is not counted as healthy.

A high healthy fraction with low coverage is weak evidence. Different report
windows or policy assumptions are not automatically comparable. Recorded facts,
coverage arithmetic and incident review do not establish actual SLA compliance,
independently measured uptime or the cause of an incident.
