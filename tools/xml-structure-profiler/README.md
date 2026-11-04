# XML Structure Profiler

Summarize bounded XML element paths, attributes and child counts without text values. Independent MIT CLI/library, Python 3.12/3.13 standard library only.

```text
python -B profile.py --input examples/input.json
python -B source_check.py
```

Library: `profile.check(raw_json_bytes)`. Format `outlands-xml-structure-profile-v1`. Optional `--out` writes a NEW private report outside source under an existing trusted parent.

## Contract

Input exactly `{format,xml_text}`. XML text is at most 4096 UTF-8 bytes, with at most 512 elements, 256 distinct paths and depth 12. DTD, processing instructions and comments are refused by the shared strict XML parser. Paths are arrays of expanded element names; each path reports occurrences, attribute-name counts, direct nonblank text presence and minimum/maximum direct children. The profile pin covers this summary, while the XML pin covers exact bytes.

## Limits and privacy

No XML Schema validation, rendered layout, text or attribute-value comparison, external resources, or source completeness claim. Element/attribute names, counts and hashes can still be sensitive. Keep real inputs and reports private. Hash pins establish byte identity only. See [Python JSON](https://docs.python.org/3.12/library/json.html), [Python XML](https://docs.python.org/3.12/library/xml.etree.elementtree.html), [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
