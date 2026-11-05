# OUTLANDS sixteen-tool install bundle

This ZIP contains sixteen independent MIT Python wheels, four collection wheels,
and selector v1.2.0. Python 3.12 or 3.13 and pip are required separately. It includes
a machine-readable component guide, checksums and a manifest. No runtime, private
input, user profile, cache, journal or application adapter is included.

Download the ZIP and outer SHA256SUMS.txt from the same
[release](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/public-tools-install-bundle-v1.2.0).
Verify the ZIP before extraction into a new folder outside a source checkout.
The extracted SHA256SUMS.txt pins all twenty-one wheels in `wheels/`;
MANIFEST.json pins every other archive member.

Create a fresh environment outside the extraction folder: Windows PowerShell
`py -3.12 -m venv ../ENV`, or Ubuntu `python3.12 -m venv ../ENV`.
From the extracted root, choose one command and substitute that environment's Python:

```text
python -m pip install --no-index --no-deps wheels/outlands_cache_key_contract_checker-1.0.0-py3-none-any.whl
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[routing]==1.2.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[ai]==1.2.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[probability]==1.2.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[cache]==1.2.0"
python -m pip install --no-index --find-links wheels "outlands-public-tools-collection[all]==1.2.0"
```

The first installs one tool; substitute any other individual filename from
COMPONENTS.json. The remaining commands choose a four-tool group or all sixteen.
On Windows PowerShell, substitute `& ../ENV/Scripts/python.exe` for `python`;
on Ubuntu use `../ENV/bin/python`. Commands are in the environment's Scripts or bin
directory. `outlands-public-tools` lists component commands and actual installed
state. Run a listed tool's command with `-demo` appended for its embedded fictional
fixture. Use an explicit private JSON file for project data. `--no-index` avoids
package indexes and `--find-links wheels` resolves only local bundle dependencies.

The [general terms](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/methodology/TERMS.md),
[model routing guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/model-routing/README.md),
[AI decision guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/ai-decision-contracts/README.md),
[probability guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/probability-integrity/README.md) and
[cache/retry guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/cache-retry/README.md)
explain definitions, examples, APIs, result interpretation and system use cases.

The tools inspect caller-supplied declarations. They do not run models, fit/apply
calibration maps, dispatch requests, read/change caches, authenticate receipts,
write real ledgers or guarantee exactly-once execution. The selector installs
packages without wiring them to a system. Other public tools in the
[install plan](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/integrations/INSTALL-PLAN.md)
remain outside this sixteen-tool ZIP. Public MIT attribution is retained;
archive timestamps and permissions are fixed synthetic values.
