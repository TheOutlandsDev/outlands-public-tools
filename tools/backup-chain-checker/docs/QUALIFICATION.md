# Standalone download qualification

Backup Chain Checker 0.1.0 is a reviewed **source-only** release. Qualification
starts from freshly extracted source and clean environments. Actual versions,
counts, outcomes and named skips belong to release `VALIDATION.json`; selected
coverage is not a passing result.

## Required source and test boundary

Eight lanes select Windows/Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each creates a new venv without pip or installed distributions and imports
`chain_check.py` from the selected extraction. The single-script CLI uses only
standard-library/OS APIs, without a runtime mirror, public sibling or donor.

All 43 original test method bodies, 105 assertion calls and eight helper ASTs
remain preserved. Explicit `python-ast-fields-json-v1` encoding retains full
AST fields rather than relying on interpreter-specific dump formatting;
original/adapted within-version equality remains required. Adapter globals
select the actual extracted module/script for both in-process and subprocess
checks. Runtime and all four example controls retain exact baseline Git bytes.

Another 26 copied single-script CLI methods select real processes, complete
JSON/exit outcomes, native input safeguards and input/runtime preservation.
This selects **69 methods per lane, 552 across eight lanes**: 344 original
regression and 208 copied CLI cases. Missing/duplicate IDs, changed original
methods/helpers, zero discovery, wholly skipped modules, noncontract skips,
failures and errors cannot qualify. Pass/skip counts are separate from these
selected-method totals.

Applicable hosted hardlink/symlink/junction/native input fixtures must execute.
Platform-only and locally unavailable capabilities require exact method/reason
contracts; do not bypass device policy or mistake a setup failure for a
successful CLI refusal. Skips are not passes or substitute native coverage.

## Source and execution evidence

The source gate checks the finite inventory/manifest, hashes, sizes, Python/
structured-data syntax, module-local links and selected privacy indicators.
It is not perfect secret detection, exclusive-authorship proof or blanket
privacy/rights/security clearance. The ZIP contains no interpreter/dependency
binary, backup payload, real control/result, private source or raw log.

All eight lanes independently rebuild committed reviewed source and compare
**both ZIP and build-manifest bytes**. Sorted members and synthetic fixed
archive metadata support deterministic identity. `build.py` and `qualify.py`
refuse optimized Python, including `-O`, `-OO` and active `PYTHONOPTIMIZE`, before
assertions can be disabled. The CLI's normal interpreter contract is separate
from helper refusal.

Preserved coverage includes all 1,296 four-node parent graphs against an
independent reachability oracle, 300 seeded valid forests, permutation
invariance, maximum depth and blocked ancestry. Local declaration issue order,
all cycle members including invalid full-parent edges, separate selected-target
status, all-or-empty ancestry order and unrelated bad-branch review remain part
of the graph contract. Counts/IDs/issues/order are metadata observations only.

Copied consumers use only authored disposable plans. The checker reads one
selected control and prints stdout, without a clock query, backup-content read,
restore/deletion action, command generation or network probe. All eight action/
verification flags remain false. Original-component validation precedes path
normalization; native leaf/parent dot/space spelling checks are separate from
any claim about hostile-filesystem or universal alias safety.

The unchanged runtime already supplies these graph and input checks. Historical
local 43/41/2 and collection workflow 3.12/3.13 evidence remain separate from
fresh standalone release/download qualification.

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
[USAGE.md](../USAGE.md) supplies isolated fictional full JSON/exit outcomes and
input/extra/prior-output/runtime preservation checks.

User-owned Python/venvs do not inherently need administrator access. Respect
device policy and OS prerequisites without bypasses. Real controls/IDs/results,
backup data, personal paths, credentials and raw logs stay private. Publish only
designated reviewed source and sanitized actual validation.

## Limits that remain

Input is at most 64 KiB, with 1–256 snapshots, tokens of at most 40 characters
and sequence integers 0–1,000,000. Paths have 4,096-character/64-part bounds.
These are not total CPU/memory/JSON-depth/deadline or storage quotas. Interruption
or OS stdout failure may leave partial captures.

Consistency does not establish snapshot existence, completeness, parent/content
agreement, authenticity, application consistency, independence, encryption-key
access, restorability, retention safety or deletion permission. Outputs retain
identifying IDs/issues/dependency order despite omitted series/sequence/parent
fields. No secret scan, IP/licensing review or publication clearance follows.

Sampled identity checks are not atomic snapshots, deny-writer/race guarantees,
hostile-filesystem containment, arbitrary mount/drive aliases, live/network/
virtual-provider, universal I/O, ACL privacy or power-loss acceptance. Reads can
affect access metadata; Python caches and caller tracebacks/captures are
separate. See [README.md](../README.md) and [PROVENANCE.md](PROVENANCE.md).
