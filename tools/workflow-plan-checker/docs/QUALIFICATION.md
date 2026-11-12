# Standalone download qualification

Workflow Plan Checker 0.1.0 is a reviewed source-only release. Qualification
starts from freshly extracted source and clean environments. Actual versions,
counts, outcomes and named skips belong to release `VALIDATION.json`; selected
coverage is not a passing result.

## Required source and test boundary

Eight lanes select Windows/Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each creates a new venv without pip or installed distributions and imports
`workflow_check.py` from the selected extraction. The single-script CLI uses
standard-library/OS APIs, without a runtime mirror, sibling tool or donor.

All 46 original method bodies, 106 assertion calls and nine original helper ASTs
remain preserved. Explicit `python-ast-fields-json-v1` encoding retains full
AST fields instead of interpreter-specific dump formatting; original/adapted
within-version equality remains required. Adapter globals select the actual
extracted checker/script for in-process and subprocess checks. Runtime and all
four example controls retain exact baseline Git bytes.

Another 26 copied single-script CLI methods select real processes, complete
JSON/exit outcomes, native input safeguards and input/runtime preservation.
This selects **72 methods per lane, 576 across eight lanes**: 368 original
regression and 208 copied CLI cases. Missing/duplicate IDs, changed originals/
helpers, zero discovery, wholly skipped modules, noncontract skips, failures
and errors cannot qualify. Selected counts are separate from actual passes/skips.

Applicable hosted hardlink/symlink/junction/native input fixtures must execute.
Platform-only and locally unavailable capabilities require exact method/reason
contracts. Do not bypass device policy or mistake setup failure for a successful
CLI refusal. Skips are not passes or substitutes for native hosted evidence.

## Source and execution evidence

The source gate checks finite inventory/manifest, hashes, sizes, Python/
structured-data syntax, module-local links and selected privacy indicators.
It is not perfect secret detection, exclusive-authorship proof or blanket
privacy/rights/security clearance. No interpreter/dependency binary, actual
plan/result, operational payload, private source or raw log is bundled.

Every hosted lane independently rebuilds committed reviewed source and compares
**both ZIP and build-manifest bytes**. Sorted members and synthetic fixed archive
metadata support deterministic identity. `build.py` and `qualify.py` refuse
optimized Python, including `-O`, `-OO` and active `PYTHONOPTIMIZE`, before
assertions can be disabled. The CLI's interpreter contract is separate.

Preserved reference coverage includes all 512 three-node dependency graphs with
an independent path-cycle oracle, 216 acyclic graph/state combinations, 300
seeded valid plans and 100 brute-force ordering comparisons. These are declared-
metadata fixtures. Any issue globally withholds all three derived lists, even
for unrelated apparently clean branches. Cycle members, active/completed
prerequisite claims, lexicographic topological order and pending-only eligibility
retain their existing behavior; no state is repaired or advanced.

Copied consumers use authored disposable plans. The checker reads one selected
control and prints stdout, without task execution, state verification, execution
authorization, command generation, plan mutation, filesystem scan or network
probe. All seven action/verification flags remain false. Original components
are validated before normalization; native leaf/parent spelling observations
remain separate from hostile-filesystem or universal alias-safety claims.

The unchanged runtime already supplies these graph/state/input checks.
Historical local 46/44/2 and collection workflow Python 3.12/3.13 evidence remain
separate from fresh standalone release/download qualification.

## Reproduce privately

From the reviewed committed repository module, with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Package outputs must be new, with existing parents and the same reviewed commit.
Qualification input directories must exist; workspace/report must be new
absolute paths with existing parents outside source. Generated work and receipts
stay in an external [private workspace](PRIVATE-WORKSPACE.md).

Consumer qualification may omit `--reference-build`, honestly recording
`identical_zip` and `identical_build_manifest` false without independent
Git-source rebuild proof. Every hosted lane requires both true. Anonymous
asset/source comparisons and fresh consumer execution provide separate evidence.
[USAGE.md](../USAGE.md) supplies isolated fictional complete JSON/exit outcomes
and input/extra/prior-output/runtime preservation checks.

User-owned Python/venvs do not inherently need administrator access. Respect
device policy/OS prerequisites without bypasses. Real plans/IDs/results, personal
paths, credentials, private source and raw logs remain private. Publish reviewed
source and sanitized actual validation only.

## Limits that remain

Input is at most 64 KiB, with 1–128 tasks, 0–32 prerequisites per task and tokens
at most 40 characters. Paths have 4,096-character/64-part bounds. These are not
total CPU/memory/JSON-depth/deadline or storage quotas. Interruption or stdout
failure may leave partial captures.

Consistency does not establish execution history, prerequisite success,
authorization, scheduling/resource/concurrency acceptance or containment.
Outputs retain identifying IDs/counts/issues/order/eligibility despite omitted
raw states/prerequisites. No privacy/IP/licensing or publication clearance follows.

Sampled identity checks are not atomic snapshots, deny-writer/race guarantees,
hostile-filesystem containment, arbitrary mount/drive aliases, live/network/
virtual-provider, universal I/O, ACL privacy or power-loss acceptance. Reads
can affect access metadata; Python caches/caller tracebacks/captures are separate.
See [README.md](../README.md) and [PROVENANCE.md](PROVENANCE.md).
