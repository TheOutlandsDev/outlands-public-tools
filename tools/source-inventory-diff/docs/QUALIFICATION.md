# Standalone download qualification

Source Inventory Diff 0.1.0 is a reviewed **source-only** release. Qualification
starts from freshly extracted source and clean environments. Actual versions,
counts, outcomes and exact skips belong to release `VALIDATION.json`; selected
coverage is not a passing result.

## Required scope and test boundary

Eight lanes select Windows/Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each creates a new venv without pip or installed distributions and imports
`inventory_diff.py` from the chosen extraction. Only standard-library/OS APIs
are required. The single-script CLI needs no sibling module.

The 45 original methods comprise 13 parser, 17 comparison and 15 reader/CLI
methods. Their bodies/assertions remain preserved. The compatibility method
uses two pinned public Source Inventory source files under a test-only fixture
root; the adapter redirects that fixture root while preserving method bodies.
The producer pair is not a runtime dependency or newly bundled interpreter.
Original `.gitattributes` and fictional controls retain exact bytes, including
line endings; their CSV hashes are byte-sensitive.

Another 26 copied-runtime CLI methods select real processes, complete JSON/exit
outcomes, native input guards and input/runtime preservation. This selects
**71 methods per lane, 568 across eight lanes**. Missing/duplicate IDs, changed
original method bodies, zero discovery, noncontract skips, failures and errors
cannot qualify. Actual passed/skipped counts remain separate from these totals.
Applicable hosted native link/hardlink/junction cases must execute. Platform-only
and locally unavailable privilege cases require exact method/reason contracts;
do not bypass device policy or turn fixture failures into successful CLI refusals.

## Source and execution evidence

The source gate checks the finite inventory/manifest, hashes, sizes, Python/
structured-data syntax, module-local links and selected privacy indicators.
It is not perfect secret detection, exclusive-authorship proof or blanket
privacy/rights/security clearance. The ZIP contains no interpreter/dependency
binary, held original source, real inventory/result or raw diagnostic log.

All eight lanes independently rebuild committed reviewed source and compare
**both ZIP and build-manifest bytes**. Sorted members and synthetic fixed
archive metadata support deterministic identity. `build.py` and `qualify.py`
refuse `-O`, `-OO` and `PYTHONOPTIMIZE` before assertions can be disabled. The
runtime CLI's normal interpreter contract is separate from helper refusal.

Existing coverage includes 200 seeded comparisons against independent
list-search/grouping logic, exact fields/hashes/escaping, coverage/skip/name
ambiguity, reversal/permutation invariants, 10,000-row grouped hints, parser/
reader/output limits, sampled identity changes, side-effect prohibitions and
single-script standalone execution. Grouping avoids quadratic rename pairs;
it still does not establish a rename or verify a source body.

Copied CLI consumers use only authored disposable controls. Successful paths
read four fixed controls without enumerating extras or reopening reported
bodies; stdout is the sole result channel. No runtime/parser/result-contract
change is part of standalone packaging. Historical local 45/43/2 evidence in
the README is separate from fresh release/download qualification.

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
hash/source comparisons and fresh consumer execution are separate evidence.
[USAGE.md](../USAGE.md) supplies fictional full JSON/exit and control/runtime
preservation checks, with fixed invented timestamps distinguished from real
capture metadata.

User-owned Python/venvs do not inherently need administrator access. Respect
device policy and OS prerequisites without bypasses. Actual controls, output,
private captures, interpreter trees, personal paths and raw logs stay private.
Publish only designated reviewed source assets and sanitized actual validation.

## Limits that remain

Per selected run: CSV 16 MiB, summary 1 MiB, 10,000 rows, decoded path 4,096
characters, declared file 64 MiB and total selected bytes 256 MiB. Summary JSON
depth/value-node limits are 16/50,000; serialized stdout is at most 32 MiB plus
its final newline. These are not total CPU/memory/deadline or storage quotas.

The declared file/total sizes describe supplied metadata rather than reopened
body sizes. Hash agreement, matching selected records and coverage declarations
do not establish truthful or authentic reports, equivalent roots, complete
capture, ownership, licensing, privacy or release readiness. Names/digests/times
remain identifying. A consistent CSV-plus-summary replacement can pass without
an independent trust anchor.

Ordinary supported single-link files/ancestors and sampled identity checks do
not provide an atomic four-control snapshot, hostile-filesystem sandbox,
universal deadline, mount/drive-rebinding, live/network/virtual-provider or
power-loss guarantee. Reads can affect access metadata; Python caches and caller
tracebacks/captures are separate. Interrupted stdout can remain partial. See
[PROVENANCE.md](PROVENANCE.md) and the preserved contract in [README.md](../README.md).
