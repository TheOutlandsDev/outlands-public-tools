# Report Dataset Binding Checker

Check declared report field aliases against pinned dataset fields, types, and nullability. Independent MIT source tool; Python 3.12/3.13 standard library.

```text
python -B bindings.py --input examples/input.json
python -B source_check.py
```

Library entry: `bindings.check(raw_json_bytes)`. Input is a bounded strict JSON declaration with exact format `outlands-report-dataset-bindings-v1`. Identifiers and full normalized declaration hashes bind selected revisions. `PASS` means the supplied declarations and claims satisfy this tool's narrow rules; `REVIEW_REQUIRED` marks logical findings, and `ERROR` refuses malformed or stale inputs. The example is wholly fictional. Optional `--out` writes one new report to an existing trusted parent outside the source tree; it never overwrites an existing file.

No database or query execution, result-row validation, expression language, or proof that a dataset was produced. Real field names and reports may be private. The hash in a report is a byte pin, not anonymization or provenance proof. See [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
