# Private workspace

Extract public source into a fresh directory. Choose a separate existing,
user-owned private parent for Python/venvs, fictional matrices, actual counts,
stdout captures and qualification receipts:

```text
source/evaluation-metrics-calculator-0.1.0/  selected source only
private/evaluation-metrics/
  venv312/                                  separate no-pip environment
  fictional_walkthrough.py                  private copy of usage driver
  fictional-demo/                           new authored aggregate counts
  actual-counts.json                        private evaluation declaration
  captures/                                 caller-owned stdout/diagnostics
  qualification/                            extraction/environments/receipts
```

Select Python and `evaluation_metrics.py` explicitly. `--counts FILE` is required;
there is no default/environment source, model/corpus loader, target/program
execution, clock/network service, report writer or input update. Only the
selected JSON is read. Caller stdout capture/redirection is separate and can
overwrite its chosen file; choose new private captures deliberately.

The model is a closed-set single-label square confusion table. Rows are expected
classes; columns are predicted classes, both in supplied class order. No class
sorting/discovery, binary positive-class inference, normalization, coercion,
weighting, model execution or individual-record ingestion occurs. Do not invent
or coerce real observations to force a different task format into this schema.

Support is the row sum, TP the diagonal, FP the column sum minus TP, FN the row
sum minus TP. Accuracy is diagonal sum/positive total. Precision/recall/direct
F1 use their own denominators. A zero denominator is UNDEFINED with null
numerator/zero denominator, never an imputed zero/one. Defined ratios keep raw
integer numerator/denominator, including unreduced zero and perfect ratios.
No rounding, smoothing, averaging, threshold, ranking or winner selection exists.
All TP values can be zero with defined denominators and exit 0: this describes
arithmetic, not acceptable performance. Undefined output can coexist with
defined F1/accuracy and still requires review.

Class IDs, support/TP/FP/FN, ratios and counts disclose evaluation structure.
The raw matrix is omitted but binary counts can be reconstructed. Aggregation
is not anonymity. Fixed errors do not anonymize captures/logs/tracebacks. Keep
actual inputs/results private and review a separate export before sharing.
No label truth, prediction provenance, representativeness, data rights, leakage
prevention, statistical confidence or model quality is established.

Use fully spelled canonical trusted paths and stable ordinary files. Components
are checked after absolute normalization. Fictional Windows probes on Python
3.12.7/3.15.2 accepted canonical/leaf-dot/leaf-space/parent-dot forms with exit 0;
parent-space returned 2/INPUT_PATH_INVALID, preserving input/runtime bytes.
These mixed observations establish no blanket original-suffix refusal. Ordinary
single-link files/ancestors with usable sampled identities are required;
observed links/reparse/special/multi-link inputs and sampled changes are refused.
These are not atomic snapshots, writer denial or hostile-filesystem containment.
Rebinding/mount/drive aliases, remote/cloud/virtual/live storage, blocked I/O,
power loss and ACL privacy remain outside acceptance. OS reads can use network
storage without a socket/DNS probe; access metadata and caches remain separate.

Input is at most 64 KiB, with 1–32 classes, bounded integer cells/total and tokens.
These are not total CPU/RAM/JSON-depth/deadline/storage quotas. Require complete
JSON and actual exit/status; interruption or stdout failure may leave partial
captures. No checker-owned output transaction rolls back. Fictional work is
retained without automatic cleanup; requested modes depend on OS/Python/ACL
behavior and do not guarantee confidentiality.

User-owned Python/venvs need no inherent administrator access. Respect OS/device
policy without bypasses. No pip distribution, network, model or account is needed;
Python retains separate terms. Build/qualification outputs must be new private
paths outside source with existing parents. Publish reviewed source/sanitized
actual validation only, excluding real counts/class IDs/results, datasets/models,
personal paths, credentials, private source, binaries and raw logs.
See [USAGE.md](../USAGE.md), [QUALIFICATION.md](QUALIFICATION.md) and
[PROVENANCE.md](PROVENANCE.md).
