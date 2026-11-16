# Qualification contract

Version 0.1.0 is standard-library source. The required Windows/Ubuntu matrix uses
the exact CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2 complete archives in
[PYTHON-LOCK.json](../PYTHON-LOCK.json), from python-build-standalone 20261110.
Preparation verifies the whole archive SHA-256, actual interpreter version and
executable hash. Each application environment is freshly created without pip and
requires zero installed distributions.

## Selected source and checks

Each lane selects all 54 original methods and exactly 30 copied-runtime CLI
methods, 84 total; the eight-lane requirement is 672 executions (432 original,
240 copied). The originals retain 84 assertion call sites and seven helper
definitions. Their contract, shared-control and buffer/native-boundary tests are
distinct from this mapping-only CLI's product scope. All original test bodies,
two original JSON examples and three historical records remain preserved.

The five runtime files contain 67 non-generator top-level definitions; 66 remain
unchanged. No generator exists. Only `native_windows.exclusive_write` changes,
using the previously qualified existing-leaf check and native CREATE_NEW with
OPEN_REPARSE_POINT plus explicit descriptor/handle cleanup. It refuses an existing
dangling destination without creating its missing target, retaining generic CLI
refusal codes. Four other runtime files are byte-identical to the source baseline.
Historical [IO-SAFETY.md](../IO-SAFETY.md), [ORIGINS.md](../ORIGINS.md) and
[VALIDATION.md](../VALIDATION.md) retain their original bytes and limits.

Native hardlinks and Windows junctions are mandatory original fixtures. Originals
permit only exact opposite-platform skips. The copied suite has selected platform
fixtures and a Windows leaf-symlink refusal case: strict hosted checks require it;
non-strict local execution can skip only that selected case on an actual Windows
error 1314, with exact reason and provenance. Missing hardlink/junction support,
unexpected skips and unstarted selected tests fail. Actual pass/skip totals are
measured, never inferred from the selection count.

Copied tests exercise actual copied script entry points against fictional mapping
declarations. The separate [executable guide](../USAGE.md) independently verifies
86 outcomes, 23 full reports, 79 authored inputs and 105 retained files. It checks
source-header omission, exact change-code order, canonical/raw pin distinctions,
both embedded-map refusal positions, limits, no overwrite and retained partial
output. The guide is separate from the 84-test lane total. Two independent early
semantic reviews precede its first formal execution.

## Selected Python and measured scope

Full archive qualification measures `xml.etree.ElementTree`, `_elementtree`,
`pyexpat` and `zlib` files or genuine built-ins under the selected complete SDK,
plus reported Expat and compiled/runtime zlib versions, before/after testing.
C XMLParser/TreeBuilder bindings are required. The copied CLI children and guide
check actual affinity before and in `finally` after script execution. These XML
components support shared-toolkit boundary evidence; product inputs are JSON.
Versions may differ between selected platform builds. This is selected pinned-SDK
identity, not independent library-build certification or binary reproducibility.

The preserved `intake.py` contains record/CSV/XLSX/Decimal conversion routines,
but the mapping CLI uses only declaration validation. Their presence/import does
not establish exercised record conversion, workbook support or an arithmetic
product/context envelope. The report's fixed false row/receipt flags are not
authenticated import or transaction evidence.

The source ZIP, four-target checksums, executable usage guide, build record and
actual validation records remain separate assets. A source rebuild under a
selected complete SDK is distinct from testing copied code in a new environment.
Anonymous consumer qualification may deliberately omit a reference rebuild and
must report that omission and false identical-reference flags accurately.

All ten application scope flags remain false: no real records/workbooks, import,
source transformation, verified compatibility, inferred rename, row validation,
external-resource following, source-completeness proof or production verification.
Reports are private, not anonymized. Limits and sampled native checks assume
trusted quiescent inputs; they are not OS isolation, atomic-snapshot or hardware
durability guarantees.
