# Standalone exact-byte patch-planner source qualification

## Required matrix and accepted records

The source ZIP requires eight fresh Windows/Ubuntu lanes on exact CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2. Each selects 82 methods: 52 preserved
original methods plus 30 copied-runtime methods, totaling 656 selections. These
are required selections, not assumed passes. The [release validation
asset](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/binary-patch-planner-v0.1.0)
records actual accepted outcomes, finite native skips, interpreter fingerprints
and source revisions.

Python is supplied separately. The recipe verifies SHA-256/lengths of locked
standalone distributions from build release 20261110, extracts into new owned
prefixes and measures the actual executable version/hash before source-bound
acceptance. No global install or persistent PATH change is performed. Native
binary reproducibility is not claimed. No third-party Python package, game,
firmware tool, device, real binary or private patch plan is required or bundled.

## Preserved original code and native tests

The 52 originals comprise 34 planner/CLI methods and 18 shared-support methods,
with 105 assertion calls: 103 in tests and two in seven supporting helpers.
All three production/generator files and both original test files retain raw
bytes and parsed bodies against the reviewed base, including 26 runtime top-level
definitions and three generator definitions. No production mirror or parser
replacement is introduced. Historical format/provenance/validation documents
and the examples README remain unchanged.

The test-only adapter narrows broad platform skips and rejects undocumented
ones. Windows records the POSIX FIFO test. POSIX records Windows alternate-stream
syntax and destination-naming cases. Only actual local Windows privilege error
1314 may explain the two optional planner/support symlink skips. Applicable
hosted link/hardlink cases are mandatory. Exact IDs/reasons are separate from
passes. Empty discovery, wholly skipped groups, arbitrary errors or test failures
cannot qualify.

## Actual copied runtime and byte consistency

Additional tests copy the actual planner, support and fictional generator to an
external owned location and invoke the real CLI. They check preview defaults,
explicit new-file application and readback, whole source size/hash binding,
expected bytes, no-op/adjacent/unsorted edits, invalid ranges/overlaps, strict
JSON/numeric/hex/schema rules, finite resource bounds, input immutability,
native path/alias refusal, exclusive outputs, reports/manifests, privacy and
simulated write/readback/report failure artifacts.

Every declared source size/hash and expected slice must match before a candidate
is calculated. A source mismatch produces review findings and withholds even an
explicit application request. Invalid plans fail incomplete rather than being
partially interpreted. Source hashes cover the complete selected fictional
binary. Source/plan/report/candidate hashes are independently checked; report
manifests cover only JSON/HTML, while an applied candidate has a separate
byte-length/SHA receipt. Neither is authenticity, ownership or behavioral proof.

Reports omit byte payloads and local filenames, but retain identifying hashes,
offsets and sizes; omission is not anonymization. Plans contain edit bytes and
must be reviewed separately. Equal-length edits do not validate any file format,
update its checksums/signatures or establish runtime compatibility.

All eight scope facts remain false: `real_user_binaries_used`,
`candidate_files_executed`, `game_files_patched`, `firmware_files_patched`,
`physical_devices_opened`, `format_semantics_verified`,
`runtime_behavior_verified`, `transactional_rollback_claimed`.

## Fresh archive and release gates

Each lane independently rebuilds deterministic ZIP/build-manifest bytes from
exact reviewed Git source, checks every source-manifest row/archive member and
extracts to a new external owned directory. Safe relative names, exact inventory,
regular-file modes, fixed timestamps and UTF-8 payloads are checked. The ZIP has
29 reviewed source files and their manifest, 30 members. Runtime binaries,
private plans/inputs, generated candidates/reports and raw logs are excluded.

The fresh application environment has no pip and zero installed distributions.
Imports/tests resolve to extracted source and interpreter/runtime bytes remain
unchanged before/after. Assertion-based helpers reject optimized Python.
Every selected original/copied method must pass subject only to finite recorded
native skips. Existing source CI commands remain available with an empty
environment, measured interpreter fingerprints and owned canonical fixture roots.

Source/privacy findings require exact finite dispositions. Publish only the
source ZIP, usage guide, public validation JSON, build manifest and checksums.
Download all five anonymously, compare byte lengths/hashes and exact tagged
source, then qualify downloaded source in another empty environment. A consumer
without a reference rebuild records that omission explicitly.

## Executed fictional guide and failure boundary

The [guide](../USAGE.md) runs 25 cases: five successes, four review results and
sixteen incomplete results, comprising fifteen refusals and one injected late
report failure. Eight normal manifests, sixteen report-file hashes, sixteen
source/plan hash observations and three candidate readbacks are independently
checked. Seventeen fixtures stay unchanged and the exact workspace contains
44 input/report/candidate files. Four requested candidates remain withheld.
Preview and applied reports differ only by the explicit application receipt.

The injected report failure runs actual CLI main and candidate creation/readback
while a test-only standard-library mock makes subsequent report writing fail.
The independently checked candidate remains without a normal report. This
demonstrates the absence of automatic rollback; it does not simulate power loss
or prove hardware durability. Other failures can leave partial candidates/reports.

The unchanged [format](FORMAT.md), [historical validation](VALIDATION.md) and
[provenance](PROVENANCE.md) retain their original scope. Trusted stable inputs and
owned output parents are required. Snapshot/path checks and cooperative limits
are not an OS sandbox, atomic snapshot or hard native I/O deadline. Candidate
and report creation is not transactional; preserve/review failed artifacts and
choose new destinations after resolving the cause. No real game, application,
firmware or device acceptance is claimed.
