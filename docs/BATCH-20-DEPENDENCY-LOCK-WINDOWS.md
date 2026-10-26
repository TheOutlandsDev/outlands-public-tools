# Batch 20: Dependency Lock Tools on Windows

This addition adapts only the existing public MIT toolkit and native input
mechanism. It does not read, copy or run a held private helper, actual report,
dependency lock, package artifact, credential, endpoint, user record or operational
configuration. No third-party implementation/runtime or OS DLL is bundled.

## Behavior and preservation

Windows invocations previously rejected file I/O. Supported local-volume paths
now use retained ancestor handles, normalized native name/identity observations,
reparse and multi-link input refusal, bounded reads and exclusive new output
creation. Raw CLI paths are checked before normalization can erase spelling
details. Ambiguous paths, alternate streams, reserved/trailing names and observed
short-name aliases are refused.

Report parsing and rendering complete before output creation. Native `CREATE_NEW`
never falls back to replacement. Output handles request no sharing during the
bounded short-write loop, file flush, final size/name/identity checks and close.
Existing files, links and directories remain intact. A post-creation error
retains the new file, which may be empty, partial or fully written but
unconfirmed. No Windows cleanup unlinks a pathname or creates missing parents.

Windows output inherits the selected parent's ACL: no POSIX mode 0600 equivalent,
ACL confidentiality check or encryption is provided. Choose a trusted private
parent outside the public checkout. File flushing is not directory-entry or
power-loss durability proof. See the [Windows contract](../tools/dependency-lock-tools/docs/WINDOWS.md).

The original common POSIX reader/writer bodies are unchanged after their new
Windows dispatch. Existing pure report parsing, normalization, fixed-version
subset, lock rendering and strict lock validation definitions are byte-identical.
The original 32-test file is unchanged and runs on Ubuntu in CI. POSIX retains its
mode request, no-follow checks, directory-relative exclusive creation, flushing,
identity-qualified cleanup and limitations. CLI help uses fixed program names;
Windows arguments remain raw strings and interruption returns a fixed category.

## Fictional validation

The new local Windows/Python 3.12.7 suite discovered 43 methods: 39 passed, four
skipped, with no failures/errors. It contains 33 native Windows methods and ten
portable methods; skips were unavailable native hardlink/symlink/junction
creation and one POSIX-only API probe. Skips are not passes. Windows CI requires
those three native link fixtures; short-name cases may explicitly skip if no
alternate spelling is supplied by the filesystem.

Fixtures cover deterministic conversion, strict parser roundtrips for 40 seeded
fictional reports, metadata omission, counts-only/fixed errors, raw path refusal,
input/output limits, single-link/reparse/alias refusal, conflicting data writers,
retained ancestor sharing, source/existing-file preservation and fresh CLI use.
An exact 1 MiB output exercises multiple native writes. Fault cases cover short,
zero/invalid/failed writes, flush failure, CRT ownership-transfer failure,
post-create name mismatch, post-write identity mismatch and close errors. Partial
or unconfirmed files stay present. Repeated native success/rejection cases showed
no handle-count growth in the fixture process; this is not an exhaustive leak or
filesystem proof.

A separate four-file copy outside the checkout passed 33 fresh-process Windows
CLI scenarios using fictional reports and locks only. Runtime/source/input bytes
were preserved and no bytecode was produced. The collection regression discovered
559 methods: 532 passed and 27 skipped. All 339 local documentation/JSON checks
passed. These are separate observations from the new 43-method suite. Ruff
checks/formatting passed for the new backend and test file. Platform CI targets
Windows/Ubuntu, Python 3.12/3.13; Ubuntu also executes the original 32-method suite.
Consult exact-commit Actions results for actual pass/skip counts.

## Privacy and remaining limits

Generated locks retain normalized package names, versions and report-supplied
hashes. They can identify private projects; output is not anonymous. Counts-only
CLI results omit raw names, paths, records, native IDs and OS error text, but
Python library tracebacks can retain source locations. Keep real reports/locks
and captured results private and separately review sharing rights.

Use stable trusted local paths. Network/virtual storage, drive/mount rebinding,
hostile concurrent mutation, mapped views, Windows ACL privacy and every
filesystem behavior are not certified. Neither backend is an atomic snapshot or
hostile-filesystem sandbox. Conversion/validation performs no package downloads,
installation, environment inspection, artifact verification or advisory checks.
Strict syntax and matching hash declarations do not establish origin rights,
artifact authenticity, compatibility or complete dependency coverage.

The exact changed publication bytes receive an unchanged-detector/private-marker
review and hash inventory. Private markers, scanner outputs, mappings, receipts
and audit ledgers remain outside the repository. This addition does not clear
unrelated imports, Git history, held source/rights families or v0.1.0 assets.
Selected original code/tests/docs remain MIT under TheOutlandsDev.
