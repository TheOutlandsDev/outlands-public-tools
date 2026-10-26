# Android image and saved-APK metadata review — 2026-10-26

Three selected local workshop wrapper use cases have fresh original reusable
public implementations. Historical helpers remain intact and fingerprinted in
the private review record. Only authored generic source, first-party MIT helper
code, documentation, tests and fictional fixture generators are selected. No
actual firmware/APK contents, vendor implementations, real badging reports,
private identifiers, credentials or device-specific deployment recipes are bundled.

| Module | Local discovered methods | Local passed / skipped |
| --- | --- | --- |
| Android Sparse Image Inspector | 45 | 41 / 4 |
| Boot / Vendor Boot Header Inspector | 53 | 50 / 3 |
| APK Metadata Report Diff | 61 | 58 / 3 |

The reviewed local Windows/CPython 3.12.7 run discovered 159
methods: 149 passed and 10 platform/environment
skips, no failures/errors. Repeated first-party safeguard tests support standalone
folders; they are not distinct product features. Windows/Ubuntu CI runs source
gates and these suites on Python 3.12/3.13/3.14 in a four-job matrix. Skips concern
platform-only mechanisms or unavailable link creation and stay separate from
passes. Consult Actions for the actual matrix results.

Sparse fixtures cover RAW/FILL/DONT_CARE structure, explicit unverified CRCs,
declared range/size equations, truncation, unsupported formats, bounds and actual
CLI outputs. Boot fixtures cover v3/v4 boot/vendor layouts, page arithmetic,
vendor table ranges/overlaps/gaps and bounded read-only metadata. APK fixtures
cover strict quoted declarations, exact version/SDK strings, required/optional
libraries, duplicate holds, unidentified opposite rows and private report fields.
All suites invoke their actual authored Python CLI on disposable generated files.
An additional private deterministic check sampled 2,000 generated binary-header
mutations without unexpected exceptions or out-of-range reads; it is not exhaustive
fuzzing. Manual AAPT2 capture instructions are not executed acceptance evidence.

Each folder documents installation, Windows/Linux usage, outputs, exit codes,
supported grammar, resource limits, privacy, tests, provenance, licensing and
contributions. Six dedicated bug/suggestion forms welcome fictional reproductions
and format/usability ideas. No real input or identifying report should be attached.
Reports omit documented private fields, but sizes/hashes/structure can identify
inputs: this is not anonymization. Manifests are unsigned consistency evidence.

Publication review uses explicit source-only allowlists and exact SHA-256
inventories, privacy-pattern scans plus manual scope review, original-source
fingerprints and canonical Git-blob readback. These checks do not prove exclusive
historical authorship, input authenticity or absence of every possible secret.
MIT applies to newly authored original code/docs/tests and first-party reuse;
upstream specifications/tools and inspected input files retain their own rights.

The tools perform no reconstruction, extraction, decompression, mount, device
operation, APK install or execution. Image payload integrity, full-image hashing,
AVB/signature validation, sparsechunk-set completeness, bootability, hardware
compatibility, required runtime components and effective app state are outside
their evidence. Scope coverage or findings produce review, not deployment advice.
