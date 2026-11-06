# Install and use the test and evidence tools

Start with the [plain-language methodology](../../methodology/TEST-EVIDENCE.md)
and [machine-readable component guide](components.json). Each independent MIT
Python package provides a command, an embedded fictional demo and
`check(raw_json_bytes)` API. Supply Python 3.12 or 3.13; runtime code uses the
standard library only.

| Tool | When to use it | Fictional input and output | What the result establishes |
| --- | --- | --- | --- |
| [Test Case Manifest Checker](../../tools/test-case-manifest-checker/README.md) | Review a planned case cohort. | One HVAC flow case with its exact expectation: PASS and one present contract. | Declared expectation coverage. |
| [Test Run Coverage Checker](../../tools/test-run-coverage-checker/README.md) | Reconcile observations against that plan. | One complete matching flow observation: planned=1, completed=1, matched=1. A wrong output hash requires review. | Exact declared matching within the selected run. |
| [Regression Comparison Reporter](../../tools/regression-comparison-reporter/README.md) | Compare baseline and candidate runs. | Matching baseline and mismatching candidate with equal case pins: one regression. | Classification of compatible supplied observations. |
| [Evidence Completeness Checker](../../tools/evidence-completeness-checker/README.md) | Review required evidence roles. | One complete capture for a failed case: evidence PASS, observation matched=false. | Evidence declaration completeness, independently of test success. |

The individual source guides above define full schemas, row accounting, pin
derivation, refusals and limits. Definition and content hashes are opaque claims;
the tools do not run scripts, open artifacts or authenticate their provenance.

## Install one tool or the four-tool collection

Download the selected wheel(s), MANIFEST.json and SHA256SUMS.txt from the
[versioned release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/test-evidence-wheels-v1.0.0).
Verify SHA-256 before installing. One tool needs only its own wheel. For the
collection, download all five wheels into one directory outside the checkout.
Create a fresh environment with `py -3.12 -m venv ENV` on Windows or
`python3.12 -m venv ENV` on Ubuntu, then use its Python:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_test_case_manifest_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-test-evidence-collection==1.0.0
```

On Windows PowerShell substitute `& ./ENV/Scripts/python.exe` for `python`;
on Ubuntu use `./ENV/bin/python`. Commands live in that environment's Scripts or
bin directory. Run `outlands-test-case-manifest-checker-demo` for an embedded
fictional fixture, or `outlands-test-case-manifest-checker --input PRIVATE_JSON`
for a selected input. Substitute the other literal commands from components.json.
`outlands-test-evidence` lists the four commands. These are downloadable wheels;
no package-index registration is implied.

## Call a tool from another project

This example reads an embedded fictional fixture and performs no test execution:

```python
from importlib.resources import files
from outlands_test_run_coverage_checker.runs import check
raw = files("outlands_test_run_coverage_checker").joinpath("examples", "input.json").read_bytes()
report = check(raw)
assert report["status"] == "PASS"
assert report["assessment"]["planned_cases"] == 1
assert report["assessment"]["matched_cases"] == 1
```

For a project integration, explicitly select full case/run snapshots and map its
expectations and observations into the documented schema. Inspect status,
assessment, issue codes and scope pins together. Invalid outer API input raises a
fixed refusal; the CLI returns exit 2. REVIEW_REQUIRED is exit 1. A missing qualified
scope pin withholds qualification; a structural binding error withholds assessment.

## Worked workflow and system connection

Run `python -B integrations/test-evidence/exercise.py` from the repository root
using the collection environment's Python. It constructs fictional declarations,
checks the planned manifest, reconciles a baseline and a failing candidate,
identifies a regression, and accepts complete evidence without upgrading the
failed observation. It also exercises a missing role, changed contract and stale
run binding. This example provides explicit mappings; installation does not
connect the tools into an automatic pipeline.

The [Test & Evidence Workbench](../../systems/test-evidence-workbench/README.md)
stores case revisions, explicit execution trust, run plans, captured observations
and private evidence reviews. A caller-owned adapter could select those records
and map them into these contracts. It must distinguish raw-byte hashes from the
Workbench's parsed stdout and normalized-stderr comparisons, preserve incomplete
capture states, select attempts explicitly, and define case identities, expectation
derivation and evidence roles. Existing Workbench hashes and verdicts cannot be
copied as if their semantics were identical. No adapter or live integration is
implemented or qualified here. Unlike these declaration checkers, the Workbench
can execute trusted code only through its explicit trust/run workflow.

Actual case definitions, output bytes, policies, reviewer notes, store paths and
exports stay private. Neither evidence completeness nor PASS authorizes sharing.

## Build and qualification

Supply Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create an empty absolute
output directory outside the repository, then run
`python -B integrations/test-evidence/build_wheels.py --output DIRECTORY` and
`python -B integrations/test-evidence/verify_wheels.py --wheels DIRECTORY`.
The builder verifies exact public source manifests and isolates package imports.
Fixed synthetic ZIP metadata retains public MIT attribution and required package
metadata. Hosted Windows/Ubuntu Python 3.12/3.13 qualification fresh-installs each
tool and the collection, runs CLI/demo/API/review cases, the installed exercise and
the literal API example, then compares exact wheel and manifest bytes. Anonymous
public-download checks repeat after release. This qualifies package behavior on
fictional declarations, not authenticated execution, actual evidence or live systems.
