# Report Chart Coverage Reconciler

Reconcile declared point identities and ordering with one pinned fictional row cohort and series assignment. Independent MIT source tool; Python 3.12/3.13 standard library.

```text
python -B coverage.py --input examples/input.json
python -B source_check.py
```

Library entry: `coverage.check(raw_json_bytes)`. Input is a bounded strict JSON declaration with exact format `outlands-report-chart-coverage-v1`. Identifiers and full normalized declaration hashes bind selected revisions. `PASS` means the supplied declarations and claims satisfy this tool's narrow rules; `REVIEW_REQUIRED` marks logical findings, and `ERROR` refuses malformed or stale inputs. The example is wholly fictional. Optional `--out` writes one new report to an existing trusted parent outside the source tree; it never overwrites an existing file.

No query or chart execution and no assertion that the supplied snapshot includes all source rows. Excluded rows use null series. The hash in a report is a byte pin, not anonymization or provenance proof. See [input and output safety](IO-SAFETY.md), [origins](ORIGINS.md), and [validation](VALIDATION.md).
