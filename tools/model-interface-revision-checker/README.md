# Model Interface Revision Checker

Compare pinned baseline and candidate port interfaces for selected breaking declarations. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B revisions.py --input examples/input.json
python -B source_check.py
```

Library: `revisions.check(raw_json_bytes)`. Format `outlands-model-interface-revision-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,baseline,candidate,baseline_sha256,candidate_sha256}`. Both manifests use the standalone manifest schema, have the same model ID, and candidate revision must be newer. Exact normalized pins are recomputed. REVIEW_REQUIRED identifies removed ports, changed dtype or shape (including symbolic bounds), newly required inputs, weakened output requirements, and changed preprocessing pins. New optional inputs and new outputs may pass. Artifact hashes may change without an interface finding. This is a deliberately narrow declared-interface rule, not runtime compatibility proof.

## Limits and privacy

No artifact authentication, inference, provider check, deployment decision, or source execution. Inputs and reports from real work may reveal IDs, totals, shape metadata, or artifact pins; keep them private. A matching hash is not an authenticity or rights proof. [Input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md) give the remaining boundaries.
