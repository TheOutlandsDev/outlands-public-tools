# Platform metadata inspector source review — 2026-10-25

This batch adapts useful inspection mechanisms identified in three local helper
sources into fresh original public tools. The originals are retained unchanged;
the private review contains their fingerprints. Only reviewed generic code,
authored documentation/tests and fictional fixture generators are published.
No actual image, firmware, vendor code, module binary, device config, hardware
recipe, customer data or identifying real report is included.

| Tool | Local generated Windows methods discovered | Local passed / skipped |
| --- | --- | --- |
| GPT Disk Image Inspector | 46 | 40 / 6 |
| Kernel Module Inspector | 38 | 35 / 3 |
| VINTF Manifest Inspector | 58 | 55 / 3 |

These are 142 discovered methods, 130 passes and 12 platform/environment skips,
with no failures/errors in the reviewed local run. Local CPython is 3.12.14;
VINTF also ran on 3.12.7 and uses an original restricted XML reader without a native XML-parser dependency. Windows/Ubuntu CI runs the full suites on updated
Python 3.12/3.13/3.14 as documented by the workflow. Windows-specific paths,
POSIX FIFOs/sparse files and link availability are distinct platform coverage.
Skips are not counted as passes. Shared guard tests are intentionally repeated
for the standalone module copies; these counts are not unique product features.

GPT tests cover generated raw images, CRC corruption, mismatched tables, unsafe
declared ranges, partition overlaps, privacy and bounded file reads. Module tests
cover cycles versus blocked dependants, missing metadata, duplicate names,
literal alias rules, deep iterative traversal and selected dependency ordering.
VINTF tests cover declaration forms, explicit versions, ambiguous duplicates,
transport changes, malformed/unsupported XML and restricted XML grammar and construction limits.
Each suite also invokes the actual CLI on generated fixtures.

The publication uses exact reviewed source allowlists/SHA-256 inventories,
generated reports outside the source tree, a local privacy-pattern scan with
manual disposition of fictional test markers and canonical Git-blob readback.
No scanner or unsigned checksum proves exclusive authorship, authenticity,
universal secret absence or runtime correctness. MIT applies to the new original
source, not inspected payloads or third-party runtime/format implementations.

Read each module's FORMAT, PROVENANCE and VALIDATION guides. Findings concern
selected evidence; unsupported coverage is never presented as a clean result.
No physical drive, device, boot, mount, module load or effective VINTF merge is
part of this source release. Public suggestions should use minimal fictional
examples and the dedicated issue forms.
