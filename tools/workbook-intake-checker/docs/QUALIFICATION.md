# Qualification contract

Version 0.1.0 is a source-only, standard-library release. The required matrix uses
Windows and Ubuntu with the exact CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2
archives in [PYTHON-LOCK.json](../PYTHON-LOCK.json), selected from the 20261110
python-build-standalone release. Preparation verifies the complete archive hash,
actual interpreter version and executable hash. Each qualification uses a new
environment without pip and requires zero installed distributions.

## Selected checks and preservation

Each archive lane selects 47 original methods and exactly 30 copied-runtime CLI
cases, 77 total; the eight-lane requirement is 616 executions (376 original and
240 copied). The originals comprise 25 intake and 22 buffer/native-boundary
methods. They contain 76 assertion call sites and five helper definitions
(one top-level mutation helper and four class helpers). Runtime code has 54
non-generator top-level definitions; 53 remain unchanged, alongside both generator
definitions. Original test bodies and the three original example JSON/CSV fixtures
remain preserved.

Only `native_windows.exclusive_write` changes: the narrow previously qualified
Windows port checks an existing leaf before opening, uses exclusive native
creation without following a reparse point and owns file-descriptor/handle cleanup.
This refuses an existing dangling destination instead of creating its missing
target. The port retains the generic CLI refusal codes. The other three runtime
files remain byte-identical to the source baseline. Historical [IO-SAFETY.md](../IO-SAFETY.md),
[ORIGINS.md](../ORIGINS.md) and [VALIDATION.md](../VALIDATION.md) are retained records;
they do not replace current release evidence.

Native hardlinks and Windows junctions are mandatory fixtures. Original tests
permit only the opposite-platform boundary skip. The copied suite additionally
has platform-specific fixtures and a Windows leaf-symlink fixture: strict hosted
qualification requires it; local non-strict checks may skip only the selected
case for an actual Windows error 1314 with exact reason/provenance. Missing
hardlink/junction support, unexplained skips and missing selected tests fail.
Actual pass/skip counts are measured in each receipt and never inferred from the
77 selection count. A skipped test does not count as passed.

The copied suite exercises actual copied CLI entry points and guarded file roles
using invented CSV/XLSX buffers. The executable [guide](../USAGE.md) separately
checks complete independently authored reports and artifact bytes: 78 outcomes,
28 reports, 71 fixtures and 103 retained files. It covers duplicates/conflicts,
row accounting, whole-batch readiness, exact selection, unsupported unselected
sheet content, mapping/format limits, no overwrite and partial-write retention.
The guide is not added to the 77-test lane total.

## Selected Python components and context

The full archive qualifier measures the actual selected Python files (or genuine
built-in modules) for `xml.etree.ElementTree`, `_elementtree`, `pyexpat` and `zlib`,
plus reported Expat and compiled/runtime zlib versions, before and after testing.
It requires the C `XMLParser` and `TreeBuilder` bindings. Versions may differ
between selected platform builds; these are identities within a SHA-pinned Python
distribution, not independent library-build certification.

Decimal measurements bind `decimal`/`_decimal` module identities and C `Decimal`/
`Context` aliases, with default precision 28, `ROUND_HALF_EVEN`, Emin −999999,
Emax 999999, capitals 1, clamp 0, only DivisionByZero/InvalidOperation/Overflow
traps active and no flags set. Actual CLI entry-point children in the copied
suite and guide check their XML and Decimal bindings/context before and in
`finally` after execution. Library calls
under modified ambient Decimal contexts remain outside qualification. There is
no context-independence, formula-evaluation or Excel-compatibility claim.

## Evidence and limits

The release includes a source ZIP, checksums, this tool's executable usage guide,
a build record and measured validation records. Rebuilding a ZIP with another
selected complete SDK is distinct from testing a copied application in a fresh
no-pip environment. Anonymous download qualification may deliberately omit a
second reference build; receipts must report that omission truthfully.

All selected examples are fictional. No real records/workbooks, imports, source
transformations, evaluated formulas, executed macros, Office process, external
resources, visual layout or production workflow is verified. Accepted values,
mappings, positions and exact fingerprints remain private by default. The bounds
are application checks, not operating-system isolation, and file stability is
not an atomic multi-input snapshot or hardware durability proof.
