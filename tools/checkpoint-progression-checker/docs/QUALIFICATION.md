# Qualification contract

Version 0.1.0 is standard-library source. Required Windows/Ubuntu lanes use exact
CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2 complete distributions in
[PYTHON-LOCK.json](../PYTHON-LOCK.json), from python-build-standalone 20261110.
Preparation checks the complete archive SHA-256, actual version and executable
hash. Each application environment is fresh, created without pip and requires
zero installed distributions.

## Selected checks and preserved source

Each archive lane selects all 64 original methods and exactly 30 copied-runtime
CLI methods, 94 total. Eight lanes require 752 executions: 512 original and 240
copied. The originals comprise 26 checkpoint contracts, 16 shared-control methods
and 22 buffer/native boundaries, with 106 assertion call sites and seven helpers.
Original test bodies, two invented JSON examples and three historical records
retain their bytes.

Four runtime files contain 57 non-generator top-level definitions; 56 are unchanged.
There is no generator. Only `native_windows.exclusive_write` ports the previously
qualified existing-leaf refusal and CREATE_NEW/OPEN_REPARSE_POINT safeguards with
explicit descriptor/handle cleanup. It refuses an existing dangling destination
without creating its target and retains generic CLI refusal codes. Three other
runtime files remain BASE-identical. Historical [IO-SAFETY.md](../IO-SAFETY.md),
[ORIGINS.md](../ORIGINS.md) and [VALIDATION.md](../VALIDATION.md) remain untouched.

Native hardlink and Windows junction fixtures are mandatory. Originals permit
only exact opposite-platform skips. The copied suite has selected platform cases
and a Windows leaf-symlink fixture: strict hosted checks require it; non-strict
local runs can skip only that selected actual Windows error 1314 with exact reason
and provenance. Missing mandatory support, unexplained skips and selected tests
that never start fail. Pass/skip totals are measured, not inferred from selections.

The first copied boundary fixture unintentionally prefixed a 48-character batch
ID into a 56-character receipt ID, so the product correctly refused that malformed
receipt row. Its failed source/log/proof remain retained privately. The corrected
positive fixture supplies a valid receipt ID and a separate 49-character refusal
case retains the guard. This is a fixture correction, not a relaxed product limit
or an unchanged-test success claim; release acceptance requires the final selected
methods to pass with only the finite documented skips.

The separate [guide](../USAGE.md) independently checks 81 outcomes, 47 reports,
74 inputs and 124 retained files. It covers contiguous/missing coverage, exact
matching precedence, global holds even with positive resolution counts, duplicate/
conflict/alias accounting, zero-width no-change windows, ordinal/list bounds, native
file guards and partial retention. It is separate from the 94-test lane total.
Two independent early semantic/prose reviews precede its first formal execution.

## Component identity and measured scope

Full archive qualification measures selected `xml.etree.ElementTree`,
`_elementtree`, `pyexpat` and `zlib` files or genuine built-ins, and reported Expat
and compiled/runtime zlib versions, before/after testing. C XMLParser/TreeBuilder
affinity is required; actual copied CLI/guide children check it before and in
finally after execution. This supports shared-toolkit boundary evidence. Product
inputs are JSON only, without workbook/XML-input support or an arithmetic/Decimal
context envelope. Versions can differ between platform builds. Pinned SDK identity
is not independent library-build certification or binary reproducibility.

The source ZIP, four-target checksums, executable guide, build record and measured
validation record are separate assets. A source rebuild under a selected complete
SDK is distinct from testing copied code in a new no-pip environment. Anonymous
consumer qualification can omit a reference rebuild and must accurately retain
the omission and false identical-reference flags.

All ten application scope flags remain false: no real records/workbooks, import,
checkpoint write, previous-checkpoint authority, target change, source-record count
recomputation, receipt authority, exactly-once or production workflow verification.
An eligible suggestion is for explicit review only, never verified source progress,
complete history, safe advancement or execution authorization. Reports remain
private. Cooperative limits/native checks are not OS isolation, atomic snapshots
or hardware-durability guarantees.
