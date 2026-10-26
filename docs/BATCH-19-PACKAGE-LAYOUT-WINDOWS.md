# Batch 19: Package Layout Checker on Windows

This addition adapts only the collection's existing public MIT contract. It
adds a separate native Windows reader and CLI dispatch without importing,
copying or running a held private verifier or real package/manifest. Original
private source, paths, identities, records, credentials, endpoints and operational
configuration remain excluded. No third-party implementation/runtime is bundled.

## Behavior and preservation

The Windows CLI previously rejected the platform. Supported local-volume inputs
now receive the same manifest v1, bounded declared-file checks, optional Python
syntax parsing, case-insensitive literal checks, JSON result shape and exit codes.
Selected Python is never imported or executed. Presence-only entries do not read
their bodies; unlisted entries are not enumerated or opened.

Windows retains ancestor handles, checks normalized native names and identities,
rejects reparse points and multi-link files, refuses ambiguous/reserved/stream
paths and short-name aliases, and requests read sharing only. Sharing conflicts
and unavailable metadata fail closed. File descriptors explicitly own transferred
native handles and are noninheritable. Keep both Python source files together.
See the [native API contract and limits](../tools/package-layout-checker/docs/WINDOWS.md).

The 15 original top-level support definitions are byte-identical to the reviewed
pre-change main source; the existing 33 POSIX test methods/file are unchanged.
The main function only dispatches Windows separately; its POSIX branch keeps the
original platform probe, manifest reader and descriptor checker. Windows path
rules do not alter the shared manifest parser's POSIX rules.

## Fictional validation

Local Windows/Python 3.12.7 discovered 64 component methods: 27 passed and 37
skipped, no failures/errors. That comprises 25 native Windows passes and two
portable passes; 33 POSIX-only methods, one POSIX-only API method and three
unavailable native hardlink/symlink/junction fixtures were skipped. Skips are not
passes. The four CI jobs target Windows/Ubuntu and Python 3.12/3.13, preserving
native POSIX coverage and requiring those three Windows link fixtures to execute
successfully. Short-name tests may skip when no alternate spelling is available;
consult exact-commit Actions results for executed counts.

New cases cover native opens/reads/cleanup, writer/delete/parent-rename refusals,
noninheritable descriptors, bounded manifest/per-file/total reads, redacted errors,
unchanged input bytes, static syntax/literals, source nonexecution, metadata-only
presence checks, unlisted-file exclusion, aliases, links/reparse points and
identity/name changes. Repeated local success/rejection checks showed no handle
count growth in that fixture process.

A separate two-file runtime copy outside the checkout passed 23 fresh-process
CLI scenarios with fictional packages and preserved input/checker bytes. The
collection regression discovered 559 methods: 532 passed, 27 skipped. Ruff
checks/formatting of the two new Python files and local documentation/JSON checks
passed. These observations do not prove application correctness or exhaustive
filesystem behavior; declared checks do not establish public-release clearance.

## Privacy and remaining limits

Public fixtures are invented; new negative cases create disposable local trees.
Real manifests/results can retain private relative names and literal rules and
must receive their own review. Native paths, IDs, matched values and OS error
text are suppressed by CLI findings, but Python library tracebacks can disclose
source locations. Use stable trusted inputs: drive/mount rebinding, hostile
mutation, mapped views, network/virtual storage, power loss and ACL privacy are
outside the guarantee. Windows handles do not claim POSIX directory-descriptor
semantics or an atomic snapshot.

The exact changed publication bytes receive a separate pattern/private-marker
review and hash inventory. Scanner outputs, private markers, source mappings,
publication receipts and audit ledgers remain outside the public repository.
This selected addition does not clear unrelated imports, Git history, held
source/rights families or existing v0.1.0 release assets. Copyright identity for
selected original MIT work remains TheOutlandsDev.
