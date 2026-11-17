# Qualification contract

Version 0.1.0 is standard-library source. Required Windows/Ubuntu lanes use exact
CPython 3.12.16, 3.13.18, 3.14.10, 3.15.2 complete distributions in
[PYTHON-LOCK.json](../PYTHON-LOCK.json), from python-build-standalone 20261110.
Preparation checks complete archive SHA-256, actual version and executable hash.
Each application environment is fresh, without pip, with zero installed packages.

## Selected source and checks

Each archive lane selects 63 original methods and exactly 30 copied CLI methods:
93 total, 744 across eight lanes (504 original, 240 copied). The originals contain
105 assertion call sites and seven helpers. Original test bodies, two invented
JSON examples and three historical records retain their bytes.

Four runtime files contain 57 non-generator top-level definitions; 56 remain
unchanged. There is no generator. Only `native_windows.exclusive_write` ports the
previously qualified existing-leaf refusal and CREATE_NEW/OPEN_REPARSE_POINT
safeguards with explicit handle/descriptor ownership cleanup. An existing dangling
destination is refused without creating its target; generic CLI refusal codes are
preserved. Three other runtime files stay BASE-identical. Historical
[IO-SAFETY.md](../IO-SAFETY.md), [ORIGINS.md](../ORIGINS.md),
[VALIDATION.md](../VALIDATION.md) remain untouched.

Native hardlink and Windows junction fixtures are mandatory. Originals permit
only exact opposite-platform skips. The copied suite includes selected platform
cases and a Windows leaf-symlink fixture: strict hosted checks require it;
non-strict local runs can skip only that selected actual Windows error 1314 with
exact reason/provenance. Missing mandatory support, unexplained skips and selected
methods that never start fail. Actual pass/skip totals are measured.

The independent [guide](../USAGE.md) verifies 71 outcomes, 44 complete reports,
64 input files and 111 retained files. Noncontiguous and empty cohorts, declared
totals versus observed list accounting, exact matching precedence, duplicate/
conflict/alias holds, row/list/JSON bounds, native guards and partial retention are
separate from the 93-test lane total. Two early full semantic/prose reviews precede
the guide's first formal run. Retained attempts remain distinct from final evidence.

## Components and interpretation

Full archive qualification measures selected `xml.etree.ElementTree`,
`_elementtree`, `pyexpat`, `zlib` files or genuine built-ins, and reported Expat and
compiled/runtime zlib versions before/after testing. Actual CLI entry-point
children in the copied suite and guide assert C XMLParser/TreeBuilder identities
before and in finally after execution. This supports shared-toolkit boundary
evidence, not XML ingestion by this JSON-only product. No arithmetic/Decimal
context envelope applies. Components belong to the complete pinned SDK; versions
may differ across platform builds, without independent library-build certification.

The source ZIP, four-target checksums, executable guide, build record and measured
validation record are separate assets. Rebuilding source under a selected SDK is
distinct from running copied code in a new no-pip environment. An anonymous
consumer may omit a reference rebuild and must retain that omission and false
identical-reference flags accurately.

All ten scope flags remain false: no real records/workbooks, import, actual-store
verification, ingestion-run execution, target changes, source-row recomputation,
receipt authority, exactly-once or production-workflow verification. The positives
cover fictional cohort flow and native file guards only. A PASS is declaration
consistency within supplied inputs, not authenticated commits, source completeness,
verified store totals, approval to execute or a safe replay guarantee. Counts and
fingerprints remain private. Bounds are cooperative, not an OS sandbox or atomic
snapshot, and do not prove hardware durability.
