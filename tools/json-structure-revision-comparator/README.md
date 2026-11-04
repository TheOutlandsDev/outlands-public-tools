# JSON Structure Revision Comparator

Compare two recomputed, pinned JSON structure profiles. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B compare.py --input examples/input.json
python -B source_check.py
```

Library: `compare.check(raw_json_bytes)`. Format `outlands-json-structure-compare-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,baseline,candidate}`. Each side contains `{json_text,profile_sha256}`. Both documents are independently reprofiled; supplied pins must match. The result lists changed path presence, occurrence counts and value-type counts. Equal profiles can have different JSON bytes or scalar values.

## Limits and privacy

No scalar comparison, semantic compatibility judgment, migration plan, or target update. Key names, path structure, counts and hashes can still be sensitive. Keep real inputs and reports private. Hash pins establish byte identity only. See [Python JSON](https://docs.python.org/3.12/library/json.html), [Python XML](https://docs.python.org/3.12/library/xml.etree.elementtree.html), [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
