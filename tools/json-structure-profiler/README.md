# JSON Structure Profiler

Summarize bounded JSON paths and value types without reporting scalar values. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B profile.py --input examples/input.json
python -B source_check.py
```

Library: `profile.check(raw_json_bytes)`. Format `outlands-json-structure-profile-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,json_text}`. The JSON text is at most 4096 UTF-8 bytes, with at most 512 nodes, 256 distinct paths and depth 12. Duplicate object keys and nonfinite numbers are rejected. Array indices become `item:*` path tokens; object keys become `key:<name>` tokens. The report lists type and occurrence counts per path. The profile pin covers this summary, while the JSON pin covers exact text bytes.

## Limits and privacy

No value disclosure, JSON Schema validation, record identity, or source completeness claim. Key names, path structure, counts and hashes can still be sensitive. Keep real inputs and reports private. Hash pins establish byte identity only. See [Python JSON](https://docs.python.org/3.12/library/json.html), [Python XML](https://docs.python.org/3.12/library/xml.etree.elementtree.html), [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
