# Standalone download qualification

Backup Retention Planner 0.1.0 is a reviewed **source-only** release. Qualification
starts from freshly extracted source and clean environments. Actual versions,
counts, outcomes and named skips belong to release `VALIDATION.json`; selected
coverage is not a passing result.

## Required source and test boundary

Eight lanes select Windows/Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each creates a new venv without pip or installed distributions and imports
`retention_plan.py` from the chosen extraction. The CLI uses only standard-
library/OS APIs and needs no sibling module or donor fixture.

All 39 original test method bodies/assertions remain preserved. Their adapter
creates an owned temporary collection-shaped runtime mirror for the original
subprocess method and verifies its bytes against the selected source. Only one
runtime is shipped; unrelated shared-suite code and public sibling tools are
not required by the standalone consumer.

Another 26 copied single-script CLI methods select real processes, complete
JSON/exit outcomes, native input guards and input/runtime preservation. This
selects **65 methods per lane, 520 across eight lanes**. Missing/duplicate IDs,
changed original method bodies, zero discovery, wholly skipped modules,
noncontract skips, failures and errors cannot qualify. Actual pass/skip counts
remain separate from these selected-method totals.

Applicable hosted native hardlink/symlink/junction fixtures must execute.
Platform-only and locally unavailable capability cases require exact method/
reason contracts; do not bypass device policy or mistake a fixture setup
failure for a successful CLI refusal. Native skipped cases are not passes.

## Source and execution evidence

The source gate checks the finite inventory/manifest, hashes, sizes, Python/
structured-data syntax, module-local links and selected privacy indicators.
It is not perfect secret detection, exclusive-authorship proof or blanket
privacy/rights/security clearance. The ZIP contains no interpreter/dependency
binary, backup payload, actual plan/result, private source or raw log.

All eight lanes independently rebuild committed reviewed source and compare
**both ZIP and build-manifest bytes**. Sorted members and synthetic fixed
archive metadata support deterministic identity. `build.py` and `qualify.py`
refuse optimized Python, including `-O`, `-OO` and active `PYTHONOPTIMIZE`, before
assertions can be disabled. The CLI's normal interpreter contract is separate
from helper refusal.

Preserved semantics include strict plan/policy/snapshot fields and types,
canonical UTC syntax, supplied `as_of`, count/age/pin union, exact cutoff ties,
inclusive rolling-24-hour age boundaries, disabled age protection, future
exclusion from nonfuture ranking and conservative review issues. Row/reason/
issue order and all six false action/verification flags remain part of the
result contract. The existing 24:00 canonical-clock refusal is already in the
baseline; no new timestamp or policy change is packaged here.

Path checks retain their post-normalization boundary. Native Windows probes
accepted canonical plan spelling plus trailing-dot/space aliases as the same
selected file. The public docs record that limit and require fully spelled
trusted canonical paths. Original-spelling suffix prevalidation or universal
alias refusal is not claimed, and the runtime is not changed for this behavior.

Copied consumers use only authored disposable metadata, not actual backup
software, storage or payloads. The planner reads one selected control and prints
stdout only; it neither uses a live clock nor scans, copies, restores, deletes,
contacts a host or generates commands. Historical collection/Python-3.15 repair
evidence stays distinct from fresh release/download results.

## Reproduce privately

From the reviewed committed repository module, with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Package outputs must be new with existing parents and use the same reviewed
commit. Qualification input directories must exist; workspace/report must be
new absolute paths with existing parents outside source. Generated work and
receipts stay in an external [private workspace](PRIVATE-WORKSPACE.md).

Consumer qualification may omit `--reference-build`, honestly recording
`identical_zip` and `identical_build_manifest` false without independent
Git-source rebuild proof. Every hosted lane requires both true. Anonymous asset
hash/source comparisons and fresh consumer execution provide separate evidence.
[USAGE.md](../USAGE.md) supplies isolated fictional full JSON/exit and input/
extra/prior-output/runtime preservation checks, using declared review instants.

User-owned Python/venvs do not inherently need administrator access. Respect
device policy and OS prerequisites without bypasses. Actual plans, IDs,
results, captures, interpreter trees, personal paths, credentials and raw logs
stay private. Publish only designated source and sanitized actual validation.

## Limits that remain

The plan is at most 64 KiB, with 1–256 snapshots, IDs of at most 40 characters,
`keep_latest` 1–256 and `keep_days` 0–36,500; zero disables age protection.
Paths have 4,096-character/64-part bounds. These are not total CPU/memory/JSON-
depth/deadline or storage quotas. Interruption or OS stdout failure can leave
partial captured output.

Canonical UTC dates, `independent_full` and pins remain supplied declarations.
KEEP/REVIEW does not establish snapshot existence, independence, authenticity,
integrity, restorability, redundancy, free space, privacy or deletion permission.
IDs/reasons/counts can remain identifying even when dates/policy values are
omitted. No secret scan, IP review, licensing or publication clearance follows
from a valid plan.

Sampled checks on a supported regular single-link input/ancestors are not an
atomic snapshot, hostile-filesystem sandbox, universal I/O deadline, arbitrary
mount/drive, live/network/virtual-provider or power-loss guarantee. Reads can
affect access metadata; Python caches and caller tracebacks/captures are
separate. See [README.md](../README.md) and [PROVENANCE.md](PROVENANCE.md).
