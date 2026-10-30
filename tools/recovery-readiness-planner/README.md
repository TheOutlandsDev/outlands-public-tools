# OUTLANDS | Recovery Readiness Planner

Reconcile required declared recovery checks and fresh evidence against exact incident revisions, without performing recovery. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic logic and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B recovery.py --input examples/input.json
python -B recovery.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects an
absolute fresh private report outside source under an existing trusted parent.
Library entry: `recovery.check(raw_json_bytes)`.

## Contract

Input exactly `{format,components,incidents,policy,checks,evidence,as_of}`, format
`outlands-recovery-readiness-v1`. Components/incidents must be nonempty; checks and
evidence may be empty. Policy exactly `{id,revision,required_roles,maximum_evidence_age}`.
Required_roles is 1..32 unique role IDs normalized by sorting; maximum_evidence_age is
integer 0..1,000,000,000. Check exactly `{id,revision,incident,incident_revision,
incident_sha256,role}`. Role must appear in the selected policy. Evidence exactly
`{id,check,check_revision,check_sha256,policy_sha256,outcome,observed_at,artifact_sha256}`.
Outcome is pass, fail or unknown. Every check binds an exact selected incident;
every evidence row binds an exact selected check and the normalized policy.

Different check IDs for one incident/role or evidence IDs for one check are ambiguous;
no latest/best receipt selection. Unknown/stale references, policies, invalid rows or
slot ambiguity withhold the entire assessment/cohort pins. Evidence artifact hashes
are never dereferenced or verified. A component contract pin identifies its metadata;
it does not supply an implicit health check.

For every incident and required role, report missing checks, missing evidence, declared
outcomes, freshness and failed criteria. Freshness is the same inclusive age rule as
the health checker, using maximum_evidence_age. Missing checks/evidence, future/stale
evidence and every outcome except pass require review. All blockers remain visible;
cohort pins remain but qualified_scope_sha256 is null. Every role must have one fresh
declared pass before ready_for_manual_recovery_review can be true.

Roles have no built-in operational meaning. The fictional policy names component-health,
incident-resolution and restore-drill; the connected example explicitly adapts separate
report declarations into pinned evidence. The planner does not authenticate those
reports, infer an incident is resolved or prove a drill occurred. It checks only supplied
metadata. PASS is readiness for manual review, never authorization or a recovery plan
with commands. No restart, restore, rollback, scheduling, equipment control or actual recovery.

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
