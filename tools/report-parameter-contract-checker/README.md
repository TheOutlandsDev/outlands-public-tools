# Report Parameter Contract Checker

Validate offline report parameter declarations and supplied binding cases, including bounded conditional activation. Independent MIT source tool; Python 3.12/3.13 standard library.

```text
python -B parameters.py --input examples/input.json
python -B source_check.py
```

Library entry: `parameters.check(raw_json_bytes)`. Input is a bounded strict JSON declaration with exact format `outlands-report-parameters-v1`. Identifiers and full normalized declaration hashes bind selected revisions. `PASS` means the supplied declarations and claims satisfy this tool's narrow rules; `REVIEW_REQUIRED` marks logical findings, and `ERROR` refuses malformed or stale inputs. The example is wholly fictional. Optional `--out` writes one new report to an existing trusted parent outside the source tree; it never overwrites an existing file.

No SQL execution, data retrieval, UI rendering, or verification of source completeness. Supplied values and identifiers can be private; keep real input and reports private. The hash in a report is a byte pin, not anonymization or provenance proof. See [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
