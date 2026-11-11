# Standalone download qualification

Package Layout Checker 0.1.0 is a reviewed **source-only** release. Qualification
starts from freshly extracted source and clean environments. Actual versions,
counts, outcomes and exact skips belong to release `VALIDATION.json`; intended
coverage is not a passing result.

## Required scope and platform contracts

Eight lanes cover Windows/Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each creates a new venv without pip/installed distributions and imports adjacent
`layout_check.py`/`layout_windows.py` from the selected extraction. The tool and
helpers use only the standard library; no network/model/account is required.
Interpreters/OS prerequisites are separately supplied/licensed.

The baseline has **64 methods: 33 original POSIX regressions, three portable
contract methods and 28 native Windows methods**. The 33-method POSIX module
intentionally skips on Windows and must run on supported Linux. This explicit
platform contract is not a generic permission for missing/wholly skipped
coverage. Applicable Windows native cases must execute in strict hosted lanes,
including hardlink/symlink/junction fixtures. Optional short-alias absence and
other platform-only skips need exact method/reason contracts. Do not weaken
discovery/assertion guards or bypass device policy to force a pass.

Another 26 copied-runtime CLI methods select real calls and complete JSON/exit
outcomes, declared-file scope, native guards and input/runtime preservation.
That selects **90 methods per lane, 720 across eight lanes**. Missing/duplicate
IDs, zero discovery, noncontract skips, failures and errors cannot qualify.
Actual pass/skip counts remain separate from these selected-method totals.

## Source and execution evidence

The source gate checks exact inventory/manifest, hashes, sizes, Python/structured-
data syntax, module-local links and selected privacy indicators. It does not
prove perfect secret detection, exclusive authorship or blanket rights/security
clearance. The ZIP contains no interpreter/dependency binary, private original
verifier, actual package/manifest/result or raw log.

All eight lanes independently rebuild committed reviewed source and compare
**both ZIP and build-manifest bytes**. Sorted members and synthetic fixed
archive metadata support deterministic identity. `build.py` and `qualify.py`
refuse `-O`, `-OO` and `PYTHONOPTIMIZE` before assertions can be disabled.

Existing and copied-process coverage retains strict manifest types/duplicates/
paths, byte/read budgets, ordered aggregate results, running-parser syntax,
case-insensitive literal checks, presence-only metadata, unlisted-file exclusion,
source nonexecution, fixed codes/privacy, descriptor/native handle lifetime and
applicable path/link/identity safeguards. Complete results never substitute for
checks of unlisted data. The CLI writes stdout only, without package/report files.

The two runtime files and existing contracts remain preserved. Historical
[WINDOWS.md](WINDOWS.md) wording is retained; only its review hyperlink is made
absolute for standalone resolution. Its historical counts remain separate
from fresh release/download qualification. POSIX descriptor anchoring and
Windows native retained handles are distinct mechanisms, without claimed
semantic identity or atomic snapshots.

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

Consumer runs can omit `--reference-build`, honestly recording `identical_zip`
and `identical_build_manifest` false, without independent Git-source rebuild
proof. All eight hosted lanes require both true. Anonymous asset hashes/source
comparisons and fresh consumer execution provide separate evidence.
[USAGE.md](../USAGE.md) provides fictional complete JSON/exit comparisons and
input/manifest/tree/runtime preservation checks.

User-owned Python/venvs do not inherently need administrator access. Respect
device policy and OS prerequisites without bypasses. Keep actual packages,
private literal rules/manifests, results, captures, interpreter trees, personal
paths and raw logs private. Publish designated reviewed source assets and
sanitized actual validation only.

## Limits that remain

Control bounds are 64 KiB/1–100 declared files, 256 KiB per selected file,
2 MiB reserved content reads/run and 16 literals/row of 1–256 characters each.
These are not total CPU/memory/AST/deadline quotas. Presence-only entries do
not read bodies, but still check supported metadata and size. Only declared
files are opened; unlisted entries are not enumerated or checked.

PASS does not establish an exact export allowlist, privacy, dependency safety,
application/runtime correctness, ownership, licensing or release readiness.
Relative names remain identifying; actual literal rules and stdout/caller
captures require privacy review. Reads may affect OS access metadata and Python
caches are separate. Interrupted stdout can be partial. Trusted quiescent local
inputs and sampled checks are not hostile-filesystem containment, immutable/
atomic snapshots, universal deadlines, mount/drive-rebinding, live/network/
virtual-provider or power-loss acceptance. ACL privacy/streams/topology are
outside these declared checks. See [PROVENANCE.md](PROVENANCE.md).
