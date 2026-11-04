# XML Structure Revision Comparator

Compare two recomputed, pinned XML element structure profiles. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B compare.py --input examples/input.json
python -B source_check.py
```

Library: `compare.check(raw_json_bytes)`. Format `outlands-xml-structure-compare-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,baseline,candidate}`. Each side contains `{xml_text,profile_sha256}`. Both documents are independently reprofiled; supplied pins must match. The result lists changed element paths, occurrence counts, attribute-name counts, direct text presence and child-count bounds. Equal profiles can have different XML bytes, text or attribute values.

## Limits and privacy

No text equality, XML Schema compatibility judgment, rendered layout comparison, or target update. Element/attribute names, counts and hashes can still be sensitive. Keep real inputs and reports private. Hash pins establish byte identity only. See [Python JSON](https://docs.python.org/3.12/library/json.html), [Python XML](https://docs.python.org/3.12/library/xml.etree.elementtree.html), [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
