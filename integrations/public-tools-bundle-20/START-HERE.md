# OUTLANDS twenty-tool install bundle

This ZIP contains twenty independent MIT Python tool wheels, five group installers
and selector v1.3.0. Supply Python 3.12 or 3.13 and pip separately. COMPONENTS.json,
checksums and a manifest describe the exact distribution. No runtime, private input,
profiles, caches/journals or application adapters are included.

Download the ZIP and outer SHA256SUMS.txt from the same
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/public-tools-install-bundle-v1.3.0).
Verify the ZIP before extraction into a new folder outside a source checkout.
The inner SHA256SUMS.txt pins all twenty-six wheels in wheels/; MANIFEST.json pins
every other archive member. Create a fresh environment outside the extracted folder:
Windows PowerShell `py -3.12 -m venv ../ENV`, or Ubuntu `python3.12 -m venv ../ENV`.
From the extracted root, choose one command using that environment's Python:

```text
python -m pip install --no-index --no-deps wheels/outlands_review_queue_contract_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[routing]==1.3.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[ai]==1.3.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[probability]==1.3.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[cache]==1.3.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[review]==1.3.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[all]==1.3.0"
```

The first installs one tool; substitute any individual filename from COMPONENTS.json.
The remaining choices install one four-tool group or all twenty. On Windows
PowerShell use `& ../ENV/Scripts/python.exe` for Python; on Ubuntu use
`../ENV/bin/python`. Commands are in the environment's Scripts or bin directory.
Run `outlands-public-tools` to list component commands and actual installed state.
Append `-demo` to an individual command for its embedded fictional fixture, or pass
an explicit private JSON input. `--no-index` avoids package indexes; `--find-links`
resolves the declared dependencies from this extracted bundle.

The [general terms](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/methodology/TERMS.md),
[model routing guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/model-routing/README.md),
[AI decision guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/ai-decision-contracts/README.md),
[probability guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/probability-integrity/README.md),
[cache/retry guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/cache-retry/README.md) and
[review/change guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/review-change/README.md)
explain definitions, examples, APIs, result interpretation and system use cases.

The tools inspect declarations. They do not run models, fit/apply calibration maps,
dispatch requests, operate caches, authenticate reviewers or receipts, execute
approvals, apply corrections, discover real dependencies, update targets or guarantee
exactly-once execution. The selector installs packages without wiring them to a system.
Other public tools in the [install plan](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/INSTALL-PLAN.md)
remain outside this twenty-tool ZIP. MIT attribution is retained; ZIP metadata is fixed.
