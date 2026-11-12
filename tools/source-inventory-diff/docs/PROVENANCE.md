# Provenance and license scope

Offline Source Inventory Diff compares captured metadata using exact decoded
paths, supplied size/digest/time fields, declared coverage and grouped hints.
The parser, canonical spreadsheet escape and guarded input reader adapt public
MIT code at collection commit `6797c65129122de9e6d2b2a799a71de5e0c469ad`.
The existing single runtime and comparison contract remain preserved for this
initial standalone release; its displayed version was already 0.1.0.

Selected source, original tests/examples and documentation retain the full
[MIT license](../LICENSE) and TheOutlandsDev attribution. Standalone packaging,
qualification, documentation and authored fictional consumers used AI
assistance, without a claim of exclusive authorship. Python/standard-library
and OS mechanisms retain their own terms and are not bundled as binaries.

The original 45 test method bodies are retained. One compatibility method
uses a pinned test-only copy of the public Source Inventory producer and its
adjacent Windows backend from baseline
`fd98a06f3b1d5a409f7ae3c308f96fa7d6a11116`. These two source files live below
`tests/producer-fixture/tools/source-inventory/`; the adapter changes fixture
resolution without turning them into runtime dependencies. The comparator's
single script runs independently. Original `.gitattributes`, example README
and all six CSV/summary controls retain their exact bytes/line endings.

Only newly authored fictional controls and reported names/hashes ship here.
No held source archive, original private inventory/configuration, actual
project body, operational record, credential, user identifier, raw log or
third-party implementation is selected. Real reports/results and supporting
operational evidence remain private; unrelated historical rights remain
uncleared.

CSV hashes establish agreement between selected control bytes, not provenance,
authenticity or the truth of declared body hashes. A consistent replacement of
CSV plus summary remains possible. Path groups do not verify renames, identify
an original/canonical copy or authorize deletion. Equal selected records and
coverage declarations do not establish equivalent roots or complete capture.

See the historical
[inventory-diff review](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/BATCH-17-INVENTORY-DIFF.md),
[source report contract](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/tools/source-inventory/docs/CLASSIFICATION.md)
and [collection licensing](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/LICENSING.md).
Historical local counts are distinct from actual standalone versions, counts,
outcomes and skips in release `VALIDATION.json`.
