# Standalone download qualification

Environment Contract Checker 0.1.0 is reviewed source only. Qualification starts
from fresh extraction/clean environments. Actual versions/counts/outcomes/named
skips belong to release `VALIDATION.json`; selected coverage is not a pass.

Eight lanes select Windows/Ubuntu Python **3.12, 3.13, 3.14 and 3.15.2**. New
venvs have no pip/installed distributions. Imports select extracted checker/
backend files; copied consumers select that pair and `examples/make_fixture.py`,
without sibling tools/dependencies. No selected target/program body is read,
imported or executed.

Retain 103 originals (53 shared regression, 50 I/O), 173 assertion calls
(166 in tests, seven in helpers) and 21 helpers (ten `regression:`, eight `io:`,
three `shared:`). Two original ROOT-relative CLI cases need an owned collection-
shaped mirror of exact checker/backend/generator files, verified before/after
with creation count one. Normal cases use actual source boundaries; no duplicate
runtime is shipped. `python-ast-fields-json-v2` retains actual fields, adding
eager `is_lazy: 0` only where older Import/ImportFrom nodes lack it. Nonzero
values remain distinct. Within-version equality and complete cross-version
preservation objects/maps are required without dropped fields or hash waivers.

Add 30 copied checker/generator CLI methods: **133/lane, 1,064 across eight
lanes**, comprising 824 regression and 240 copied CLI cases. Missing/duplicate
IDs, zero discovery, wholly skipped modules, changed originals, noncontract
skips or failures/errors cannot qualify. Applicable hosted native fixtures must
run. Local capability/platform skips need exact method/reason contracts; setup
failure must escape expected errors. Skips are not passes. Legacy I/O discovery
selects only original `test_io_safety.py` (50 methods); new consumers belong to
dedicated fresh-environment lanes.

Three reviewed changes are allowed: checker/generator source-boundary constant
blocks plus the Windows report writer's observed-existing-leaf pre-open guard.
Literal collection placement protects the collection, otherwise the standalone
module folder; this is not Git discovery. All other function bodies, historical
I/O text and three original JSON controls remain preserved. The corresponding
boundaries are `runtime_bodies_preserved_except_report_guard` and
`windows_report_leaf_guard_repaired`; whole-code-file baseline equality would
be false. Applicable native existing/dangling output checks and controlled
no-open checks must validate guard ordering. Local Win1314 limits do not prove
CRT target creation or substitute for native hosted checks. A precheck retains
race windows and establishes no atomicity or hostile-filesystem containment.

Checker VERSION/--version already report 0.1.0; the generator has no version
option. Per-run reviewed-code stability is separate from baseline equality for
all three repaired files. Each hosted lane independently rebuilds committed
source and compares **ZIP and build-manifest bytes** with fixed synthetic archive
metadata. Extraction/import/source-manifest/runtime hashes and exact discovery/
skip contracts are checked. `build.py`/`qualify.py` refuse optimized Python
(`-O`, `-OO`, active `PYTHONOPTIMIZE`); CLI behavior is separate. The finite source
gate is not perfect secret detection, authorship proof or blanket rights clearance.

## Reproduce privately

From the reviewed committed repository module, with selected normal Python:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Package outputs must be new with existing parents and the same reviewed commit.
Inputs must exist; workspace/report must be new absolute external paths with
existing parents. Keep receipts in a [private workspace](PRIVATE-WORKSPACE.md).
Consumers may omit reference rebuild, honestly leaving both `identical_*` flags
false without independent Git-source rebuild proof; hosted lanes require both
true. Anonymous asset/source comparison and fresh execution are separate evidence.
[USAGE.md](../USAGE.md) supplies full fictional outcomes and byte preservation.

Coverage retains control schemas/BOM/duplicate-key handling, selected-root/search
and missing/unknown/unsafe distinctions, static Windows suffixes, POSIX execute-
access metadata and unverified observations. Target-body reads/import/execution,
PATH/PATHEXT discovery and service probes remain outside the tool. Reports,
missing protected program scopes, generator new-only output, failed/unconfirmed
outputs and actual native fixtures need their own evidence. No success proves
runtime version, compatibility, startability or setup readiness.

## Historical evidence and limits

Preserved [IO-SAFETY.md](../IO-SAFETY.md) records historical 53 original/50 I/O
tests, 24 copied processes and frozen-result/decoded-JSON comparisons. Earlier
unchanged-generator/backend wording predates these repairs. Python 3.12/3.13
collection evidence is separate from fresh archive qualification. Preserve
failures/skips and require actual current receipts.

Controls are bounded at 64 KiB each; requirements at 128; program dirs at 16;
relative names at 240 characters/32 parts. The 2,048-probe/five-second between-
probe budget cannot interrupt blocked metadata calls or bound the whole command.
These are not total CPU/RAM/JSON-depth/storage quotas. Report failures can leave
partial or complete-looking unconfirmed output; generator failures can leave
partial new trees. No overwrite or automatic cleanup occurs.

Use one operator, canonical paths and quiescent trusted inputs. Metadata and
control/report I/O have distinct checks; no blanket alias refusal, atomic
snapshot, writer denial, hostile-filesystem sandbox, ACL privacy or encryption
is established. Remote/cloud/live providers, mounts/rebinding, all-stream
inspection, blocked I/O and power loss remain outside acceptance. Metadata calls
can use OS network storage and affect access metadata. IDs/statuses/attestations
remain identifying. User-owned prerequisites need no inherent administrator
access; respect device policy without bypasses. Publish reviewed source/sanitized
actual validation only, excluding records, paths, credentials, installed/generated
programs, binaries, private originals and raw logs. See [README.md](../README.md)
and [PROVENANCE.md](PROVENANCE.md).
