# Qualification contract — 0.1.0

This record defines release gates. Accepted `VALIDATION.json` attached to the
source release records actual outcomes for its reviewed commit. Required
selections are not assumed passes. The unchanged [historical validation](VALIDATION.md)
remains a separate earlier source/platform record.

## Source and interpreter identity

The source ZIP contains thirty allowlisted source files plus
`SOURCE-MANIFEST.json`, 31 members: original MIT parser/comparison/support,
tests, authored docs/generator and qualification/build helpers. It excludes
interpreters, actual manifests, binaries/target-files, generated reports, raw
logs and private methods. Hashes/build manifest bind the exact ZIP; unsigned
hashes show consistency rather than authentic origin, rights or effective access.

`PYTHON-LOCK.json` pins CPython 3.12.16, 3.13.18, 3.14.10 and 3.15.2 with the
20261110 standalone archive recipe for Windows and Ubuntu. Preparation verifies
archive SHA-256, actual version and actual base executable SHA-256. Archive
lanes create new `venv --without-pip` environments with zero distributions.
No Python packages, native/policy utility, Android SDK, administrator permission
or global interpreter/PATH change is required. CLI/generator uses `-E -s -B`;
independent probes/helpers use `-I -B`.

## Preserved and copied checks

All 39 original methods remain: 21 permission/CLI methods and eighteen support
methods. Four runtime/generator files, two original tests and four historical
docs remain baseline byte-identical, including FORMAT, PROVENANCE, VALIDATION
and examples/README. The native harness binds actual source/interpreter identity
while selecting protected original methods/assertions. The shared comparison
helper remains adjacent and unchanged for standalone imports.

Thirty copied-runtime methods supplement originals using external copies,
fictional owned manifests and actual CLI execution. Each lane selects 69 methods;
four versions on Windows/Ubuntu select 552 total: 312 original and 240 copied
selections. Actual passes/skips/failures/errors remain separate. Finite named
platform-opposite FIFO/Windows-stream skips are allowed. Local privilege skips
require the exact actual Windows symlink privilege error; hosted strict mode
permits no privilege skip. Hardlinks must execute and skip-policy IDs must be
selected and unique.

Coverage includes decimal UID/GID and octal normalization, field/option order,
all supported changes, null optional versus explicit zero, canonical uint64 hex,
literal SELinux context/category order and case-sensitive relative ASCII paths.
Duplicates on either side/across files stay held. Unsupported known fields
retain a held identity; unknown paths create unidentified scope and hold
unmatched opposite keys. Supported matched changes remain visible with coverage.
Checks include fixed errors, immutable stable regular inputs, aliases/links/
streams, encoding/control/line/byte/count/collection budgets, fresh output,
default/details privacy, escaped static HTML and exact input/report manifests.

## Exact fictional guide and evidence limits

The [fictional guide](../USAGE.md) executes its exact published Python block in
fresh no-pip 3.15.2 using copied actual runtime. Explicit whole-report expectations
do not import/reuse parser/matcher logic. Working evidence is preserved separately
from one committed-head rerun; nineteen source hashes include the actual
comparison helper and qualifier.

Forty cases include fixture generation, 27 completed reports and twelve
controlled refusals. The guide checks 54 payload hashes, 57 input hash
observations, 42 unchanged fixtures and 123 exact input/report files. Twenty
default/seven details reports include four observation-equivalent privacy pairs.
Unsupported raw metadata/local filenames stay omitted even with details; no
normalized fields are invented for unsupported known paths. Hashes/structure
remain identifying, so omission is not anonymization.

All eight scope flags stay false: declared paths opened, permissions/ownership
changed, SELinux policy evaluated, capabilities applied, effective access verified,
devices accessed and actual permission manifests used. No chmod/chown, target
lookup, user database, binary config/target-files/policy load, access decision,
security risk verdict, bootability or deployment safety is verified. Capability
and mode changes are declared differences, not automatically vulnerabilities.
Empty scope or a nonexistent declared target does not prove real filesystem state.

Use the [pinned Python preparer](../packaging/prepare_python.py),
[source builder](../packaging/build.py) and [archive qualifier](../packaging/qualify.py)
in a new owned external workspace. Review actual release workflow outcomes.
Public validation retains sanitized counts/versions/byte identities rather than
machine paths, raw logs or real manifests. Stable-input/cooperative bounds are
not an OS sandbox, atomic hostile-writer snapshot, hard I/O deadline, rollback
transaction or durable-output guarantee. Failed writes may leave partial fresh
reports; only complete checked manifests establish report-byte consistency.
