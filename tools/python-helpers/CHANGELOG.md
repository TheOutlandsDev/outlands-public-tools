# Changelog

## 0.1.0

- Added the initial standalone source-ZIP release of the existing bounded JSON
  loader and structured-redaction library with its adjacent Windows backend.
- Added standalone usage, private-workspace, provenance and external notices.
- Added reviewed-source packaging and fresh Windows/Ubuntu Python 3.12–3.15
  qualification in clean no-pip environments. Actual versions/counts/skips
  appear in release `VALIDATION.json`.
- Preserved JSON/BOM/duplicate-key/number behavior, sensitive-key normalization,
  redaction copies/errors, byte/depth limits and native input contracts. The
  historical `docs/INPUT-CONTRACT.md` remains unchanged.
- Preserved five original shared test bodies through method-AST comparison
  and 40 existing input methods; added actual copied-library API consumers
  without unrelated tool imports. No CLI, installer or background service added.
- Kept real data/results, originals, interpreters, dependencies, binaries and
  raw diagnostics outside the public source selection.
