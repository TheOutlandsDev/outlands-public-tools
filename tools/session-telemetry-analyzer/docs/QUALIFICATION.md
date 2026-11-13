# Standalone saved-telemetry source-download qualification

## Required scope and accepted records

Qualification requires eight fresh Windows/Ubuntu lanes on exact CPython
3.12.16, 3.13.18, 3.14.10 and 3.15.2. Each selects 84 methods: 54 preserved
original methods and 30 copied-runtime methods, totaling 672 selections. Those
are required selections, not assumed pass counts. The [release validation
asset](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/session-telemetry-analyzer-v0.1.0)
records actual accepted outcomes, finite skips, interpreter facts and source revisions.

Python is separately supplied. The recipe checks SHA-256/lengths of locked
standalone distributions from build release 20261110, extracts to new owned
prefixes and measures actual executable version/hash before source-bound
acceptance. No global install or persistent PATH change is performed. Native
binary reproducibility is not claimed. No Python package, game/plugin, live
collector, monitoring service, capture or device is required or bundled.

## Preserved originals and native safeguards

The 54 original methods comprise 36 telemetry/CLI cases and 18 support cases,
with 134 assertion calls: 133 in tests and one in nine supporting helpers.
Three production/generator files and both original test files retain raw bytes
and parsed bodies against the reviewed base, including 22 runtime top-level
definitions and four generator definitions. No production mirror or parser
replacement is introduced. Historical format/provenance/validation documents
and the examples README remain unchanged.

The test-only adapter narrows broad native skips and rejects undocumented ones.
Windows records the POSIX FIFO test; POSIX records the Windows alternate-stream
syntax test. Only actual local Windows privilege error 1314 can explain the
optional support symlink skip. Applicable hosted link/hardlink cases are
mandatory. Exact IDs/reasons and counts remain separate from passes. Empty
discovery, wholly skipped groups, arbitrary errors or failures cannot qualify.

## Copied runtime and statistical scope

Additional tests copy the actual analyzer, support and fictional generator to
an external owned location and invoke the real CLI. They check per-metric
valid-present population denominators, valid zero, missing/invalid/null values,
LOS boolean denominators, exact decimal declarations/decrease, duplicate-key
rejection, malformed/unknown coverage, single/ambiguous end/drop markers,
per-file isolation, repeated observations, strict numeric/structure/record/file
bounds, immutability, native path/alias refusals, private output, fresh reports,
escaped HTML and independently recomputed source/report hashes.

Missing and invalid values never become zero samples. Means are exact unreduced
numerator/denominator objects over valid-present observations, not time-weighted
statistics, rates or unique populations. An explicit zero sample is valid; a
metric with no valid samples has a null mean. LOS missing/invalid entries and
collections are distinct from valid true/false samples.

Declared time is preserved as an exact decimal string; it is not an authenticated
clock or measured duration. Invalid time declarations do not replace the last
valid one. Multiple end rows make dropped lines ambiguous even when equal or
only one has a valid value; no first/last winner or cumulative sum is invented.
Missing end/drop declarations mean unspecified, not lossless capture. Marker
counts describe rows rather than verified sessions.

Every file stays separate. Identical distinct files and repeated rows contribute
repeated observations; there is no pooling, deduplication, session segmentation,
entity identity or inference of unique players/bots. Source SHA-256 records
selected saved bytes, not authenticity, complete capture or producer acceptance.
Raw records, map/unknown values, identifiers and paths are omitted. No details
mode exposes them. Hashes, sizes, counts, exact declared times and structure can
identify material: omission is not anonymization. Unsigned manifests are
consistency evidence, not origin or redistribution permission.

All eight scope facts remain false: `live_collection_performed`, `games_launched`,
`processes_monitored`, `real_user_captures_used`, `capture_completeness_verified`,
`unique_entities_inferred`, `causal_diagnosis_performed`,
`runtime_performance_verified`. No game, live process, producer integration,
multiplayer behavior, capture health or runtime performance is certified.

## Fresh archive and release gates

Each lane independently rebuilds deterministic source ZIP/build-manifest bytes
from reviewed Git source, checks every source-manifest row/member and extracts
to a new external owned directory. Exact safe relative names, regular-file
modes, fixed timestamps and UTF-8 source payloads are checked. The ZIP contains
29 reviewed source files plus their manifest, 30 members. Runtimes, real
captures, game/plugin files, generated reports and raw validation logs are excluded.

Fresh application environments have no pip and zero installed distributions.
Imports/tests resolve to extracted source; interpreter/runtime bytes stay
unchanged before/after. Assertion-based helpers reject optimized Python. Every
selected original/copied method must pass subject only to finite recorded
native skips. Existing source CI commands and sibling native lanes are retained
with measured interpreter fingerprints and canonical owned fixture roots.

Source/privacy findings require exact finite dispositions. Publish only the
source ZIP, usage guide, public validation JSON, build manifest and checksums.
Download all five anonymously, compare lengths/hashes and tagged source, then
qualify downloaded source in another fresh environment. A consumer without a
reference rebuild records that omission explicitly.

## Executed fictional guide and limits

The [guide](../USAGE.md) runs 22 cases: five successes, nine review results and
eight controlled incomplete/refusal results. Thirteen normal manifests,
26 report-file hashes and fifteen selected-source observations are independently
checked. Fifteen fixtures stay unchanged and the exact workspace has 54
input/report files. No raw or identifying source values are exposed by a details
option; that unsupported option is explicitly refused.

The unchanged [format](FORMAT.md), [historical validation](VALIDATION.md) and
[provenance](PROVENANCE.md) retain their earlier evidence boundaries. Stable
trusted inputs and owned output parents are required. Snapshot/path checks and
cooperative limits are not an OS sandbox, atomic snapshot or hard native I/O
deadline. Output failure can leave a partial new report directory; preserve it,
review the cause and select a new destination after resolving the failure.
