# Validate a fictional production workflow contract

Download the source ZIP and `SHA256SUMS.txt` from the release page and verify
the ZIP before you extract it.

On Windows, run this command in PowerShell and compare the hash to the ZIP
entry in `SHA256SUMS.txt`.

```powershell
Get-FileHash -Algorithm SHA256 .\production-workflow-contract-validator-0.1.0.zip
```

On Ubuntu, run this command from the download directory.

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Open a terminal at the extracted root. The commands below use `python` for
CPython 3.12 or 3.15. Substitute the full path to that interpreter if needed.

Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-runtime.txt
```

Ubuntu

```sh
python -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-runtime.txt
```

Save the following as `validate_workflow.py` at the extracted root.

```python
from pathlib import Path
import sys

from production_planning.internal_panel_flex_contract import (
    internal_panel_flex_contract_sha256,
    load_internal_panel_flex_contract,
)

candidate = Path(sys.argv[1]) if len(sys.argv) > 1 else None
contract = load_internal_panel_flex_contract(candidate)
print(
    f"{len(contract.products)} products, {len(contract.state_model.states)} states, "
    f"{len(contract.state_model.transitions)} transitions, "
    f"{len(contract.event_identities)} event types"
)
print(f"Production included = {contract.production_included}")
print(internal_panel_flex_contract_sha256(candidate))
```

Run one of the following commands from the extracted root.

```powershell
.\.venv\Scripts\python.exe validate_workflow.py
```

```sh
.venv/bin/python validate_workflow.py
```

The first line prints `5 products, 4 states, 3 transitions, 4 event types`.
The next two lines show `Production included = False` and the 64-character
SHA-256 checksum of the validated JSON file.

To check a candidate, append its path to the command. The candidate must meet
the bundled schema and use the expected fictional mappings, workflow states,
transitions, and event identities. A changed product mapping, a duplicate
event identity, or a production permission flag set to true raises
`InternalPanelFlexContractError`. The validator also rejects empty files and
files larger than 128 KiB. Permission flags describe the contract and have no
effect outside the validator.

To run the 15 original test cases, install `requirements-test.txt` with the
same pip flags. Run `python -B -m pytest -q -p no:cacheprovider tests` with
the virtual environment's interpreter. See `VALIDATION.json` in the GitHub
release for the test results, pinned dependencies, and checks from fresh ZIP
extractions.
