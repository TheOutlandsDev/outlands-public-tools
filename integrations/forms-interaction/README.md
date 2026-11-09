# Install and use the forms and interaction tools

Review a declared form, supplied values, an asserted interaction history and
selected version changes. Start with the [plain-language terms](../../methodology/FORMS-INTERACTION.md)
and [machine-readable component guide](components.json). Each independent MIT
wheel provides a command, embedded fictional examples and a Python API. Supply
Python 3.12 or 3.13; runtime dependencies are standard library only.

| Tool | When to use it | Fictional result | What it establishes |
| --- | --- | --- | --- |
| [Form definition checker](../../tools/form-definition-contract-checker/README.md) | Inspect fields, conditions and version identity before writing cases. | A service-request definition with conditional filter grade PASSes. | Consistency of one bounded custom form declaration. |
| [Form submission checker](../../tools/form-submission-contract-checker/README.md) | Check supplied values against an exact form version. | A complete service draft PASSes; missing or invalid required values need review. | Validity of the selected supplied values under the selected declaration. |
| [Transition history checker](../../tools/ui-transition-history-checker/README.md) | Review a claimed action sequence and submission guards. | A draft reaches the declared reviewed state through two valid steps. | Consistency of supplied events with a declared flow. |
| [Scenario comparator](../../tools/ui-interaction-scenario-comparator/README.md) | Compare identical selected cases under two exact versions. | Equal cases PASS; tightening the priority maximum changes outcomes and needs review. | Selected-case outcome equality or change. |

These tools read supplied assertions. They do not render HTML, inspect a DOM,
click controls, submit forms, authenticate, enforce permissions or execute a
workflow. A history PASS can take a declared invalid-submission branch. A
comparison PASS can describe matching expected-negative cases. Reports omit raw
values but retain IDs and hashes; keep actual project inputs and reports private.

## Install one tool or all four

Download selected wheels and SHA256SUMS.txt from the immutable
[v1.0.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/forms-interaction-wheels-v1.0.0).
Verify hashes before installing. Create a fresh environment outside the checkout
with `py -3.12 -m venv ENV` on Windows or `python3.12 -m venv ENV` on Ubuntu.
Then use that environment's Python and scripts directory:

```text
python -m pip install --no-index --no-deps WHEEL_DIRECTORY/outlands_form_submission_contract_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links WHEEL_DIRECTORY outlands-forms-interaction-collection==1.0.0
```

The collection requires all five release wheels in `WHEEL_DIRECTORY` and pins
the four components exactly. `outlands-forms-interaction` lists their commands.
`outlands-form-submission-contract-checker-demo` runs embedded fictional input.
`outlands-form-submission-contract-checker --input PRIVATE_JSON` checks selected
input. Use components.json to substitute another individual package or command.
On Windows use `ENV/Scripts/python.exe` and commands in `ENV/Scripts`; on Ubuntu
use `ENV/bin/python` and commands in `ENV/bin`. These are release-download wheels;
package-index registration is not implied.

## Call a tool from another project

The APIs are `forms.check`, `submissions.check`, `histories.check` and
`scenarios.check` in separate `outlands_TOOL` packages. Each accepts raw JSON
bytes and returns a report dictionary. For example:

```python
from importlib.resources import files
from outlands_form_submission_contract_checker.submissions import check

raw = files("outlands_form_submission_contract_checker").joinpath("examples", "input.json").read_bytes()
report = check(raw)
assert report["status"] == "PASS"
assert report["assessment"]["submissions"][0]["valid"] is True
assert report["browser_started"] is False
assert report["whole_ui_compatibility_verified"] is False
```

Replace the embedded example with your own reviewed JSON bytes for actual data.
Catch `outlands_form_submission_contract_checker.toolkit.Rejected` for refused
input. `REVIEW_REQUIRED` is a report, not an exception. CLI exits are 0 PASS,
1 REVIEW_REQUIRED, 2 refusal and 130 interruption. Commands emit JSON on stdout;
the source guides describe guarded fresh `--out` destinations.

## Worked service-request review

After installing all four, run `python -B integrations/forms-interaction/exercise.py`
from the repository root. The script imports only installed packages and their
embedded fictional examples. It checks:

1. The four positive examples PASS and the selected form, submission, flow and
   history cohort pins agree across tools.
2. The four review examples return REVIEW_REQUIRED.
3. Tightening a declared priority maximum from 5 to 1 under a new revision,
   with exact reference repinning, changes the selected submission and history
   outcomes; the comparator returns REVIEW_REQUIRED.
4. Identical expected-negative cases compare equal and PASS, while their
   submission and history validity remain false.

The script does not use repository imports, open a browser or contact an
application. Individual source guides give the complete input schemas, output
fields and validation boundaries.

## Relationship to Data & Services Stack

The [Data & Services Stack](../../systems/data-services-stack/README.md) has a
separate browser workbench with configuration, preview, run and report actions.
Its current public UI uses a JSON editor, input text, saved job snapshots and
actual loopback API actions. The tools here neither read that UI nor accept its
raw browser events or nested job configuration as a form declaration.

A possible **documented review use case** is to select a small, explicit scalar
projection of a proposed screen and interaction path before changing that UI.
A caller-reviewed mapping would need field IDs and types, visible/required rules,
state and action names, exact form/flow revisions and hash domains, which source
observation each asserted event came from, and how application effects are
checked separately. The fictional service-request example is not an assertion
that the stack implements that form or flow. No adapter or live system
integration is included; actual DOM behavior, accessibility, API effects,
authorization and persistence need separate evidence.

## Build and qualification

Use Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1. Create an empty
absolute output directory outside this checkout, then run:

```text
python -B integrations/forms-interaction/build_wheels.py --output OUTPUT_DIRECTORY
python -B integrations/forms-interaction/verify_wheels.py --wheels OUTPUT_DIRECTORY
```

The build verifies exact public SOURCE-MANIFEST pins for the four source
entries, shared modules, fictional examples, README and MIT license. It rewrites
imports only in isolated wheel staging. ZIP headers have fixed synthetic
metadata; standard package and license attribution remain. SHA256SUMS.txt and
release.json pin the wheel bytes. Qualification includes source tests,
individual and collection installs, CLI/demo/API/review cases, the installed
exercise and this guide's Python snippet. These checks do not establish actual
browser behavior or whole-UI compatibility.
