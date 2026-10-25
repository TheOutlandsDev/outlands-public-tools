# Offline Evaluation Metrics Calculator

Calculate accuracy and per-class precision, recall and F1 from an explicitly
selected JSON declaration of confusion counts. Python 3.12+, standard library
only. The calculator reads one bounded file and writes JSON to stdout. It does
not run a model, ingest a corpus or individual records, contact a service,
modify inputs or create report files.

The calculations describe the supplied counts. They do not establish label
truth, prediction provenance, dataset quality, runtime behavior or a winning
model. All shipped counts and class IDs are fictional.

## Fictional examples

Run from the collection root:

```text
python -B tools/evaluation-metrics-calculator/evaluation_metrics.py --counts tools/evaluation-metrics-calculator/examples/counts.json
```

Expected exit: **0**, `METRICS_COMPUTED`, with 20 declared observations,
accuracy `17/20`, and no undefined metrics:

| Class | Support | TP | FP | FN | Precision | Recall | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `class_a` | 10 | 8 | 1 | 2 | `8/9` | `8/10` | `16/19` |
| `class_b` | 10 | 9 | 2 | 1 | `9/11` | `9/10` | `18/21` |

```text
python -B tools/evaluation-metrics-calculator/evaluation_metrics.py --counts tools/evaluation-metrics-calculator/examples/perfect-counts.json
```

Expected exit: **0**, `METRICS_COMPUTED`, with accuracy `5/5`. Ratios remain
unreduced: for `class_a`, precision and recall are `3/3`, and F1 is `6/6`.
This is a calculation on invented counts, not evidence of perfect real-world
performance.

```text
python -B tools/evaluation-metrics-calculator/evaluation_metrics.py --counts tools/evaluation-metrics-calculator/examples/undefined-counts.json
```

Expected exit: **1**, `REVIEW_REQUIRED`, with one declared observation,
accuracy `0/1`, and five undefined metrics. `class_a` has undefined precision;
`class_b` has undefined recall; `class_c` has undefined precision, recall and
F1. F1 for both `class_a` and `class_b` remains defined as `0/1`. Review is
required because denominators are zero, not because a quality threshold was
applied.

## Count format

The UTF-8 JSON object has exactly `schema_version`, `classes` and `counts`:

```json
{
  "schema_version": 1,
  "classes": ["class_a", "class_b"],
  "counts": [[8, 2], [1, 9]]
}
```

The schema version is the integer `1`. Declare 1 to 32 unique class IDs: a
lowercase ASCII letter, followed by lowercase letters, digits, underscores or
hyphens, at most 40 characters total. The square matrix has one row and one
column per declared class, in that exact order. **Rows are expected classes;
columns are predicted classes.** A cell counts observations for that ordered
pair, following the orientation documented by
[scikit-learn's confusion matrix reference](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html).

Cells must be actual JSON integers from 0 to 1000000000. The total must be from
1 to 1000000000000. An all-zero matrix is invalid. Booleans, floats, strings,
negative counts, ragged matrices, duplicate classes/JSON keys, unknown fields
and nonstandard JSON numeric constants are refused. There is no coercion,
automatic class discovery, sorting, normalization or expansion.

This is closed-set single-label classification only. Models, prompts,
responses, individual records, probabilities, weights, dataset splits, corpus
references and extra metadata are outside the schema. It does not support
multilabel records or infer a binary positive class.

## Formulas and exact ratios

For each class, `support` is its row total, TP is the diagonal cell, FP is the
column total minus TP, and FN is the row total minus TP. Precision is
`TP / (TP + FP)` and recall is `TP / (TP + FN)`. These definitions and support
are described in the official
[precision/recall/support reference](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html).

F1 is computed directly as `2*TP / (2*TP + FP + FN)`, using the formula in the
official [F1 reference](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html).
Each denominator is evaluated independently: undefined precision or recall
does not make a nonzero-denominator F1 undefined.

Accuracy is the diagonal sum divided by the total count, corresponding to the
fraction correctly classified in the official
[accuracy reference](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.accuracy_score.html).
The positive-total input rule makes accuracy defined for every valid input.

A defined ratio has exactly this shape:

```json
{"status": "DEFINED", "numerator": 17, "denominator": 20}
```

The formula's raw integer numerator and denominator are preserved. Fractions
are not reduced, rounded or converted to floats: `0/d` and `n/n` remain as
calculated. A zero denominator has this shape instead:

```json
{"status": "UNDEFINED", "numerator": null, "denominator": 0}
```

An undefined ratio is not a score of zero or one and must not be divided or
silently replaced by a score. There are no macro, micro or weighted averages,
rankings, thresholds or automatic quality/winner claims.

The cited pages document metric definitions. This standalone implementation
does not require or import scikit-learn and does not claim compatibility with
its APIs, default zero-division handling or other supported task types. No
third-party implementation is bundled.

## Results and privacy

The result scope is `DECLARED_SINGLE_LABEL_CONFUSION_COUNTS_ONLY`, with
orientation `EXPECTED_ROWS_PREDICTED_COLUMNS`. It includes overall accuracy;
counts `classes`, `observations` and `undefined_metrics`; and per-class `id`,
`support`, `true_positive`, `false_positive`, `false_negative`, `precision`,
`recall` and `f1`. Class results preserve declaration order. Flags
`model_executed`, `network_probed`, `input_modified`, `ground_truth_verified`
and `predictions_verified` are always false.

Exit `0` means `METRICS_COMPUTED` with every ratio defined. Exit `1` means
`REVIEW_REQUIRED` because at least one per-class ratio is undefined; other
defined results are still returned. Exit `2` means `ERROR` for invalid inputs
or arguments. Interruption returns `130`. None approves a dataset or model.

The raw matrix, input path, extra metadata and native errors are omitted from
results. Aggregation is **not anonymity**: class IDs, counts and ratios can
disclose a real evaluation, and binary confusion counts can be reconstructed
from the per-class output. Keep real inputs and stdout private. This tool is
not a secret scanner, anonymizer, IP review or clearance to publish counts.
Use the [private workspace guide](../../docs/PRIVATE-WORKSPACE.md) for your own
inputs and keep them outside the checkout.

## Filesystem and validation limits

The selected input is limited to 64 KiB and must be a regular single-link file
with verifiable file and ancestor identities. Paths are limited to 4,096
characters and 64 parts; traversal, UNC paths, drive-relative paths and unsafe
stream/device forms are refused. Symlink/reparse paths, special nodes and
detected metadata changes are refused. These checks do not freeze a tree or
create an atomic or hostile-filesystem boundary. Use stable trusted local
storage. Although no socket/DNS probe is performed, mapped-drive and
mounted-share reads can involve the operating system's network storage stack.
Remote storage, arbitrary mounts and concurrent writers are not proven safe.
The input size bound cannot interrupt a blocked filesystem operation.

The CLI accepts `--counts FILE`, `--help` and `--version`; there is no report-file
option. Examples use Python's `-B` option to avoid generating bytecode files.

## Provenance and licensing

This is a fresh neutral implementation with invented aggregate counts and a
reviewed public input-reader pattern. No held AI application, private schema,
model configuration, corpus, prompt/response archive or historical evaluation
data is read or copied. Those source families remain outside this review.
Selected original source and examples use the repository's
[MIT license](../../LICENSE), attributed to TheOutlandsDev; operator inputs and
third-party material are not relicensed.

See the [batch review](../../docs/BATCH-13-EVALUATION-METRICS.md) for actual
validation results and remaining limits. CI targets Windows and Ubuntu with
Python 3.12 and 3.13. Fictional arithmetic tests do not establish label truth or
real model performance.
