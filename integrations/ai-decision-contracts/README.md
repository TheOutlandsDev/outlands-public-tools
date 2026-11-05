# Install AI decision-contract checks

Four MIT Python tools inspect caller-supplied decision declarations offline. Each
has an independent wheel and an embedded fictional demo. The collection wheel
declares exact-version dependencies on all four; it does not run them as a
pipeline. Python 3.12 or 3.13 is required. The earlier [source ZIP](../../downloads/ai-decision-contracts-4/README.md)
remains a folder-based alternative.

Start with the [plain-language terms](../../methodology/TERMS.md) and the
[machine-readable component guide](components.json). Every input and report can
contain private values. Use the supplied fictional HVAC/game examples to learn
the contracts; keep real inputs and reports in a private project directory.

| Task | Tool | Fictional input | Result to inspect |
| --- | --- | --- | --- |
| Compare prompt interfaces | [Prompt Contract Diff](../../tools/prompt-contract-diff/README.md) | Invented HVAC classifier before/after contracts | `changes`, taxonomy pins, `issues` |
| Check label changes | [Label Mapping Contract Checker](../../tools/label-mapping-contract-checker/README.md) | Invented filter-service to filter-check mapping | `assessment.mappings`, `record_level_rule_required`, `issues` |
| Reproduce a score policy | [Score & Abstention Policy Checker](../../tools/score-abstention-policy-checker/README.md) | Invented scores with one explicit abstention | `decisions`, `summary`, `issues` |
| Plan candidate review | [Candidate Evaluation Gate Planner](../../tools/candidate-evaluation-gate-planner/README.md) | Invented three-case HVAC cohort | `metrics`, `assessment.eligible_for_manual_review`, `issues` |

All four expose `check(raw_json_bytes)` and return a Python dictionary. `PASS`
means the supplied declarations meet that tool's checked rules; it does not
establish label truth, prompt safety, model quality, inference, authorization or
deployment. `REVIEW_REQUIRED` means inspect the reported issue. A fixed refusal
means the input could not be assessed. Each tool README defines its exact format,
bounds, output and limits.

## Download and install one tool

After publication, download the selected `.whl` file and `SHA256SUMS.txt` from
the [AI Decision Contracts Wheels v1.0.0 release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/ai-decision-contracts-wheels-v1.0.0).
Check the wheel's SHA-256 against the matching checksum line. In Windows
PowerShell, from a fresh download directory outside this repository:

```powershell
py -3.12 -m venv ..\outlands-ai-decision-env
& ..\outlands-ai-decision-env\Scripts\python.exe -m pip install --no-index --no-deps .\outlands_prompt_contract_diff-1.0.0-py3-none-any.whl
& ..\outlands-ai-decision-env\Scripts\outlands-prompt-contract-diff-demo.exe
```

On Ubuntu, use `python3.12 -m venv ../outlands-ai-decision-env`, then
`../outlands-ai-decision-env/bin/python` and the corresponding `bin/` command.
Each `-demo` command runs a fictional fixture embedded in its wheel without a
source checkout or real project data.

## Install all four

Download all five wheels to the same directory. The collection installer needs
the four individual wheels to resolve its exact dependencies offline:

```powershell
& ..\outlands-ai-decision-env\Scripts\python.exe -m pip install --no-index --find-links . outlands-ai-decision-contracts-collection==1.0.0
& ..\outlands-ai-decision-env\Scripts\outlands-ai-decision-contracts.exe
```

The collection command lists the four installed tool commands. Run each tool's
own `-demo` or pass an explicit JSON file with `--input`.

## Call a tool from a Python project

After installing its wheel, call the pure checking API with exact JSON bytes:

```python
from pathlib import Path
from outlands_label_mapping_contract_checker.labels import check

report = check(Path("private-input.json").read_bytes())
if report["status"] == "REVIEW_REQUIRED":
    raise RuntimeError("Review the reported mapping issues before continuing")
```

The other entry points are `outlands_prompt_contract_diff.prompts.check`,
`outlands_score_abstention_policy_checker.scores.check`, and
`outlands_candidate_evaluation_gate_planner.gates.check`. An application must
interpret each report and decide what to do next. A pin is a consistency check,
not an authenticity guarantee.

## Build from reviewed public source

With Python 3.12/3.13, setuptools 80.9.0 and wheel 0.45.1, build into a new
empty directory outside the repository:

```text
python -B integrations/ai-decision-contracts/build_wheels.py --output NEW_EMPTY_EXTERNAL_DIRECTORY
python -B integrations/ai-decision-contracts/verify_wheels.py --wheels NEW_EMPTY_EXTERNAL_DIRECTORY
```

The builder checks each copied file against its public source manifest and
normalizes ZIP metadata. The verifier checks exact release hashes, member paths,
metadata, fresh individual and collection installs, CLI demos and Python APIs.
The [release plan](release.json) pins all seven assets.

## System relationship

The [Corpus & Model Workbench](../../systems/corpus-model-workbench/README.md)
and [ML Experiment Workbench](../../systems/ml-experiment-workbench/README.md)
are related public projects. These wheels do not import their records or install
an adapter. An integration would need explicit schema mapping, refusal handling,
private-instance rules and tests against the selected system. The
[task-to-system map](../../docs/TOOL-TO-SYSTEM-MAP.md) records this use case.
