# Qualification contract

Version 0.1.0 uses the standard library. Required Windows/Ubuntu archive lanes use
the complete CPython 3.12.16, 3.13.18, 3.14.10, 3.15.2 distributions pinned in
[PYTHON-LOCK.json](../PYTHON-LOCK.json), python-build-standalone 20261110. Preparation
checks whole-archive SHA-256, actual version and executable identity. Each
application environment is fresh, without pip and with zero installed packages.

## Preserved methods and source

Each lane selects 52 original methods and exactly 30 copied CLI methods: 82 per
lane, 656 across eight lanes (416 original, 240 copied). The originals have 80
assertion call sites, 79 in test methods and one in a helper, plus seven helpers.
Original tests and three historical documents remain byte-identical to BASE.
Four original invented source/mapping/preview/receipt fixtures are separately pinned.

Five non-generator runtime files contain 64 top-level definitions; 63 stay unchanged.
The fictional workbook generator's two definitions stay unchanged. Only
`native_windows.exclusive_write` ports the existing-leaf refusal and
CREATE_NEW/OPEN_REPARSE_POINT safeguard with explicit handle/descriptor ownership.
Existing dangling destinations are refused without creating their target; generic
CLI refusal codes remain. Five other runtime/generator files are unchanged. See
[IO-SAFETY.md](../IO-SAFETY.md), [ORIGINS.md](../ORIGINS.md) and historical
[VALIDATION.md](../VALIDATION.md).

Native hardlink and Windows junction fixtures are mandatory. Originals permit
only exact opposite-platform skips. Copied strict hosted Windows checks require
the selected leaf-symlink fixture. Non-strict local execution may skip only that
case's actual Windows privilege error 1314 with exact ID/reason/provenance.
Unexpected skips, unavailable mandatory fixtures or selected methods that never
start fail. Skipped safeguards are not passed safeguards; totals are measured.

The first copied fixture reused an authored expected-count object inside a
deliberately forged receipt. Editing the receipt also changed the fixture's
expectation, while the product correctly recomputed the original source counts.
The initial failed source, logs and proof are retained privately. The fixture
correction separates those objects and checks their independence/stability; it
does not change the product, original tests or refusal rules. Final acceptance
requires corrected fresh evidence with only the documented finite skips.

The independent [guide](../USAGE.md) checks 86 outcomes, 33 complete reconciliation
reports, 262 role inputs and 299 retained files. It authors full typed previews and
reports, distinguishes raw pins from canonical typed content, exercises actual
CSV/XLSX intake and readiness holds, checks all four native file roles and retained
partial output. It is separate from the 82-method lane total. Two early full
semantic/prose reviews precede the first formal guide execution. Attempts and
phase identities are retained honestly rather than relabelled as final evidence.

## Actual parser and arithmetic components

Full archive lanes and the guide measure selected ElementTree, `_elementtree`,
`pyexpat`, `zlib`, `decimal`, `_decimal` module identities before/after execution.
File-backed modules must belong to the selected complete SDK and are SHA-256
recorded; genuine built-ins bind its executable hash. Expat and compiled/runtime
zlib versions are measured, not assumed equal across platforms. C XMLParser/
TreeBuilder and Decimal/Context identities are required.

Actual CLI entry-point children in the copied suite and guide verify those C
bindings and the fresh default Decimal context before and in finally after
execution: precision 28, ROUND_HALF_EVEN, Emin -999999, Emax 999999, capitals 1,
clamp 0, traps DivisionByZero/InvalidOperation/Overflow and no flags. Decimal
normalization uses ambient context; changed library-caller contexts are outside
the qualified scope. Bounded accepted decimals need at most 19 significant digits.
These are selected-SDK component records, not independent library-build
certification or binary reproducibility. Auxiliary original-source evidence must
be distinguished from detailed full-archive component measurements.

Source ZIP, checksums for the other four assets, executable guide, build record
and measured validation record are separate. Rebuilding source under a selected
SDK is distinct from testing copied code in a fresh application environment.
An anonymous consumer may omit a reference rebuild and must preserve that omission
and false identical-reference flags accurately.

The three positive checks are fictional receipt flow, native file guards and
actual row-count recomputation. The ten negative scope flags remain false: no real
records/workbooks, import, source authority, actual store verification, ingestion
run, target changes, receipt authority, exactly-once or production verification.
Readiness is only an explicit-review gate. No formula evaluation, macro execution,
Office process, remote-resource access, input archive extraction, visible layout,
independent writer or general workbook compatibility is qualified. Source ZIP
extraction into an owned test workspace is separate from input-workbook scope.
