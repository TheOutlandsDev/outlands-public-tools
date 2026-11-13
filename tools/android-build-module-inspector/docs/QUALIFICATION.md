# Standalone saved build-declaration source-download qualification

## Required scope and accepted evidence

Qualification requires eight fresh Windows/Ubuntu lanes on exact CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2. Each selects 86 methods: 56 preserved
original methods and 30 copied-runtime methods, totaling 688 selections. Those
are required selections, not assumed pass counts. The [release validation
asset](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-build-module-inspector-v0.1.0)
records accepted outcomes, exact native skips, interpreter facts and source revisions.

Python is separately supplied. The recipe verifies SHA-256/lengths of locked
standalone distributions from build release 20261110, extracts into new owned
prefixes and measures actual executable version/hash before binding evidence to
selected source. It does not install globally or change persistent PATH. Native
binary reproducibility is not claimed. No third-party Python package, Make,
Soong, AOSP checkout, SDK or device is required or bundled.

## Preserved originals and native safeguards

The 56 original methods comprise 38 build/CLI cases and 18 support cases, with
118 assertion calls: 117 in test methods and one in eleven supporting helpers.
Three production/generator files and both original test files retain raw bytes
and parsed bodies against the reviewed base, including 29 runtime top-level
definitions and one generator definition. No production mirror, parser rewrite
or test replacement is introduced. Historical format/provenance/validation and
the examples README remain unchanged.

The test-only adapter rejects undocumented skips and narrows broad platform
paths. Windows records the POSIX FIFO test; POSIX records the Windows alternate
stream test. Only the actual local Windows privilege error 1314 may explain the
additional support symlink skip. Applicable hosted link/hardlink cases are
mandatory. Exact test IDs/reasons and counts remain separate from passes.
Empty discovery, wholly skipped groups, arbitrary errors and failures do not qualify.

## Copied runtime and interpretation boundary

Additional tests copy the actual inspector, support and fictional generator to
an external owned location, then invoke the real CLI. They check literal/direct
BP names, nested-name exclusion, repeated observations, dynamic identities,
duplicate properties, unsupported top-level stops, limited Make blocks and
unfollowed includes/directives, wanted-name holds, exact status/count/error
stdout, empty stderr, input immutability, bounds, fresh reports, native paths,
privacy, escaped HTML and independently verified input/report hashes.

Names are exact case-sensitive observations. Repetition does not establish a
build collision. Unsupported/incomplete parser scope holds unmatched requests;
`not_observed_selected_supported_scope` describes only selected supported text,
not effective build absence. Literal declarations do not prove build inclusion.
Namespace/variant selection, variables, expressions, includes and build context
remain unevaluated. Discarded property/assignment values are not type-checked or
assessed for their complete build meaning.

Default reports omit names/kinds, filenames and discarded source values. Requested
details enable supported names/kinds and wanted names; the mode flag must match
each request. Removing only opt-in fields leaves the same observations. Source
hashes, line positions, IDs/counts and structure can identify material: omission
is not anonymization. Text-source hashes are not binary/build/device hashes, and
unsigned manifests do not prove authenticity or redistribution rights.

Qualification keeps these eight scope facts false: `make_invoked`,
`soong_invoked`, `includes_followed`, `builds_executed`,
`real_user_build_files_used`, `fixture_inputs_executed`,
`physical_devices_opened`, `effective_build_availability_verified`. No real
build acceptance or device compatibility is claimed.

## Fresh archive and publication gates

Each lane independently rebuilds deterministic source ZIP/build-manifest bytes
from exact reviewed Git source, checks every source-manifest row/archive member,
and extracts to a fresh external owned prefix. Exact safe relative names, regular
file modes, fixed timestamps and UTF-8 source payloads are checked. The ZIP has
29 reviewed source files plus their manifest, 30 members; it excludes private
build text, runtimes, build tools, generated reports and raw logs.

A fresh application environment has no pip and zero installed distributions.
Imports/tests must resolve to extracted source. Interpreter/runtime bytes stay
unchanged before/after; assertion-based helpers refuse optimized Python. Every
selected original/copied method must succeed subject only to finite recorded
native skips. Retained source-suite jobs keep their commands and use measured
interpreter fingerprints plus canonical owned fixture roots.

Source/privacy findings require exact finite dispositions. Publish only the
source ZIP, usage guide, public validation JSON, build manifest and checksums.
Download all five assets anonymously, compare lengths/hashes and tagged source,
then qualify downloaded source in another fresh environment. A consumer run
without a reference rebuild records that omission explicitly.

## Executed fictional guide

The [walkthrough](../USAGE.md) runs eighteen cases: three exit 0 results, eight
expected review exit 1 results and seven controlled incomplete/refusal exit 2
results. Ten manifests, twenty report-file hashes and 22 selected-text source
observations are independently checked, with eighteen unchanged fictional
inputs and 48 exact input/report files. Five reports use defaults and five
enable details. The clean default/details pair differs only by its opt-in
literal fields and mode flag. No build text or include target is executed.

The unchanged [format](FORMAT.md), [historical validation](VALIDATION.md) and
[provenance](PROVENANCE.md) define the subset and earlier evidence boundary.
Trusted stable input paths/output parents remain required. Path/handle sampling
and cooperative bounds are not an OS sandbox, atomic snapshot or hard native
I/O deadline. Failed writes can leave partial new reports.
