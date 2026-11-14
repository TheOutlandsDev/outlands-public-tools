# Qualification contract — 0.1.0

This record defines release gates. Accepted `VALIDATION.json` attached to the
source release records actual outcomes for its reviewed commit. Required
selections are not assumed passes. The unchanged [historical validation](VALIDATION.md)
remains a distinct earlier source/platform record.

## Exact source and interpreter identity

The source ZIP contains thirty allowlisted source files plus
`SOURCE-MANIFEST.json`, 31 members: original MIT parser/comparison/support,
tests, authored docs/generator and qualification/build helpers. It excludes
interpreters, real snapshots, binaries, generated reports, raw logs and private
methods. Hashes/build manifest bind the exact ZIP; unsigned hashes show byte
consistency rather than authentic authorship, rights or effective configuration.

`PYTHON-LOCK.json` pins CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2 with the
20261110 standalone archive recipe for Windows and Ubuntu. Preparation verifies
archive SHA-256, actual version and actual base executable SHA-256. Archive
lanes use new `venv --without-pip` environments with zero distributions. No
Python packages, XML/native/Android dependency, administrator permission or
global interpreter/PATH change is required. CLI/generator uses `-E -s -B`;
independent probes/helpers use `-I -B`.

## Preserved and copied coverage

All 38 original methods remain: twenty property/CLI methods and eighteen support
methods. Four runtime/generator files, two original tests and four historical
docs remain baseline byte-identical, including FORMAT, PROVENANCE, VALIDATION
and examples/README. The native harness selects originals and binds actual
source/interpreter identity without replacing protected assertions. The included
declaration_diff helper remains unchanged and adjacent for standalone imports.

Thirty copied-runtime methods supplement originals with external copies,
fictional owned fixtures and actual CLI execution. Each lane selects 68 methods;
four versions on Windows/Ubuntu select 544 total: 304 original and 240 copied
selections. Actual passes/skips/failures/errors are separate. Finite named
platform-opposite FIFO/Windows-stream skips are allowed. Local privilege skips
require the exact actual Windows symlink privilege error; hosted strict mode
permits no such skip. Hardlink safeguards must execute, and all skip-policy IDs
must be selected and unique.

Coverage includes multi-before/after key indexing, first-equals/ASCII trim,
literal hashes/quotes/backslashes/dollars/empty values, case/nonbreaking-space
behavior, comment/order equivalence and supported additions/removals/changes.
Duplicate keys remain held without arbitrary pairing, including equal values and
cross-file duplicates. Unidentified/import rows on the opposite side hold
unmatched keys; supported matched changes coexist with coverage. Imports are
never followed and no service/precedence/permissions/runtime state is evaluated.
Safe I/O checks cover immutable stable regular files, aliases/links/streams,
fixed errors, encoding/control/line/byte/count/collection budgets, fresh output,
privacy/details, escaped HTML and exact input/report hashes/manifests.

## Exact fictional guide and evidence limits

The [fictional guide](../USAGE.md) executes its exact published Python block in
fresh no-pip 3.15.2 with copied actual runtime. Explicit whole-report expectations
do not import/reuse parsing or matching code. Working evidence is preserved
separately from one committed-head rerun; nineteen source hashes include the
comparison helper and actual qualifier.

Its 36 cases include fixture generation, 23 completed reports and twelve
controlled refusals. It checks 46 payload hashes, 49 input hash observations,
36 fixtures and 105 exact input/report files. Eighteen default/five details
reports include four observation-equivalent privacy pairs. Defaults omit keys/
values; details expose supported identities and values. Raw lines/import targets/
local filenames remain omitted, but hashes/structure identify: no anonymization.

All eight scope flags remain false: property import following, device property
changes, effective merging, precedence evaluation, permission checks, runtime
compatibility verification, device access and actual snapshots. No Android
property service, reserved-key/partition semantics, implicit precedence/expansion,
bootability, complete configuration or deployment acceptance is verified. Empty
scope can exit 0; supported partial results do not establish global absence.
Unknown rows/imports deliberately limit unmatched claims.

Use the [pinned Python preparer](../packaging/prepare_python.py),
[source builder](../packaging/build.py) and [archive qualifier](../packaging/qualify.py)
in a new owned external workspace. Review actual release workflow results.
Public validation retains sanitized counts/versions/byte identities rather than
machine paths, raw logs or real snapshots. Stable-input/cooperative bounds are
not an OS sandbox, atomic hostile-writer snapshot, hard I/O deadline, rollback
transaction or durable-output guarantee. Failed writes may leave partial fresh
reports; only complete checked manifests establish report-byte consistency.
