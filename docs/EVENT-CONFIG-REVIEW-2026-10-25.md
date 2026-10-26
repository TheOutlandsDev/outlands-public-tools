# Saved-event and configuration review — 2026-10-25

Three selected local helper mechanisms have fresh original reusable public
implementations. Originals remain intact and fingerprinted in the private review.
Only generic code, authored guides/tests and fictional fixture generators are
published. Real event exports, property/configuration snapshots, vendor code,
device recipes, credentials and identifying reports are excluded.

| Module | Local discovered methods | Local passed / skipped |
| --- | --- | --- |
| Windows Event Timeline Inspector | 59 | 56 / 3 |
| Android Property Configuration Diff | 38 | 35 / 3 |
| Filesystem Permission Manifest Diff | 39 | 36 / 3 |

The reviewed local Windows/CPython 3.12.7 run discovered 136 methods: 127 passed,
9 platform/environment skips, no failures/errors. Shared guard tests are repeated
for standalone copies, not counted as distinct product features. Windows/Ubuntu
CI runs the three suites/source gates on Python 3.12/3.13/3.14. Skips concern
platform-only mechanisms or unavailable link creation and remain separate from
passes. The event XML reader has no native XML-parser dependency.

Event fixtures cover precision/timezones, stable ties, grouped metadata,
declared gaps, source/computer/channel identity scope, payload omission, XML/JSON
coverage and exact 64-bit output representation. Diff fixtures cover duplicate
holds, literal syntax, imports, numeric normalization, optional-field absence,
unsupported known identities and unknown-opposite-side unmatched holds. All
three suites invoke the actual Python CLI on generated inputs. Manual Windows
export instructions are separate; no live log query was performed for acceptance.

The publication has explicit UTF-8 source-only allowlists/SHA-256 inventories,
private pattern-scan results with manual review where needed, original-source
fingerprints, canonical Git-blob readback and generated reports outside source.
No unsigned manifest or scanner proves authenticity, exclusive authorship,
universal secret absence, effective runtime state or successful deployment.

Each module documents its supported grammar, private output, exit codes, tests,
provenance and community forms. MIT applies to the new original implementation,
not inspected inputs or a new license for third-party code/configurations.
No live Windows log query, property/permission change, native EVTX interpretation,
filesystem/policy evaluation, device operation or causal diagnosis is part of
these tools' generated-test evidence.
