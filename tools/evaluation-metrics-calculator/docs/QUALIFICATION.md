# Standalone download qualification

Evaluation Metrics Calculator 0.1.0 is a reviewed source-only release.
Qualification starts from fresh extracted source/clean environments. Actual
versions/counts/outcomes/named skips belong to release `VALIDATION.json`;
selected coverage is not a passing result.

Eight lanes select Windows/Ubuntu Python **3.12, 3.13, 3.14 and 3.15.2**. New
venvs have no pip/installed distributions; in-process imports select actual
extracted `evaluation_metrics.py`. The CLI uses its one script and stdlib/OS
APIs, without sibling tools, scikit-learn or donors.

All 34 original method ASTs, 107 total assertions (96 in tests, 11 in helpers)
and ten namespaced local/shared helpers remain preserved. Fraction-equivalence
and expanded-observation oracle bodies/imports remain exact. Canonical
`python-ast-fields-json-v1` retains full AST fields; within-version equality
is also required. Only needed shared scaffolding is retained, without unrelated
applications. Runtime/three JSON examples retain exact baseline Git bytes.

One ROOT-relative subprocess needs an owned collection-shaped test fixture with
an exact extracted runtime copy. Pre/post hashes must match;
`runtime_mirror_test_only`/`runtime_mirror_verified` must be true and
`runtime_mirror_sha256` must match runtime pins. The case must execute without
failure/skip. Independent copied CLI consumers use one script; no duplicate
runtime, donor or unrelated application is shipped.

Another 26 process CLI methods select whole JSON/exit outcomes, native input
safeguards and input/runtime preservation: **60/lane, 480 across eight lanes**,
comprising 272 original regression and 208 copied CLI cases. Missing/duplicate
IDs, changed originals/helpers/oracles, zero discovery, wholly skipped modules,
noncontract skips, failures/errors cannot qualify. Hosted applicable native
fixtures must execute; local capability/platform skips need exact method/reason
contracts. Respect device policy; setup failure must not masquerade as a CLI
refusal. Skips are not passes or substitutes for native hosted evidence.

The finite source gate checks inventory/manifest, hashes/sizes, syntax, local
links and selected privacy indicators. It is not perfect secret detection,
exclusive-authorship proof or blanket privacy/rights/security clearance. No
interpreter/dependency binary, actual evaluation/result, dataset/model, private
source or raw diagnostic log is bundled.

Each hosted lane independently rebuilds committed source and compares **ZIP and
build-manifest bytes**, using sorted members/fixed synthetic metadata.
`build.py`/`qualify.py` refuse optimized Python (`-O`, `-OO`, active
`PYTHONOPTIMIZE`) before assertions can be disabled. CLI behavior is separate.

Preserved coverage includes expected-row/predicted-column asymmetry, exact raw
formula components, independent Fraction/expanded observation oracles, transpose
and class permutations, perfect/zero/undefined ratios and absent classes inside
nonempty tables. Precision/recall/direct-count F1 denominators are independent;
positive-total accuracy is always defined. Defined zero scores can return exit
0 without meeting any quality threshold. Strict shape/type/resource bounds,
input preservation/fixed errors and absence of model/corpus/network/clock/write
activity remain covered. Five flags stay false: `model_executed`,
`network_probed`, `input_modified`, `ground_truth_verified`, `predictions_verified`.

The unchanged reader samples identities after absolute normalization, without
an original-component suffix precheck. Fictional Windows probes on Python
3.12.7/3.15.2 accepted canonical/leaf-dot/leaf-space/parent-dot forms with exit 0;
parent-space returned 2/INPUT_PATH_INVALID, preserving input/runtime bytes.
No blanket suffix/alias/race/hostile-filesystem guarantee follows. Historical
34/32/2, 547 independent scenarios, 31 CLI scenarios and collection Python
3.12/3.13 evidence are separate from fresh standalone qualification.

## Reproduce privately

From the reviewed committed repository module, with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Package outputs must be new with existing parents and the same reviewed commit.
Qualification inputs must exist; workspace/report must be new absolute paths
with existing parents outside source. Keep work/receipts in an external
[private workspace](PRIVATE-WORKSPACE.md). A consumer can omit the reference,
honestly leaving both `identical_*` flags false without independent Git-source
rebuild proof; hosted lanes require both true. Anonymous asset/source comparison
and fresh execution are separate evidence. [USAGE.md](../USAGE.md) supplies whole
fictional outcomes and input/extra/prior/runtime preservation checks.

User-owned Python/venvs need no inherent administrator access. Respect OS/device
policy without bypasses. Real counts/class IDs/results, datasets/models, personal
paths, credentials, private source and logs stay private. Publish reviewed source
and sanitized actual validation only.

## Limits that remain

Input is at most 64 KiB, classes 1–32, IDs at most 40 characters, cells integer
0–1000000000 and total integer 1–1000000000000. Shape/count/cell/total limits
all apply; all-zero input is invalid. Paths are bounded at 4096 characters/
64 parts. These are not total CPU/RAM/JSON-depth/deadline/storage quotas.
Interruption/stdout failure can leave partial captures.

Arithmetic proves no ground truth, prediction/model/data provenance, quality,
representativeness, independence, leakage prevention, confidence or rights.
Class IDs/counts/ratios remain identifying and can reconstruct binary confusion
counts. No anonymity/IP/licensing/publication clearance follows. Sampled reads
are not atomic snapshots, deny-writer/race/hostile-filesystem guarantees,
arbitrary mount/drive alias, remote/live/provider, universal I/O, ACL privacy
or power-loss acceptance. Reads can affect access metadata; caches/captures/
tracebacks remain separate. See [README.md](../README.md) and
[PROVENANCE.md](PROVENANCE.md).
