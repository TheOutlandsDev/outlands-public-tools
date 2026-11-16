# Qualification contract

Version 0.1.0 is standard-library source. The required Windows/Ubuntu matrix uses
the exact CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2 complete archives in
[PYTHON-LOCK.json](../PYTHON-LOCK.json), from python-build-standalone 20261110.
Preparation verifies the complete archive SHA-256, actual interpreter version and
executable hash. Each application environment is fresh, created without pip and
requires zero installed distributions.

## Selected methods and preservation

Each archive lane selects all 63 original methods and exactly 30 copied-runtime
CLI methods, 93 total. The eight-lane requirement is 744 executions: 504 original
and 240 copied. The originals comprise 25 replay contracts, 16 shared-control
methods and 22 buffer/native boundaries, with 102 assertion call sites and seven
helper definitions. Original test bodies, both invented JSON examples and the
three historical records remain preserved.

Four runtime files contain 57 non-generator top-level definitions; 56 are
unchanged. There is no generator. The only runtime change is the previously
qualified `native_windows.exclusive_write` port: existing-leaf refusal, native
CREATE_NEW with OPEN_REPARSE_POINT and explicit descriptor/handle cleanup. It
refuses an existing dangling destination without creating its target, retaining
generic CLI refusal codes. Three other runtime files remain byte-identical to
the source baseline. Historical [IO-SAFETY.md](../IO-SAFETY.md),
[ORIGINS.md](../ORIGINS.md) and [VALIDATION.md](../VALIDATION.md) retain their bytes.

Original hardlink and Windows junction fixtures are mandatory; only exact
opposite-platform original skips are allowed. The copied suite has selected
platform cases and a Windows leaf-symlink refusal fixture: strict hosted checks
require it; non-strict local execution may skip only its selected actual Windows
error 1314 with exact reason/provenance. Missing mandatory fixture support,
unexplained skips or selected tests that never start fail. Actual pass/skip totals
are measured and never inferred from the 93 selection count.

Copied checks use actual copied CLI entry points and explicit invented full reports.
The separate [executable guide](../USAGE.md) verifies 71 outcomes, 44 reports,
64 inputs and 111 retained files, with independently authored counts/issues/advice.
It covers history beyond selected candidates, conflicts/duplicates, global holds,
aliases across both lists, declared-versus-observed count scopes, limits, no
overwrite and partial retention. It is separate from the 93-test lane total.
Two independent early semantic/prose reviews precede its first formal execution.

## Component evidence and scope

Full archive qualification measures selected `xml.etree.ElementTree`,
`_elementtree`, `pyexpat` and `zlib` files or genuine built-ins, plus reported
Expat and compiled/runtime zlib versions, before/after testing. C XMLParser and
TreeBuilder affinity is required; actual copied CLI/guide entry-point children
check it before and in finally after execution. This supports shared-toolkit
boundary evidence. Product inputs are JSON only; there is no workbook/XML-input
support or arithmetic/Decimal-product context envelope. Selected versions may
differ between platform builds. Complete pinned-SDK identities are not independent
library-build certification or binary reproducibility claims.

The source ZIP, four-target checksums, executable guide, build record and measured
validation record are separate assets. Rebuilding source under a selected complete
SDK is distinct from testing copied code in a fresh no-pip environment. Anonymous
consumer qualification may omit a reference rebuild and must accurately preserve
that omission and false identical-reference flags.

All ten application scope flags remain false: no real records/workbooks, import,
retry, execution authorization, target change, source-record count recomputation,
receipt-authority verification, exactly-once verification or production workflow
verification. Computed accounting for the supplied JSON lists is separate from
the source counts declared inside a batch. A PASS plan is advice, never safe replay,
idempotency, complete history or business approval. Reports and hashes remain
private; native/audit/parser bounds are not an OS sandbox, atomic snapshot or
hardware-durability guarantee.
