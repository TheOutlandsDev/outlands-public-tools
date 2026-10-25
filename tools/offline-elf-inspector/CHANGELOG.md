# Changelog

## 1.1.0 — 2026-10-25

- Opt-in `--runtime-hints` scans bounded ASCII library/config/firmware tokens from
  the same stable open ELF input, with per-file/global byte and observation caps.
- Hints remain separate from declared dependencies and graph resolution; explicit
  partial coverage requires review, while hints alone do not change the status.
- JSON/HTML include first offsets, repetition counts, omission reasons and privacy
  limits. Default runs do not scan or emit hints.
- Original fictional hint examples and 23 additional boundary/integration tests.

## 1.0.0 — 2026-10-25

- Fresh portable offline ELF32/ELF64 metadata parser, both byte orders.
- Explicit local roots/entries; bounded discovery, read budgets and coverage issues.
- SONAME/basename candidates with ambiguity and architecture/type mismatch reports.
- Cycle-safe dependency graph, optional hashes and private HTML/JSON reports.
- Original generated examples, malformed-input tests and independent Linux oracle.
- MIT source published inside the existing OUTLANDS Public Tools collection.
