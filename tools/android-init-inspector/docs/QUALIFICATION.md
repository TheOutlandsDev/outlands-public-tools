# Standalone selected init-text source-download qualification

## Required matrix and accepted evidence

Qualification requires eight fresh Windows/Ubuntu lanes on exact CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2. Each selects 59 methods: 29 preserved
original methods plus 30 copied-runtime methods, totaling 472 selections. These
are required selections, not assumed passes. The [release validation
asset](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-init-inspector-v0.1.0)
records actual accepted outcomes, finite native skips, interpreter facts and source revisions.

Python is separately supplied. The recipe verifies SHA-256/lengths of locked
standalone distributions from build release 20261110, extracts into new owned
prefixes and measures actual executable version/hash before source-bound
acceptance. It does not install globally or change persistent PATH. Native
binary reproducibility is not claimed. No Python package, Android tool,
firmware/device config or physical device is required or bundled.

## Preserved original code and native safeguards

The 29 original methods comprise twelve init/CLI cases and seventeen support
cases, with 52 assertion calls: 51 in tests and one in four supporting helpers.
Three production/generator files and both original test files retain raw bytes
and parsed bodies against the reviewed base, including twenty runtime top-level
definitions and one generator definition. The older `text_support.py` API stays
unchanged. No production mirror or parser replacement is introduced. Historical
format/provenance/validation documents and the examples README remain unchanged.

A test-only adapter narrows broad native skips and rejects undocumented ones.
Windows records the POSIX FIFO test; POSIX records the Windows alternate-stream
syntax test. Only actual local Windows privilege error 1314 may explain the
optional support symlink skip. Applicable hosted link/hardlink cases are mandatory.
Exact IDs/reasons stay separate from passes. Empty discovery, wholly skipped
groups, arbitrary errors and failures cannot qualify.

## Actual copied runtime and selected declaration scope

Additional tests copy the actual inspector, text support and fictional generator
to an external owned location and invoke the real CLI. They check literal
services/actions/references, duplicate/override ambiguity, selected-file lookup,
unfollowed imports/mount targets, unsupported statement/context resets,
critical/reboot markers, empty/comment-only success, privacy/default-details
equivalence, always-omitted argv, escaped HTML, exact statuses/errors, UTF-8,
bounds, immutable inputs, fresh reports, native path/alias safeguards and
independent input/report hashes.

References index only explicitly selected declarations. Unique matches do not
establish effective availability; unselected references do not prove device
absence. Imports never select more files. Duplicate declarations are retained
without an override winner. Triggers/properties, execution order and version-
specific option meanings remain unevaluated. Quote/backslash/expansion lines
reset context rather than attaching later statements to a partially read header.
Empty/comment-only scope may produce exit 0 with no findings; it does not prove
that a device configuration is complete or boots.

Defaults omit literal names/paths/triggers; requested details enable selected
fields and reference names. Removing only opt-in fields and the mode flag leaves
the same observations. Service argv is always omitted, with only argument count
retained. Unknown command/option payloads and local filenames stay omitted.
Opaque IDs, source hashes, line positions, options/counts and structure can
identify material: omission is not anonymization. Input hashes describe selected
text bytes and unsigned report manifests provide consistency, not authenticity,
device validity or redistribution permission.

All eight scope facts remain false: `imports_followed`, `services_started`,
`mounts_performed`, `triggers_evaluated`, `properties_evaluated`,
`real_device_configs_used`, `bootability_verified`,
`effective_device_state_verified`. No real configuration, firmware/device,
service/mount execution, boot result or runtime acceptance is certified.

## Fresh archive and release gates

Each lane independently rebuilds deterministic source ZIP/build-manifest bytes
from reviewed Git source, checks every source-manifest row/member and extracts
to a new external owned directory. Safe relative names, exact inventory, regular
file modes, fixed timestamps and UTF-8 source payloads are checked. The ZIP has
29 reviewed source files plus their manifest, 30 members. It excludes runtimes,
real configs/firmware, generated reports and raw validation logs.

Fresh application environments have no pip and zero installed distributions.
Imports/tests resolve to extracted source; interpreter/runtime bytes stay
unchanged before/after. Assertion-based helpers reject optimized Python. Every
selected original/copied method must pass subject only to finite recorded
native skips. Existing source CI commands remain available with fresh no-pip
environments, measured interpreter fingerprints and canonical owned fixture roots.

Source/privacy findings require exact finite dispositions. Publish only the
source ZIP, usage guide, public validation JSON, build manifest and checksums.
Download all five anonymously, compare lengths/hashes and tagged source, then
qualify downloaded source in another fresh environment. A consumer without a
reference rebuild records that omission explicitly.

## Executed fictional guide and limits

The [guide](../USAGE.md) runs 24 cases: eight successes, six review results and
ten controlled incomplete/refusal results. Thirteen normal manifests, 26
report-file hashes and fourteen selected-input observations are independently
checked. Sixteen fixtures stay unchanged and the workspace has exactly 55
input/report files. Six reports use defaults and seven request details; argv
stays omitted in every mode. Three default/details pairs preserve observations
after removing only opt-in fields/mode, including escaped literal HTML.

The unchanged [format](FORMAT.md), [historical validation](VALIDATION.md) and
[provenance](PROVENANCE.md) retain their earlier evidence boundaries. Trusted
stable inputs and owned parents remain required. Snapshot/path checks and
cooperative bounds are not an OS sandbox, atomic snapshot or hard native I/O
deadline. Output failure can leave partial new reports; preserve/review them and
select new destinations after fixing the cause.
