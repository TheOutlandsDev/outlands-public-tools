# Standalone download qualification

Connection Plan Checker 0.1.0 is a reviewed source-only release. Qualification
starts from freshly extracted source and clean environments. Actual versions,
counts, outcomes and named skips belong to release `VALIDATION.json`; selected
coverage is not a passing result.

## Required source and test boundary

Eight lanes select Windows/Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each creates a new venv without pip or installed distributions and imports
`connection_check.py` from the selected extraction. The single-script CLI uses
standard-library/OS APIs, without a sibling tool or donor.

All 41 original test method bodies, 103 assertion calls and nine required helper
ASTs remain preserved. Explicit `python-ast-fields-json-v1` encoding retains
full AST fields instead of interpreter-specific dump formatting; original/
adapted within-version equality remains required. Only needed shared
`Fixture`/`load` scaffolding is retained, without unrelated application imports.
Adapter globals select the actual extracted checker/script for in-process and
subprocess checks. Runtime and both examples retain exact baseline Git bytes.

One preserved ROOT-relative subprocess method needs an owned collection-shaped
test hierarchy with an exact copy of the actual extracted `connection_check.py`.
Pre/post hashes must match; qualification requires `runtime_mirror_test_only`
and `runtime_mirror_verified` true, with `runtime_mirror_sha256` equal to actual
runtime pins. The subprocess case must execute without skip/failure. This
fixture is separate from in-process extraction imports and independent copied
CLI tests; no duplicate runtime or unrelated application is bundled.

Another 26 copied single-script CLI methods select real processes, complete
JSON/exit outcomes, native input safeguards and input/runtime preservation.
This selects **67 per lane, 536 across eight lanes**: 328 original regression
and 208 copied CLI cases. Missing/duplicate IDs, changed methods/helpers, zero
discovery, wholly skipped modules, noncontract skips, failures and errors cannot
qualify. Selected totals are separate from actual passes/skips.

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

Preserved coverage includes exact schema/types/counts/byte limits, tuple grouping,
all repeated members, TCP/UDP and address-family separation, first-appearance/
declaration ordering, malformed JSON, input safeguards/preservation and fixed
error privacy. Authored CLI consumers check whole results and ordinary/native
input behavior; these are declaration fixtures, never tests of real listeners.

The checker reads one selected control and prints stdout without socket/DNS,
listener/process inspection, program execution, command generation, installation
or configuration changes. All four flags stay false: `network_probed`,
`programs_executed`, `runtime_verified`, `availability_verified`. Path components
are checked after absolute normalization; no original suffix guard is added.
Actual fictional Windows probes on Python 3.12.7/3.15.2 accepted canonical,
leaf-dot, leaf-space and parent-dot forms with exit 0; parent-space returned
exit 2/`INPUT_PATH_INVALID`, retaining input/runtime bytes. These mixed measured
observations do not establish blanket suffix refusal or universal alias safety.

The unchanged runtime already supplies these tuple/input/fixed-error checks.
Historical local 41/39/2 and collection Python 3.12/3.13 evidence remain separate
from fresh standalone release/download qualification. The historical native-
error chaining correction already exists in the preserved baseline.

## Reproduce privately

From the reviewed committed repository module, with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Package outputs must be new, with existing parents and the same reviewed commit.
Qualification input directories must exist; workspace/report must be new
absolute paths with existing parents outside source. Generated work/receipts
stay in an external [private workspace](PRIVATE-WORKSPACE.md).

Consumer qualification may omit `--reference-build`, honestly recording both
`identical_*` flags false without independent Git-source rebuild proof. All
hosted lanes require both true. Anonymous asset/source comparisons and fresh
consumer execution provide separate evidence. [USAGE.md](../USAGE.md) supplies
isolated fictional whole JSON/exit outcomes and input/extra/prior/runtime
preservation checks.

User-owned Python/venvs do not inherently need administrator access. Respect
device policy/OS prerequisites without bypasses. Real plans/IDs/results, personal
paths, credentials, private source and raw logs stay private. Publish reviewed
source and sanitized actual validation only.

## Limits that remain

Input is at most 64 KiB, with 1–128 bindings, IDs at most 40 characters and
integer ports 1–65535. Paths have 4,096-character/64-part bounds. These are not
total CPU/memory/JSON-depth/deadline or storage quotas. Interruption or stdout
failure can leave partial captures.

No declaration proves listener existence, availability, startup, connection
success, reuse/exclusivity/dual-stack behavior or safe operational configuration.
IDs/counts/conflict relationships remain identifying despite omitted binding
values. No privacy/IP/licensing or publication clearance follows.

Sampled identity checks are not atomic snapshots, deny-writer/race guarantees,
hostile-filesystem containment, arbitrary mount/drive aliases, live/network/
virtual-provider, universal I/O, ACL privacy or power-loss acceptance. Reads
can affect access metadata; Python caches/caller tracebacks/captures are separate.
See [README.md](../README.md) and [PROVENANCE.md](PROVENANCE.md).
