# Fictional confusion-count walkthrough

Extract the [0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/evaluation-metrics-calculator-v0.1.0)
into a fresh folder and select normal Python **3.12–3.15**, with 3.15.2 selected
for that minor in qualification. The CLI needs only `evaluation_metrics.py` and
the standard library. Supply Python separately; no pip distribution, model,
corpus, service, account or network connection is required by the calculator.

The interface is `python -B evaluation_metrics.py --counts COUNTS_JSON`.
`--counts` is required; `--help` and `--version` are static. JSON goes to stdout.
There is no output-file option. A caller's shell redirection is separate and
can overwrite that caller's chosen capture file.

`METRICS_COMPUTED` means the supplied aggregate counts produce defined ratios.
It is not a quality threshold, model approval or performance validation.
The calculator runs no model, ingests no corpus or individual records, contacts
no service and verifies neither ground truth nor predictions. Keep actual
counts, class IDs and captures private: aggregate output is **not anonymity**.

## Run the complete fictional exercise

Create an existing user-owned private parent outside source. Save the single
Python block below as `fictional_walkthrough.py` there and run it unchanged
with two absolute arguments: extracted script and existing private parent.
PowerShell, with fictional paths:

```powershell
python -B 'D:\Private\metrics-review\fictional_walkthrough.py' 'D:\Source\evaluation-metrics-calculator-0.1.0\evaluation_metrics.py' 'D:\Private\metrics-review'
```

Ubuntu:

```sh
python3.12 -B '/absolute/private/metrics-review/fictional_walkthrough.py' '/absolute/source/evaluation-metrics-calculator-0.1.0/evaluation_metrics.py' '/absolute/private/metrics-review'
```

The driver creates a **new** `fictional-demo` child and refuses to reuse it.
It retains seven invented count files, an unrelated file and a prior capture
for private inspection. All class IDs and counts are authored examples. No
actual model, dataset, label, prediction, prompt, response or operational record
is used. Rows are **expected classes**; columns are **predicted classes**.

| Case | Exit | Complete JSON status | Observation |
| --- | ---: | --- | --- |
| `asymmetric` | 0 | `METRICS_COMPUTED` | Accuracy is `17/20`; orientation produces different precision and recall. |
| `perfect` | 0 | `METRICS_COMPUTED` | Raw pairs remain unreduced, including F1 `6/6`. |
| `zero_scores` | 0 | `METRICS_COMPUTED` | All predictions are wrong, but every denominator is positive. |
| `no_predictions` | 1 | `REVIEW_REQUIRED` | One precision is undefined; its recall and direct F1 remain defined zero ratios. |
| `no_support` | 1 | `REVIEW_REQUIRED` | One recall is undefined; its precision and direct F1 remain defined zero ratios. |
| `absent_class` | 1 | `REVIEW_REQUIRED` | An entirely absent class has three undefined ratios. |
| `invalid_counts` | 2 | `ERROR` / `TOTAL_COUNT_INVALID` | An all-zero matrix has no positive total and is invalid. |

The block constructs every complete expected JSON value, checks actual exit
codes/stderr and verifies all input, extra, prior-capture, tree and runtime bytes
after every process. Its 60-second child timeout is a driver choice, not a CLI
filesystem deadline. It prints fictional JSON and creates no captured result file.

```python
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

if not __debug__ or sys.flags.optimize or os.environ.get("PYTHONOPTIMIZE"):
    raise RuntimeError("NORMAL_PYTHON_REQUIRED")
if len(sys.argv) != 3:
    raise RuntimeError("SELECT_SCRIPT_AND_PRIVATE_PARENT_ARGUMENTS")
SCRIPT, PRIVATE_PARENT = map(Path, sys.argv[1:])
if (not SCRIPT.is_absolute() or not PRIVATE_PARENT.is_absolute()
        or not SCRIPT.is_file() or not PRIVATE_PARENT.is_dir()):
    raise RuntimeError("SELECT_ABSOLUTE_EXISTING_SCRIPT_AND_PRIVATE_PARENT")
SCRIPT = SCRIPT.resolve()
PRIVATE_PARENT = PRIVATE_PARENT.resolve()
if PRIVATE_PARENT.is_relative_to(SCRIPT.parent):
    raise RuntimeError("PRIVATE_PARENT_MUST_BE_OUTSIDE_SOURCE")
WORK = PRIVATE_PARENT / "fictional-demo"
WORK.mkdir(mode=0o700, exist_ok=False)

FLAGS = dict.fromkeys((
    "model_executed", "network_probed", "input_modified",
    "ground_truth_verified", "predictions_verified",
), False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def counts(matrix):
    return dict(schema_version=1, classes=["class_a", "class_b"], counts=matrix)


def ratio(numerator, denominator):
    return (dict(status="DEFINED", numerator=numerator, denominator=denominator)
            if denominator else dict(status="UNDEFINED", numerator=None, denominator=0))


def metric(identifier, support, tp, fp, fn):
    return dict(id=identifier, support=support, true_positive=tp,
                false_positive=fp, false_negative=fn,
                precision=ratio(tp, tp + fp), recall=ratio(tp, tp + fn),
                f1=ratio(2 * tp, 2 * tp + fp + fn))


def expected(rows, observations, correct):
    undefined = sum(row[key]["status"] == "UNDEFINED"
                    for row in rows for key in ("precision", "recall", "f1"))
    return dict(schema_version=1,
                status="REVIEW_REQUIRED" if undefined else "METRICS_COMPUTED",
                scope="DECLARED_SINGLE_LABEL_CONFUSION_COUNTS_ONLY",
                orientation="EXPECTED_ROWS_PREDICTED_COLUMNS", **FLAGS,
                counts=dict(classes=len(rows), observations=observations, undefined_metrics=undefined),
                accuracy=ratio(correct, observations), classes=rows)


cases = [
    ("asymmetric", counts([[8, 2], [1, 9]]), 0,
     expected([metric("class_a", 10, 8, 1, 2), metric("class_b", 10, 9, 2, 1)], 20, 17)),
    ("perfect", counts([[3, 0], [0, 2]]), 0,
     expected([metric("class_a", 3, 3, 0, 0), metric("class_b", 2, 2, 0, 0)], 5, 5)),
    ("zero_scores", counts([[0, 2], [3, 0]]), 0,
     expected([metric("class_a", 2, 0, 3, 2), metric("class_b", 3, 0, 2, 3)], 5, 0)),
    ("no_predictions", counts([[0, 1], [0, 1]]), 1,
     expected([metric("class_a", 1, 0, 0, 1), metric("class_b", 1, 1, 1, 0)], 2, 1)),
    ("no_support", counts([[0, 0], [1, 1]]), 1,
     expected([metric("class_a", 0, 0, 1, 0), metric("class_b", 2, 1, 0, 1)], 2, 1)),
    ("absent_class", counts([[1, 0], [0, 0]]), 1,
     expected([metric("class_a", 1, 1, 0, 0), metric("class_b", 0, 0, 0, 0)], 1, 1)),
    ("invalid_counts", counts([[0, 0], [0, 0]]), 2,
     dict(status="ERROR", code="TOTAL_COUNT_INVALID", **FLAGS)),
]
selected = []
for name, value, exit_code, result in cases:
    control = WORK / (name + ".json")
    write_new(control, (json.dumps(value, ensure_ascii=True, sort_keys=True) + "\n").encode())
    selected.append((name, control, exit_code, result))
write_new(WORK / "unrelated.txt", b"FICTIONAL_EXTRA_NOT_A_SELECTED_COUNT_FILE\n")
write_new(WORK / "prior-capture.txt", b"Fictional previous capture must stay unchanged\n")


def snapshot_tree():
    entries = sorted(WORK.rglob("*"))
    tree = [(path.relative_to(WORK).as_posix(), path.is_dir()) for path in entries]
    hashes = {path.relative_to(WORK).as_posix(): sha(path.read_bytes())
              for path in entries if path.is_file()}
    return tree, hashes


original = snapshot_tree()
runtime_hash = sha(SCRIPT.read_bytes())
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
results = []
for name, control, exit_code, complete_expected in selected:
    completed = subprocess.run(
        [sys.executable, "-B", "-s", "-X", "utf8", str(SCRIPT), "--counts", str(control)],
        cwd=WORK, env=environment, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=60,
    )
    assert completed.returncode == exit_code, (name, "EXIT_MISMATCH")
    assert completed.stderr == "", (name, "UNEXPECTED_STDERR")
    assert completed.stdout.endswith("\n") and len(completed.stdout.splitlines()) == 1
    actual = json.loads(completed.stdout)
    assert actual == complete_expected, (name, "FULL_JSON_MISMATCH")
    assert str(WORK) not in completed.stdout.replace("\\\\", "\\")
    assert "FICTIONAL_EXTRA_NOT_A_SELECTED_COUNT_FILE" not in completed.stdout
    assert snapshot_tree() == original, (name, "INPUT_TREE_OR_PRIOR_CAPTURE_CHANGED")
    assert sha(SCRIPT.read_bytes()) == runtime_hash, (name, "RUNTIME_CHANGED")
    results.append(dict(case=name, exit_code=completed.returncode, report=actual))

print(json.dumps(dict(
    cases=results, input_counts_tree_prior_output_and_runtime_bytes_preserved=True,
), ensure_ascii=True, sort_keys=True, indent=2))
```

The driver checks sampled byte/tree preservation, not access times, every OS
property or ACL privacy. Its requested private file modes remain subject to the
actual OS, Python and inherited permissions. There is no automatic cleanup or
rollback. Inspect the retained invented work before removing it yourself.

## Interpret the arithmetic contract

The root has exactly `schema_version`, `classes` and `counts`; version is integer
1. Declare **1–32 unique class IDs**, each matching `[a-z][a-z0-9_-]{0,39}`.
The matrix is square in declared class order. Cells are actual integers from
**0 through 1000000000**, and the total is **1 through 1000000000000**. The
selected UTF-8 JSON may include a BOM and is at most **64 KiB**. Duplicate
keys/classes, wrong types, Boolean cells, ragged rows, unknown fields and
nonstandard numbers are input errors. These are not complete CPU/memory/I/O
quotas. See the [full schema and metric references](README.md).

For each class, support is the expected row total. TP is its diagonal cell;
FP is its predicted column total minus TP; FN is its expected row total minus
TP. Precision is `TP/(TP+FP)`, recall is `TP/(TP+FN)` and F1 is calculated
directly as `2*TP/(2*TP+FP+FN)`. Accuracy is diagonal sum divided by positive
total. Each denominator is considered independently; undefined precision or
recall does not automatically make direct F1 undefined.

Defined results contain exact unreduced integer pairs. They are not rounded,
converted to floats or normalized: `0/d`, `n/n` and raw F1 `2*n/(2*n)` remain
as calculated. A zero denominator produces exactly `status: UNDEFINED`,
`numerator: null`, `denominator: 0`. Undefined is neither a zero score nor a
one score. Count every undefined precision, recall and F1 separately. Exit 1
requires review for undefined metrics; exit 0 can describe entirely wrong
predictions with positive denominators. No quality threshold is applied.

This is closed-set single-label arithmetic only. There are no macro/micro/
weighted averages, probability inputs, multilabel semantics, automatic positive
class, rankings, winner selection or model-quality claims. Class output retains
declaration order. All five verification/action flags remain false on every path.

## Privacy, paths and remaining limits

Results omit the raw matrix as an input field, selected path, extra metadata
and native errors. They retain class IDs, supports, TP/FP/FN counts and exact
ratios. A binary input matrix can be reconstructed from this output. Real
counts can disclose sensitive evaluations even when no individual record is
present. Fixed CLI errors do not anonymize library tracebacks or caller captures.

Use fully spelled canonical paths and stable trusted local inputs. The reader
requires an ordinary single-link file and ordinary ancestors, and samples
descriptor/path identity around a bounded read. Component checks happen after
absolute-path normalization. Local Windows fictional probes on Python 3.12.7
and 3.15.2 accepted leaf trailing-dot, leaf trailing-space and parent
trailing-dot spellings, while refusing the parent trailing-space spelling.
This is retained normalization behavior, not a blanket suffix-refusal or
alias-safety guarantee. Do not rely on those aliases. Observed links/reparse
points, special files, stream/device/UNC forms, traversal and reserved names
are unsupported inputs.

The reader does not hold an atomic snapshot, deny concurrent writers or enforce
a hostile-filesystem sandbox. Remote/mounted/virtual/live-changing storage,
mount rebinding and blocked OS I/O remain outside the qualification. Reads can
affect access metadata, and Python caches are separate; this guide uses `-B`.
Exit 130 means interruption; a partial or failed stdout capture is not a
completed report. No model, corpus, sample, prompt/response, probability,
provenance, timestamp, evidence or source-build field is supported, and no
attachment is opened. No input, output or test authorizes model deployment or
publication of actual evaluation counts. Read the [private workspace guide](docs/PRIVATE-WORKSPACE.md),
[qualification boundary](docs/QUALIFICATION.md) and [provenance](docs/PROVENANCE.md)
before using your own private declarations.
