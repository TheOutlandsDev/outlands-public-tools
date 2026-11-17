# Qualification contract

Windows/Ubuntu qualification uses the exact complete CPython 3.12.16, 3.13.18,
3.14.10 and 3.15.2 archives in PYTHON-LOCK.json. No global installation occurs.
Archive hashes, executable identities and the selected version are checked.
Application environments are new venvs without pip or installed distributions.

All 44 original methods retain their bytes: 12 builder, 10 shared contract and
22 boundary tests. BASELINE.json pins original runtime, tests and examples to
the recorded baseline. Only native_windows.exclusive_write changes, using the
same reviewed existing-leaf refusal and CREATE_NEW/OPEN_REPARSE_POINT fix as the
qualified receipt tool. Other runtime files and original test files remain exact.

Twenty copied-CLI methods add independently authored complete report/manifest
expectations, SHA-256 and canonical-byte checks, reserialization/order controls,
all roles, empty/identical/changed buffers, nonexecution of code, exact and exceeded
4 MiB/16 MiB limits, 16/17 selections, malformed JSON, duplicate/missing/extra
bindings, fresh-output/readback, no overwrite, source-tree refusal and mandatory
hardlink/junction or POSIX linked-parent checks. Source and input hashes remain
unchanged after every child command. Source artifacts are never executed.

Each lane selects 64 tests. Exactly one original opposite-platform skip is
permitted. Required hardlink and linked-parent fixtures cannot silently skip.
Selected, started and successful IDs, actual counts and failed IDs are recorded.
Source ZIP CRCs, the explicit manifest and original-file preservation are checked.
CI independently rebuilds the ZIP and build manifest with each selected Python;
both must match the build job bytes. Anonymous acceptance omits that rebuild and
records reference_rebuild_claimed=false rather than inventing reproducibility.

XML C bindings and reported Expat/zlib versions are recorded from the selected
SDK because retained shared tests include XML boundaries. This is whole-SDK
qualification, not an independent library build or a claim about every parser
version. This tool performs integer lengths and hashes; no Decimal arithmetic
qualification is claimed.

Development failures are retained privately: the first copied harness used -I
without adding the owned copied module directory; a second attempt incorrectly
expected LF on Windows stdout. The corrected harness explicitly imports only the
owned copy and normalizes stdout CRLF for comparison. File/report canonical bytes
and hashes remain exact. Original tests, product contracts and refusals were not
weakened to address those harness failures.

Only fictional inputs are used. Paths are explicit, artifact bodies are opaque,
and role labels, source authority, execution and content privacy remain unverified.
No real record, raw private log, interpreter, generated report or third-party
binary is bundled. Original validation and I/O boundary records are retained.
