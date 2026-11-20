# Offline Multi-Product Planning Coverage Checker

Check saved orders and WIP against explicit product mappings, planning configurations, and Kanban rules. The report identifies uncovered open demand and WIP assignment failures. It reports coverage only and generates zero plans.

[Setup and fictional walkthrough](SETUP.md) · [Download and validation records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/multi-product-planning-coverage-checker-v0.1.0)

The standalone input uses local JSON and bundles copies of the published WIP Supply Normalizer and WIP-to-Kanban Assignment Checker. Its planning configuration models retain the reviewed-route fields and validation. The input schema omits workbook metadata that the coverage calculation never reads. All examples and provenance labels are fictional.
