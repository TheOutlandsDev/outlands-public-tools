# OUTLANDS | Change Impact Planner

Plan rechecks from explicitly pinned changes and dependency edges without discovering dependencies or updating targets. Independent MIT CLI/library, Python 3.12/3.13, standard library only.
Fresh generic code and fictional HVAC/game declarations; offline and advisory.

From this complete tool directory:

```text
python -B impacts.py --input examples/input.json
python -B impacts.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional --out selects a
fresh absolute private report outside source under an existing trusted parent.
Library entry: `impacts.check(raw_json_bytes)`.

## Contract

Input exactly `{format,nodes,dependencies,changes}`; format `outlands-change-impact-v1`.
Nodes use the selected snapshot schema. Dependency exactly `{id,upstream,
upstream_revision,upstream_sha256,downstream,downstream_revision,downstream_sha256}`.
Direction means downstream depends on upstream; pins bind full selected snapshots.
Change exactly `{id,node,node_revision,node_sha256}` selects a declared changed node
snapshot, not its before/after diff. Nodes and changes must be nonempty; dependencies
may be empty. This is one explicitly selected snapshot per node ID, not revision history.

Unknown/stale references, different edge IDs for the same directed endpoint pair,
different change IDs for one node, rejected/conflicting identities, self-loops or any
cycle (including disconnected components) withhold the whole assessment/cohort pins.
No partial plan from an invalid graph. A bounded iterative topological pass avoids
recursion depth limits. Accepted graphs can have diamonds or disconnected components.
Expansion beyond 50,000 distinct (node,root-cause) pairs is a fixed IMPACT_CAUSE_LIMIT
refusal, keeping report growth bounded; no partial result is issued.

For each changed root, propagate its ID along downstream edges. Report the union of
roots and reachable downstream nodes, every sorted root cause, directly_changed flags,
and unaffected selected node IDs. A root downstream of another root retains both causes.
Report order is by ID, not an execution schedule. No minimum-path/path enumeration,
automatic diffing, filesystem/network discovery, dependency completeness guarantee,
target update or execution. dependency_discovery_complete is always false: unaffected
means outside closure in this supplied graph, never proof that a real asset is safe.

## Shared boundaries and report interpretation

Selected item/node snapshot exactly `{id,revision,artifact_sha256}`. IDs everywhere
match `[a-z][a-z0-9_-]{0,47}`; revisions are integers 1..1,000,000, not booleans.
Hashes are 64 lowercase hexadecimal characters. They are opaque caller declarations,
not content reads. Policy IDs/revisions follow the same rules. All fields are required;
unknown fields are refused. No inferred defaults, free-text notes, paths or user records.

Each identity list has <=1,000 raw rows. Structurally normalized identical snapshots
with one ID count once; conflicting snapshots exclude every member of that ID group.
Malformed rows are rejected with fixed side/row/code diagnostics without echoing their
values. Complete accounting: input_rows = accepted_records + duplicate_rows +
conflict_rows + rejected_rows. Invalid scope/reference/identity structure withholds
assessment and cohort pins. Logical incompleteness described above retains diagnostics
but never a successful review_scope_sha256. Empty required cohorts cannot pass vacuously.

Pins hash compact sorted-key escaped ASCII JSON plus LF. Sets normalize by sorting;
cohorts hash selected normalized records sorted by ID. input_sha256 hashes exact input
bytes. Qualified review_scope_sha256 binds the named full-cohort/policy pins, plus
as_of in Approval Scope Checker. Pins are consistency receipts, not signatures,
authentic reviewers/history, artifact verification, privacy or publication rights.

One explicit JSON input <=4 MiB; duplicate keys, floats/nonfinite numbers, invalid
Unicode, depth >32, >100,000 nodes, strings >4,096 and JSON integers outside +/-10^18
are refused. Output is escaped ASCII JSON <=8 MiB. Invalid outer schemas, header
policies and list bounds are fixed refusals. Reports expose supplied opaque IDs/hashes:
keep actual inputs/reports private. These tools do not anonymize or sanitize records.

Pinned public [Windows/POSIX I/O guards](IO-SAFETY.md) require ordinary single-link
inputs and trusted quiescent storage. Default report is stdout JSON. Optional --out
requires an absolute fresh destination under an existing trusted external parent
outside source; no overwrite, parent traversal or mkdir. Failed writes may retain
partial/unconfirmed output; inspect privately and choose a fresh path. Windows inherits
parent ACLs without a confidentiality guarantee. Shell redirection lacks these guards.
Exit 0 PASS, 1 REVIEW_REQUIRED, 2 fixed refusal, 130 interruption. Errors omit supplied
paths/values. The guards do not sandbox hostile concurrent processes.

All operations remain offline/advisory. No document/asset dereferencing, live collectors,
clock, account/directory lookup, databases, command execution, URI/include following,
environment expansion, approval dispatch or target changes. Independent directories
have no sibling runtime imports. Only invented HVAC/game metadata is included.
Original private code, records, policies, configurations, credentials, paths and opsec
details were not consulted or selected. See [origins](ORIGINS.md) and [validation](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
