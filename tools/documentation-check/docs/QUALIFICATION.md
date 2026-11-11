# Standalone download qualification

Documentation Check 0.1.0 is distributed as a reviewed source ZIP. Qualification
begins from fresh extracted source, not a checkout with an existing environment.
Actual interpreter versions, discovered/passed/failed/skipped counts and lane
outcomes belong in release `VALIDATION.json`; planned coverage is not a pass.

## Required scope

Eight lanes cover Windows/Ubuntu with Python **3.12, 3.13, 3.14 and 3.15.2**.
Each uses a new venv **without pip or installed distributions**, adjacent
`docs_check.py`/`docs_windows.py` and authored disposable document trees. There
are no third-party package or network/model/account dependencies. Python/OS
prerequisites are separate and retain their own licenses.

The regression baseline contains **five original shared documentation methods
plus 40 existing I/O methods**. Per-method AST comparison preserves the original
five bodies/assertions while minimal standalone scaffolding avoids unrelated
imports from the collection's combined test module. Fresh discovery must find
the selected baseline rather than accidentally testing only module-local I/O.
Another 26 process methods invoke the actual copied two-file runtime. Discovery
must retain all 45 original plus 26 process methods; actual outcomes/skips come
from the accepted source/validation record.

Zero discovered tests, wholly skipped suites, failures and unexpected skips
cannot qualify. Hosted Windows requires applicable native links/junctions to
run; relevant POSIX fixtures remain required. The regression contract allows
five Windows platform skips plus exact optional short-name absence; four
Windows error-1314 cases are optional only outside strict qualification. POSIX
has 19 Windows-native regression skips and two Windows-only process skips
(junction/interruption). Exact method/reason contracts govern every actual
skip. Never count a skip as a pass or change policy to make a fixture run.

## Checks and evidence boundary

The source gate checks the exact selected allowlist/manifest, hashes, sizes,
syntax/data, local document links and selected privacy indicators. It does
not prove perfect secret detection, exclusive authorship or complete security
clearance. Source ZIPs contain no interpreter/dependency binaries, real docs,
reports, held originals, generated workspaces or raw diagnostics.

Source packaging requires committed reviewed Git bytes. All eight lanes repeat
the build and compare both source ZIP and build-manifest bytes against an
independent reference output. Sorted members/synthetic archive metadata support
deterministic comparison. The two helpers, `build.py` and `qualify.py`, use the
standard library and refuse optimized Python (`-O`, `-OO` or `PYTHONOPTIMIZE`)
before assertions can be disabled.

Authored regressions/process fixtures cover the retained limited Markdown/JSON
grammar, code/fence handling, unfetched schemes, local targets/containment,
BOM/newlines, default duplicate-key behavior, NaN/infinity rejection,
exclusions/bounds, native path/identity guards, byte-preserved inputs and
actual stdout JSON/exit statuses. The CLI writes no selected reports/manifests;
explicit shell captures and test receipts are separate private operations.

Exit 0/PASS means documented selected checks passed; exit 1/FAIL means findings;
exit 2/ERROR means a fixed input/output/root/argument failure. Some per-file
errors are findings, not root-level errors. Handled Windows interruption is
exit 130; POSIX behavior is preserved. The original
[FILESYSTEM.md](FILESYSTEM.md) remains byte-identical historical contract/evidence.

## Reproduce privately

From reviewed committed repository source:

```text
python -B packaging/build.py --out NEW_ABSOLUTE_PRIVATE_PACKAGE_DIRECTORY
python -B packaging/build.py --out ANOTHER_NEW_ABSOLUTE_PRIVATE_REFERENCE_DIRECTORY
python -B packaging/qualify.py --packages ABSOLUTE_PACKAGE_DIRECTORY --reference-build ABSOLUTE_REFERENCE_DIRECTORY --workspace NEW_ABSOLUTE_PRIVATE_WORKSPACE --report NEW_ABSOLUTE_PRIVATE_REPORT_JSON
```

Use the selected normal Python and an external
[private workspace](PRIVATE-WORKSPACE.md). Both build outputs must be new with
existing parents and come from the same committed source. `--packages` and
`--reference-build` select those existing artifact directories. Workspace/report
must be new absolute paths with existing parents. Qualification creates fresh
extraction/venv/test work outside source. Run `packaging/qualify.py --help` for
option details; consumer/fictional-tree commands are in [USAGE.md](../USAGE.md).

The reference is optional for local/consumer use. Omitting it records
`identical_zip` and `identical_build_manifest` as false, honestly supplying no
Git-source rebuild proof. All eight hosted release lanes must record both
true. A separately hashed and freshly tested public download is consumer
evidence with its own scope; do not relabel it as an independent Git rebuild.

User-owned prerequisites/venvs do not inherently need administrator access.
Respect device policy and OS prerequisites; do not bypass restrictions. Keep
actual documents/captures, paths, machine/account metadata, interpreter trees
and raw diagnostics outside public assets. Publish sanitized structured
validation with actual versions/counts/skips.

## Limits that remain

Bounds are 10,000 encountered entries and 2 MiB per selected file, not total
byte, CPU, elapsed-time, result-size or memory quotas. Exclusions do not
authenticate omitted material. Markdown parsing is not full CommonMark,
reference-use/anchor/external validation; JSON is not schema/duplicate-key
validation. Target metadata does not establish target content or application
behavior. Default JSON duplicate-key behavior remains deliberate.

Native/POSIX checks are sampled and have filesystem race windows, not atomic
snapshots, a hostile-filesystem sandbox, universal I/O deadlines or remote/live/
power-loss acceptance. Reports contain identifying relative names/line numbers;
they are not anonymous. PASS is documentation hygiene, not a security, privacy,
source-rights or application clearance. Read [PROVENANCE.md](PROVENANCE.md)
and the preserved [filesystem contract](FILESYSTEM.md) before making claims.
