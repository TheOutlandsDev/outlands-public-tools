# OUTLANDS | Incident Timeline Checker

Validate exact incident revisions and ordered opening, acknowledgement, resolution and reopening declarations. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B incidents.py --input examples/input.json
python -B incidents.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `incidents.check(raw_json_bytes)`.

## Contract

Input exactly `{format,components,incidents,events,as_of}`, format
`outlands-incident-timeline-v1`. Event exactly `{id,incident,incident_revision,
incident_sha256,ordinal,at,action}`. Ordinal is integer 1..1,000. Action is open,
acknowledge, resolve or reopen. Components/incidents must be nonempty; events may be
empty. Every event binds a known exact incident snapshot, which in turn binds a
known exact component. Different event IDs for an incident/ordinal slot are ambiguous.

For every selected incident, sort by ordinal and require contiguous ordinals from 1
and nondecreasing at values. Equal at values use explicit ordinal order. Transitions:
not_opened + open -> open; open + acknowledge -> acknowledged; open/acknowledged +
resolve -> resolved; resolved + reopen -> open. Repeated open, acknowledgement after
resolution, reopen before resolution and other undeclared transitions are invalid.
Resolution directly from open is allowed; acknowledgement is not implicitly required.

Validate the entire supplied history, including future events. Structural/reference,
ordering or protocol errors withhold the whole assessment/cohort pins; no partial
timeline survives an invalid future declaration. Replay valid events with at<=as_of
to obtain state_as_of and resolved_as_of. Future event IDs remain visible. Missing
history or no effective open at as_of requires review with diagnostics/cohort pins
retained and qualified_scope_sha256 null. A valid open/acknowledged incident can PASS
timeline integrity while resolved_as_of stays false. No actual resolution or recovery
readiness is inferred. The supplied history is not authenticated or independently complete.

## Shared declarations and boundaries

Component exactly `{id,revision,maximum_age}`, maximum_age integer 0..1,000,000,000.
It is caller-selected metadata; only Component Health Snapshot Checker uses its age
limit to assess health observations. Other tools bind the complete component snapshot
without evaluating current health. Incident exactly `{id,revision,component,
component_revision,component_sha256}`. Reference hashes pin the entire normalized
selected snapshot, including identity/revision and policy fields; they are not signatures.

IDs everywhere match `[a-z][a-z0-9_-]{0,47}`. Revisions are integers 1..1,000,000.
Booleans are not integers. At, observed_at and as_of are explicit ordinal integers
0..10^12, not live clock values or automatically interpreted wall-clock timestamps.
All hashes are exactly 64 lowercase hexadecimal characters. Every schema is exact:
all fields required, no unknown fields, inference, environment expansion or defaults.

Each identity list has <=1,000 raw rows. Structurally normalized identical snapshots
for one ID count once; conflicting groups exclude every member. Complete accounting
is input_rows = accepted_records + duplicate_rows + conflict_rows + rejected_rows.
Malformed identity rows produce fixed side/row/code diagnostics without echoing their
values. Structural/reference/protocol errors withhold assessment and cohort pins.
Logical findings retain diagnostics as described above, never a successful qualified
scope pin. Empty required cohorts cannot pass vacuously. Malformed outer schemas,
header policies, as_of and list bounds are fixed refusals.

Pins hash compact sorted-key escaped ASCII JSON plus LF. Cohorts hash normalized
selected records sorted by ID. input_sha256 hashes exact raw bytes. Qualified_scope_sha256
binds report format, all named cohort/policy pins and explicit as_of where present.
Raw bytes, row order and duplicate counts remain distinguishable in the input pin and
accounting. Reports describe supplied declarations, not authentic observations, incident
completeness, actual health, evidence validity, authority, privacy or publication rights.
Reports expose supplied opaque IDs/hashes: keep actual inputs/reports private. These
tools do not anonymize data, sanitize logs or establish that records are safe to publish.

One explicit JSON input <=4 MiB; duplicate keys, floats/nonfinite numbers, invalid
Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers outside +/-10^18
are refused. Output is escaped ASCII JSON <=8 MiB. Pinned public [Windows/POSIX I/O
guards](IO-SAFETY.md) require ordinary single-link inputs and trusted quiescent storage.
Default output is stdout JSON. --out requires an absolute fresh destination under an
existing trusted external parent outside source; no overwrite, traversal or mkdir.
Failed writes may retain partial/unconfirmed output; inspect privately and choose a
fresh path. Windows inherits parent ACLs without a confidentiality guarantee. Shell
redirection lacks these guards. Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130
interruption. Errors omit supplied paths/values. Guards do not sandbox hostile concurrent
processes. No sibling runtime imports or third-party runtime packages are required.

No network probes, live collectors, artifact reads, commands, clock collection,
URI/include following, notifications, suppression, database/provider access, incident
updates, scheduling, restarts, restores or equipment control. Only fictional HVAC/game
metadata is included. Original private code, schemas, policies, user records, logs,
paths, credentials, endpoints and opsec details were not consulted or selected.
See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
