# Validation and evidence limits

The dedicated provenance-tools-checks workflow runs Python 3.12/3.13 on Windows
and Ubuntu. It verifies source pins, fictional core contracts, public parser
interoperability, native file boundaries and actual independently copied CLI
workflows. Required native hardlink and symlink/junction fixtures must run;
only the opposite-platform test per tool may skip. Some local filesystems cannot
create those fixtures, so a local skip alone does not qualify the platform.

Tests include actual hashes, canonical manifest pins, typed preview comparison,
forged counts/values/provenance, empty/conflicting input, invented CSV/XLSX,
snapshot boundary/staleness, graph ordering/cycles, stale review pins, exact
selection and filename collision/traversal refusal. Deliberately consistent false
snapshot counts remain marked unverified. All-true review declarations remain
consistency evidence only, without publication authorization.

Actual CLI acceptance uses private disposable fixtures, standalone copied source,
source_check.py, new reports/overwrite refusal, fixed argument errors and the
connected four-module pipeline. No code artifact is executed and no publishing
adapter is invoked. Public source/baseline contracts remain unchanged.

No private original workflow, real records, authenticated reviewer, cryptographic
signature, live source authority, target installation, production calculation,
real publication or browser interface is qualified. Tests are synthetic functional
checks, not an exhaustive security review or proof on every filesystem/OS.
Original-family and whole-drive privacy/rights clearance remain incomplete.
