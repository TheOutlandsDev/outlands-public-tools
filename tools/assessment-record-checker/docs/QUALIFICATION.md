# Standalone download qualification

Assessment Record Checker 0.1.0 is a reviewed source-only release. Qualification
starts from fresh extracted source/clean environments. Actual versions/counts/
outcomes/named skips belong to release `VALIDATION.json`; selected coverage is
not a passing result.

Eight lanes select Windows/Ubuntu Python **3.12, 3.13, 3.14 and 3.15.2**. New
venvs have no pip/installed distributions; in-process imports select actual
extracted `assessment_check.py`. The CLI uses its one script and stdlib/OS APIs,
without sibling tools or donors.

All 44 original method ASTs, 117 total assertions (116 in tests and one in the
reader-error helper) and thirteen namespaced local/shared helper ASTs remain
preserved. `python-ast-fields-json-v1` retains complete fields rather than
interpreter-specific dump formatting; within-version equality remains required.
Only needed shared scaffolding is retained, without unrelated applications.
Runtime and three JSON examples retain exact baseline Git bytes.

One ROOT-relative original subprocess needs an owned collection-shaped test
fixture with an exact extracted runtime copy. Pre/post hashes must match;
`runtime_mirror_test_only`/`runtime_mirror_verified` must be true and
`runtime_mirror_sha256` must match runtime pins. The case must execute without
failure/skip. Independent copied CLI tests use one copied script; no duplicate
runtime, donor or unrelated application is shipped.

Another 26 process CLI methods select complete JSON/exit outcomes, native input
safeguards and input/runtime preservation: **70/lane, 560 across eight lanes**,
comprising 352 original regression and 208 copied CLI cases. Missing/duplicate
IDs, changed originals/helpers, zero discovery, wholly skipped modules,
noncontract skips, failures/errors cannot qualify. Hosted applicable native
fixtures must execute; platform/local capability skips need exact method/reason
contracts. Respect device policy; setup failure must not masquerade as a CLI
refusal. Skips are not passes or substitutes for native hosted evidence.

The finite source gate checks inventory/manifest, hashes/sizes, syntax, local
links and selected privacy indicators. It is not perfect secret detection,
exclusive-authorship proof or blanket privacy/rights/security clearance. No
interpreter/dependency binary, actual ledger/result, evidence, private source
or raw diagnostic log is bundled.

Each lane independently rebuilds committed source and compares **ZIP and
build-manifest bytes**, using sorted members/fixed synthetic metadata.
`build.py`/`qualify.py` refuse optimized Python (`-O`, `-OO`, active
`PYTHONOPTIMIZE`) before assertions can be disabled. CLI behavior is separate.

Preserved coverage includes exact typed references, same-series strictly later
revisions, numeric latest selection including untested submissions, explicit
selection ownership, bad unselected history and relationship-before-latest/
outcome precedence. Open/null, pending/not_run and closure_claimed/not_observed
are checked only as declarations. Counts/privacy/ordered results, strict
schemas/resource bounds, input preservation and fixed errors remain covered.
Six flags stay false: `execution_performed`, `network_probed`, `records_modified`,
`authorization_verified`, `isolation_verified`, `outcomes_verified`.

The unchanged reader samples identities after absolute normalization, without
an original-component suffix precheck. Native spelling observations cannot
establish blanket alias/race/hostile-filesystem safety. Actual fictional Windows
probes on Python 3.12.7/3.15.2 accepted canonical, leaf-dot, leaf-space and
parent-dot forms with exit 0/DECLARED_RECORDS_CONSISTENT; parent-space returned
2/INPUT_PATH_INVALID, preserving input/runtime bytes. Historical local 44/42/2,
609 independent scenarios, 32 CLI scenarios and collection Python 3.12/3.13
evidence are separate from fresh standalone release/download qualification.

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
policy without bypasses. Actual ledgers/IDs/results/evidence, personal paths,
credentials, private source and logs stay private. Publish reviewed source and
sanitized actual validation only.

## Limits that remain

Input is at most 64 KiB; there are 1–128 submissions, 0–128 findings and 0–128
retests, with at most 256 records total. IDs/links/series tokens are at most
40 characters; revisions are integers 1–1000000000. Paths are bounded at
4096 characters/64 parts. These are
not total CPU/RAM/JSON-depth/deadline/storage quotas. Interrupted/failed stdout
can leave partial captures.

Internal consistency proves no executed test/retest, evidence collection/quality,
fix, current build, authorization, isolation or security. Own IDs/statuses can
remain identifying despite omitted relationships/labels/values. No privacy/IP/
licensing/publication clearance follows. Sampled reads are not atomic snapshots,
deny-writer/race or hostile-filesystem guarantees, arbitrary mount/drive alias,
remote/live/provider, universal I/O, ACL privacy or power-loss acceptance. Reads
can affect access metadata; caches/captures/tracebacks remain separate.
See [README.md](../README.md) and [PROVENANCE.md](PROVENANCE.md).
