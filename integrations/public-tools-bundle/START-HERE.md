# OUTLANDS eight-tool install bundle

This versioned ZIP contains eight independent MIT Python tool wheels, the two
four-tool collection wheels, and one selector wheel. It also contains a
machine-readable component list, wheel checksums and this guide. Python 3.12 or
3.13 and `pip` must be supplied separately. No runtime, models, private inputs,
user profile or application adapter is included.

Download the ZIP and the **outer** `SHA256SUMS.txt` from the same
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/public-tools-install-bundle-v1.0.0).
Verify the ZIP before extraction. After extraction, the **inner**
`SHA256SUMS.txt` pins all 11 wheels in `wheels/`; `MANIFEST.json` pins every other
archive member. Extract into a new folder outside a source checkout.

Create a fresh virtual environment outside that folder. For example, on Windows
PowerShell run `py -3.12 -m venv ..\ENV`; on Ubuntu run
`python3.12 -m venv ../ENV`. From the extracted root, choose one install
command, substituting the environment's Python for `python`:

```text
python -m pip install --no-index --no-deps wheels/outlands_model_capability_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[routing]==1.0.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[ai]==1.0.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[all]==1.0.0"
```

The first line is an example of one independent tool. Replace its filename with
any other individual wheel listed in `COMPONENTS.json`. The next three lines
select model routing, AI decision contracts, or all eight. Run
`outlands-public-tools` after installing a selector extra to list the group and
individual commands. Run a tool's `-demo` command for its embedded fictional
fixture; pass a real JSON file only in your private project environment.

On Windows PowerShell, call the environment's Python as
`& ..\ENV\Scripts\python.exe -m pip ...` and commands from `..\ENV\Scripts\`.
On Ubuntu, use `../ENV/bin/python -m pip ...` and commands from `../ENV/bin/`.
Use a newly created environment for a clean install. `--no-index` prevents
package-index resolution; `--find-links wheels` confines dependency selection
to this extracted bundle.

The [plain-language terms](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/methodology/TERMS.md),
[model-routing guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/model-routing/README.md) and
[AI decision-contract guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/ai-decision-contracts/README.md) explain inputs,
outputs, Python APIs, examples and limits. The tools inspect caller-supplied
declarations. They do not load models, dispatch requests, run inference,
authenticate receipts, relabel records, train or deploy candidates. The
selector installs packages; it does not connect them to a particular system or
make them interoperate. The [222-tool install plan](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/INSTALL-PLAN.md) lists
other public tools and review gaps; they are outside this eight-tool ZIP.
