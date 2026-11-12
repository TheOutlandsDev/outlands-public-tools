# Standalone download qualification

Release Preflight 0.1.0 is a reviewed source-only release. Qualification starts
from fresh extracted source and clean environments. Actual versions, counts,
outcomes and named skips belong to release `VALIDATION.json`; selected coverage
is not a passing result.

Eight lanes select Windows/Ubuntu Python **3.12, 3.13, 3.14 and 3.15.2**. New
venvs have no pip/installed distributions. Runtime imports select actual
extracted `preflight.py`; Windows additionally uses adjacent
`preflight_windows.py`. Copied CLI consumers use these two files without sibling
tools/installed dependencies. No candidate executable is imported or run.

All 75 original methods remain selected: 28 shared release regression methods
and 47 module I/O methods. Preserve 103 assertion calls: 97 inside test methods
and six inside helpers, with 16 namespaced helpers (five `regression:`, eight
`io:`, three `shared:`). Original AST equality and exact maps remain required.
`python-ast-fields-json-v2` retains all actual AST fields and supplies
`is_lazy: 0` only where a legacy `Import`/`ImportFrom` node lacks Python 3.15's
explicit eager-import field. Nonzero values stay distinct; no field is dropped
or hash waived. Within-version equality and matching full preservation objects/
maps across selected interpreters are both required.

Add 26 copied process CLI methods: **101/lane,
808 across eight lanes**, comprising 600 original regression and 208 copied CLI
cases. Missing/duplicate IDs, zero discovery, wholly skipped modules, changed
original assertions/helpers, noncontract skips or failures/errors cannot qualify.
Applicable hosted native fixtures must execute. Local capability/platform skips
need exact method/reason contracts; setup failure must not masquerade as a CLI
refusal. Skips are not passes or substitutes for hosted native evidence.

Only the source-boundary constant block changes: add `_SOURCE_DIRECTORY` and
revise `REPOSITORY` for literal structural collection placement, protecting the
collection; otherwise protect the enclosing standalone runtime directory.
All runtime function bodies, backend bytes and three original examples remain
preserved. `runtime_bodies_preserved` is the appropriate boundary; whole-core
baseline byte identity would be false. Report exclusion must work in extraction/
copied-runtime layouts as well as collection placement. No `--version` is added;
VERSION is package metadata.

Each hosted lane independently rebuilds committed source and compares **ZIP and
build-manifest bytes**, using sorted members/fixed synthetic metadata. Fresh
extraction/source-manifest/import/runtime pins and exact contracts are verified.
`build.py`/`qualify.py` refuse optimized Python (`-O`, `-OO`, active
`PYTHONOPTIMIZE`) before assertions can be disabled; CLI behavior is separate.
The finite source gate checks inventory, hashes/sizes, syntax, local links and
selected privacy indicators. It is not perfect secret detection, authorship
proof or blanket rights/privacy/security clearance.

Preserved coverage includes trusted raw control pins, JSON keys/constants,
schemas/path case/prefix rules, exact candidate sets, payload/resource bounds,
selected-current ADD/REPLACE/UNCHANGED decisions, unselected-current preservation,
structural launcher checks and no execution. Reads/writes and real native
hardlink/symlink/junction/path/stream fixtures retain exact capability contracts.
New-report exclusivity, short writes, flush/readback failure and unconfirmed
output need their own evidence; existence/parseability is not completion.

## Reproduce privately

From the reviewed committed repository module, with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Package outputs must be new with existing parents and the same reviewed commit.
Qualification inputs must exist; workspace/report must be new absolute paths
with existing parents outside source. Keep receipts in an external
[private workspace](PRIVATE-WORKSPACE.md). Consumers may omit reference rebuild,
honestly leaving both `identical_*` flags false without independent Git-source
rebuild proof; hosted lanes require both true. Anonymous asset/source comparison
and fresh execution are separate evidence. [USAGE.md](../USAGE.md) provides
complete fictional outcomes and input/runtime/prior-output preservation checks.

User-owned Python/venvs need no inherent administrator access. Respect OS/device
policy without bypasses. No interpreter/dependency binary, actual package,
manifest/specification, configuration, private source or raw diagnostic log is
bundled. Report/capture names/hashes remain private. Publish reviewed source and
sanitized actual validation only.

## Historical evidence and remaining limits

Preserved [IO-SAFETY.md](../IO-SAFETY.md) records historical original 28-method,
new 47-method, copied-process and 100-tree parity evidence. Its collection-layout
wording predates the standalone scope assignment. Historical Windows/Python
3.12.7 counts and Windows/Ubuntu 3.12/3.13 collection CI are not fresh archive
qualification. Preserve failures/exact skips and require actual current receipts.

Metadata is bounded at 1 MiB each; manifest files at 4,096; each payload at
256 MiB, total at 1 GiB per pass; candidate enumeration at 8,192 entries.
Relative paths permit 240 characters/32 parts; launcher arguments permit
64 strings, 2,048 characters each/8,192 total. These are not total CPU/RAM/
JSON-depth/deadline/storage quotas. Verification can reread selected bytes.

No candidate execution, installation, plan application, backup, rollback,
process stop/start, network probing or runtime readiness is established.
`execution_performed` stays false. Pins are not authorship/authenticity/rights
proof. Use one operator, canonical paths and quiescent trusted local trees;
sampled identities/held handles are not atomic snapshots, writer denial or
hostile-filesystem guarantees. Drive/mount aliases, remote/cloud/live providers,
all-stream inspection, blocked I/O, ACL privacy and power loss remain outside
acceptance. Reads may affect access metadata; stdout/failed reports can be partial.
See [README.md](../README.md) and [PROVENANCE.md](PROVENANCE.md).
