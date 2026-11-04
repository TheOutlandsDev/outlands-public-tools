# Chart Encoding Contract Checker

Check supplied chart mark, axis scale, series, and unit declarations against a pinned field schema. Independent MIT source tool; Python 3.12/3.13 standard library.

```text
python -B charts.py --input examples/input.json
python -B source_check.py
```

Library entry: `charts.check(raw_json_bytes)`. Input is a bounded strict JSON declaration with exact format `outlands-chart-encoding-v1`. Identifiers and full normalized declaration hashes bind selected revisions. `PASS` means the supplied declarations and claims satisfy this tool's narrow rules; `REVIEW_REQUIRED` marks logical findings, and `ERROR` refuses malformed or stale inputs. The example is wholly fictional. Optional `--out` writes one new report to an existing trusted parent outside the source tree; it never overwrites an existing file.

No chart rendering, unit conversion, data-value inspection, or proof of visual correctness. Unit strings are opaque exact labels. The hash in a report is a byte pin, not anonymization or provenance proof. See [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
