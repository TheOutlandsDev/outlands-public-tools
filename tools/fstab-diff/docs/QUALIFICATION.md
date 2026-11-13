# Standalone saved fstab source-download qualification

## Required matrix and accepted evidence

Qualification requires eight fresh Windows/Ubuntu lanes on exact CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2. Each selects 63 methods: 33 preserved
original methods plus thirty copied-runtime methods, totaling 504 selections.
These are required selections, not assumed passes. The [release validation
asset](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/fstab-diff-v0.1.0)
records actual outcomes, finite skips, interpreter facts and source revisions.

Python is separately supplied. The recipe verifies SHA-256/lengths of locked
standalone distributions from build release 20261110, extracts into new owned
prefixes and measures actual executable version/hash before source-bound
acceptance. No global install or persistent PATH change is performed. Native
binary reproducibility is not claimed. No Python package, mount/probe utility,
actual configuration, firmware or device is required or bundled.

## Preserved original code and native safeguards

The 33 originals comprise sixteen fstab/CLI methods and seventeen support
methods, with 53 assertion calls: 52 in tests and one in four supporting helpers.
Three production/generator files and both original test files retain raw bytes
and parsed bodies against the reviewed base, including 22 runtime top-level
definitions and one generator definition. The older `text_support.py` API stays
unchanged. No production mirror or parser replacement is introduced. Historical
format/provenance/validation documents and the examples README remain unchanged.

A test-only adapter narrows broad native skips and rejects undocumented ones.
Windows records the POSIX FIFO test; POSIX records the Windows alternate-stream
syntax test. Only actual local Windows privilege error 1314 may explain the
optional support symlink skip. Applicable hosted link/hardlink cases are mandatory.
Exact IDs/reasons stay separate from passes. Empty discovery, wholly skipped
groups, arbitrary errors and failures cannot qualify.

## Actual copied runtime and parsed-record semantics

Additional tests copy the actual comparator, text support and fictional generator
to an external owned location and invoke the real CLI with two selected inputs.
They check explicit Linux/Android modes, Linux numeric defaults/equivalence,
Android fifth-field separation, one-pass octal escapes, comment/hash handling,
option order/duplicates, field changes, unique unmatched targets, duplicate holds,
unique-common relative order, unsupported coverage, empty scope, privacy/default-
details equivalence, escaped HTML, exact statuses/errors, input immutability,
limits, native path/alias safeguards, fresh reports and independent input/report hashes.

Linux accepts four through six fields; omitted dump/pass values are zero and
leading-zero decimal spellings normalize to integers. Android accepts exactly
five fields and keeps `fs_mgr_flags` separate from mount options. Options/flags
are ordered comma text, not evaluated sets; empty or duplicate tokens remain
findings. Field splitting precedes supported whitespace/backslash decoding.
Unsupported fields/escapes/numbers remain coverage, including identical inputs.

Only exact decoded targets unique on both sides are paired. Duplicate targets
retain their rows as ambiguous and are excluded from change and order pairing.
Unique unmatched targets become added/removed observations; a target rename is
removal/addition. Relative order covers only unique common parsed targets,
excluding additions/removals, ambiguity and unsupported rows. These observations
do not prove effective absence or completeness of an actual configuration.

Defaults omit decoded private values and local filenames. Requested details
include record fields, before/after values and ambiguous targets. Removing only
opt-in fields and the mode flag preserves observations. Target IDs depend on
first-seen order and are not persistent identities. Hashes, line positions,
counts and structure remain identifying: omission is not anonymization. Input
hashes and unsigned report manifests prove selected-byte consistency, not origin,
runtime validity or redistribution permission.

All eight scope facts remain false: `filesystems_mounted`, `filesystems_probed`,
`configurations_modified`, `devices_connected`, `real_device_configs_used`,
`bootability_verified`, `effective_flags_evaluated`,
`effective_device_state_verified`. Field paths are not accessed. No actual
filesystem, complete device config, boot result or runtime behavior is certified.

## Fresh archive and release gates

Each lane independently rebuilds deterministic source ZIP/build-manifest bytes
from reviewed Git source, checks every source-manifest row/member and extracts
to a new external owned directory. Safe relative names, exact inventory, regular
file modes, fixed timestamps and UTF-8 source payloads are checked. The ZIP has
29 reviewed source files plus their manifest, 30 members. It excludes runtimes,
actual configs/firmware, generated reports and raw validation logs.

Fresh application environments have no pip and zero installed distributions.
Imports/tests resolve to extracted source; interpreter/runtime bytes stay
unchanged before/after. Assertion-based helpers reject optimized Python. Every
selected original/copied method must pass subject only to finite recorded
native skips. Existing configuration source commands and sibling native lanes
remain, with measured interpreter fingerprints and canonical owned fixture roots.

Source/privacy findings require exact finite dispositions. Publish only the
source ZIP, usage guide, public validation JSON, build manifest and checksums.
Download all five anonymously, compare lengths/hashes and tagged source, then
qualify downloaded source in another fresh environment. A consumer without a
reference rebuild records that omission explicitly.

## Executed fictional guide and limits

The [guide](../USAGE.md) runs 32 cases: seven successes, fourteen reviews and
eleven controlled incomplete/refusal results. Twenty normal manifests, forty
report-file hashes and forty before/after observations are independently checked.
Thirty-seven fixtures stay unchanged and the workspace has exactly 97
input/report files. Twelve reports use defaults and eight request details;
three pairs preserve observations after removing only opt-in fields/mode.

The unchanged [format](FORMAT.md), [historical validation](VALIDATION.md) and
[provenance](PROVENANCE.md) retain their earlier evidence boundaries. Trusted
stable inputs and owned parents remain required. Snapshot/path checks and
cooperative limits are not an OS sandbox, atomic snapshot or hard native I/O
deadline. Output failure can leave partial new reports; preserve/review them and
select new destinations after fixing the cause.
