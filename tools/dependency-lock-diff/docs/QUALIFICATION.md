# Standalone download qualification

Dependency Lock Diff 0.1.0 is a reviewed **source-only** release. Qualification
starts from freshly extracted source and clean environments. Actual versions,
counts, outcomes and named skips belong to release `VALIDATION.json`; selected
coverage is not a passing result.

## Required scope and parity boundary

Eight lanes select Windows/Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each creates a new venv without pip or installed distributions and imports
`lock_diff.py` from the chosen extraction. The CLI uses only standard-library/
OS APIs and needs no sibling module.

The 41 original methods comprise 13 parser, 10 comparison, three reference and
15 reader/CLI methods. Their bodies/assertions and the
`ReferenceTests.legacy_validator` helper remain preserved. The original parser-
parity methods use exact pinned `lock_common.py`/`verify_locks.py` public source
under a test-only fixture root. An adapter redirects fixture resolution without
turning those files into CLI dependencies or installed distributions. The
older validator's separate POSIX file-I/O contract is not extended by parity
of its pure parser. Original `.gitattributes` and all five example files retain
exact bytes, including BOM/line endings.

Another 26 copied single-runtime CLI methods select real processes, complete
JSON/exit outcomes, native input guards and input/runtime preservation. This
selects **67 methods per lane, 536 across eight lanes**. Missing/duplicate IDs,
changed original method/helper bodies, zero discovery, wholly skipped modules,
noncontract skips, failures and errors cannot qualify. Actual pass/skip counts
are separate from these selected-method totals.

Applicable hosted hardlink/symlink/junction fixtures must execute. Platform-only
and locally unavailable native-privilege cases require exact method/reason
contracts; do not bypass device policy or mistake a fixture setup failure for
a successful CLI refusal. Both original validator-parity methods must actually
run against the pinned test-only source.

## Source and execution evidence

The source gate checks the finite inventory/manifest, hashes, sizes, Python/
structured-data syntax, module-local links and selected privacy indicators.
It is not perfect secret detection, exclusive-authorship proof or blanket
privacy/rights/security clearance. The ZIP contains no interpreter/dependency
binary, actual lock/result, private original source, artifact or raw log.

All eight lanes independently rebuild committed reviewed source and compare
**both ZIP and build-manifest bytes**. Sorted members and synthetic fixed
archive metadata support deterministic identity. `build.py` and `qualify.py`
refuse optimized Python, including `-O`, `-OO` and active `PYTHONOPTIMIZE`, before
assertions can be disabled. The CLI's normal interpreter contract is separate
from helper refusal.

Existing coverage includes 100 seeded valid locks and 20 malformed variants
against the public validator, 300 independent list-search comparisons, grammar/
name/version/hash adjacency, byte/line/package limits, change precedence,
one-sided null flags, reversal and fixed errors. It also checks side-effect
prohibitions, sampled identity changes, output limits and standalone execution.
Copied consumers select only authored disposable locks, without package
operations, artifact access, dependency resolution or environment inspection.
The comparator writes stdout only.

Runtime/parser/CLI/result behavior is retained. Historical local 41/39/2 and
earlier fictional-process evidence in the public batch review remain separate
from fresh standalone release/download qualification. Exact raw example bytes
are protected rather than normalized to make hashes pass.

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
[USAGE.md](../USAGE.md) supplies six fictional full JSON/exit outcomes and input/
extra/prior-output/runtime preservation checks without editing its driver.

User-owned Python/venvs do not inherently need administrator access. Respect
device policy and OS prerequisites without bypasses. Actual locks, results,
private captures, interpreter trees, personal paths and raw logs stay private.
Publish only designated source assets and sanitized actual validation.

## Limits that remain

Each lock is at most 1 MiB, 6,000 lines, 512 characters/line and 2,000 packages;
two selected inputs total at most 2 MiB. Serialized stdout is at most 4 MiB plus
the final newline. These are not total CPU/memory/deadline or storage quotas.
Output bound failures precede comparison printing, while OS output failure or
interruption can still leave partial capture.

Version text is not ranked or semantically normalized, and declared artifact
hashes are not independently verified. Matching records do not prove installed
state, authentic artifacts, availability, licensing, compatibility, platform
coverage, reproducibility, safe installation or vulnerability status. Real
names/versions/hashes/input digests and change relationships remain identifying.

Sampled checks on ordinary supported single-link files/ancestors are not an
atomic two-input snapshot, hostile-filesystem sandbox, universal deadline,
mount/drive-rebinding, live/network/virtual-provider or power-loss guarantee.
Reads may affect access metadata; Python caches and caller tracebacks/captures
are separate. See the preserved contract in [README.md](../README.md) and
[PROVENANCE.md](PROVENANCE.md).
