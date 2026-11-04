# Model Interface Manifest Checker

Validate declared model port types, shapes, dynamic symbols, and snapshot pins offline. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B manifest.py --input examples/input.json
python -B source_check.py
```

Library: `manifest.check(raw_json_bytes)`. Format `outlands-model-interface-manifest-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,manifests}` with 1–32 unique manifests. A manifest has `id`, positive `revision`, declared artifact and preprocessing SHA-256 strings, 0–16 named dynamic symbols, and 1–32 input and output ports each. A symbol declares integer minimum/maximum dimensions in 1..10^9 and must be used. Each port has unique ID within its side, dtype float32/float64/int64/boolean, 1–8 static positive or named symbolic dimensions, and exact boolean required. Rows normalize by ID before hashing. Hashes are caller declarations, not authenticated artifact bytes.

## Limits and privacy

No ONNX parsing, model load, tensor inspection, preprocessing inference, runtime compatibility, or deployment. Inputs and reports from real work may reveal IDs, totals, shape metadata, or artifact pins; keep them private. A matching hash is not an authenticity or rights proof. [Input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md) give the remaining boundaries.
