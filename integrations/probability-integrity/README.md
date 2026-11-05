# Install and use the probability integrity tools

Start with the [probability definitions](../../methodology/PROBABILITY.md) and
[machine-readable component guide](components.json). These four independent
MIT Python packages inspect supplied declarations. Each has a command, embedded
fictional demo and `check(raw_json_bytes)` API. Python 3.12 or 3.13 is required;
the runtime code uses only the standard library.

| Tool | When to use it | Fictional result | What the result establishes |
| --- | --- | --- | --- |
| [Probability Vector Checker](../../tools/probability-vector-checker/README.md) | Check a project's class list and stated probabilities before selecting one class. | Four HVAC cases have complete vectors totaling 1/1. A game fixture covers three NPC choices. | Complete class coverage and exact totals under the declared taxonomy. |
| [Binary Probability Error Calculator](../../tools/binary-probability-error-calculator/README.md) | Score explicit positive-class probabilities against supplied binary outcomes. | Four HVAC cases have total error 3/8 and mean 3/32. | Exact arithmetic on the complete supplied cohort. |
| [Reliability Bin Reporter](../../tools/reliability-bin-reporter/README.md) | Inspect supplied predictions and outcomes in fixed ranges chosen by the caller. | Three HVAC bins have weighted absolute gap 1/4. | Descriptive differences for those cases and bin choices. |
| [Calibration Map Checker](../../tools/calibration-map-checker/README.md) | Review a proposed map's shape and revision before a separate project decision. | An unchanged map passes; changing its midpoint to 0.6 with a newer revision requires review. | Declared domain, monotonicity and revision consistency. |

## Install one tool or all four

Download the wheel(s), `MANIFEST.json` and `SHA256SUMS.txt` from the
[versioned wheel release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/probability-integrity-wheels-v1.0.0).
Verify each SHA-256 before installing. One tool needs only its own wheel; the
collection needs all five wheels together in a folder outside the source checkout.
Create a fresh virtual environment with `py -3.12 -m venv ENV` on Windows or
`python3.12 -m venv ENV` on Ubuntu. Use its Python for either command:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_probability_vector_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-probability-integrity-collection==1.0.0
```

On Windows PowerShell, substitute `& .\ENV\Scripts\python.exe` for `python`;
on Ubuntu use `./ENV/bin/python`. The environment's `Scripts` or `bin` directory
also contains `outlands-probability-vector-checker-demo`. Run that for the embedded
fictional example, or use `outlands-probability-vector-checker --input PRIVATE_JSON`.
The collection's `outlands-probability-integrity` command lists all four commands.
Every individual wheel can be installed by replacing the filename above with its
name from `components.json`. No package-index registration is implied.

## Call a tool from a project

```python
from outlands_probability_vector_checker.vectors import check
raw = b'{"format":"outlands-probability-vector-v1","taxonomy":{"id":"npc-options","revision":1,"labels":["move","wait"]},"cases":[{"id":"case-one","revision":1,"model":"npc-model","model_revision":1,"probabilities":[{"label":"move","value":"0.75"},{"label":"wait","value":"0.25"}]}]}'
report = check(raw)
assert report["status"] == "PASS"
assert report["assessment"]["all_vectors_valid"] is True
assert report["assessment"]["cases"][0]["probability_sum"]["exact_fraction"] == "1/1"
```

Pass JSON bytes, preserve exact decimal strings and inspect both status and the
relevant scope fields. A missing outcome makes the error/bin metrics null rather
than scoring just the available subset. Invalid outer input raises the tool's
fixed refusal; the CLI translates that to exit 2. The component guide names each
API, format, example and result fields. Original source guides remain the detailed
schema references. Each wheel also embeds `examples/input.json` and `needs-review.json`.

## Worked methodology and system connection

The [installed exercise](exercise.py) uses all four APIs on invented HVAC data:
validate four complete vectors, explicitly select the contract's positive label,
calculate error, copy the same binary scope into three caller-declared bins, and
review a revised map. Expected error is 3/8 total and 3/32 mean; the weighted bin
gap is 1/4. Removing one outcome withholds both aggregates. The exercise reviews
the map without applying it. Run it with the collection environment's Python.

The [ML Experiment Workbench](../../systems/ml-experiment-workbench/README.md)
already describes binary predictions, Brier error and reliability observations.
A future caller-owned adapter could map a selected immutable experiment's cases,
positive/negative labels, model revision, predictions and outcomes into these
contracts. The Workbench stores floating-point scores; these tools require exact
decimal strings with at most six fractional digits. An adapter must state and test
its rounding policy, case identity pins, full cohort coverage and treatment of
unknown labels. Its numbers may differ from the Workbench after rounding.
No adapter or live Workbench integration is included or qualified here. Keep real
experiments, outcomes and fitted map parameters private.

## Build and qualification

Build with Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create an empty
external output folder, then run `python -B integrations/probability-integrity/build_wheels.py --output FOLDER`
and `python -B integrations/probability-integrity/verify_wheels.py --wheels FOLDER`.
The build verifies source manifests before isolating imports into separate package
names. The release plan pins five wheels and two manifests. Fixed synthetic ZIP
headers remove local build times and paths; public MIT attribution is retained.
Hosted checks fresh-install each wheel and the collection on Windows and Ubuntu,
Python 3.12 and 3.13, compare exact build bytes, then repeat from anonymous public
downloads after publication. This is package/fictional-example evidence, without
model inference, fitted calibration, outcome-truth or production-quality claims.
