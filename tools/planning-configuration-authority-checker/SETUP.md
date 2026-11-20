# Check a saved planning configuration

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the release ZIP against SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The runtime lock pins Pydantic 2.14.3 and its dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_configuration.py demo
& $py configuration_authority.py demo --observed-part DEMO-01 --observed-part DEMO-13
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_configuration.py demo
.venv/bin/python configuration_authority.py demo --observed-part DEMO-01 --observed-part DEMO-13
~~~

The generator requires a new directory. The fictional example has 23 retained products, four detailed configurations, eight pending timing reviews, and 11 products with missing business inputs. It returns integrity PASS and a BLOCKED planning gate. Review the result's issues and product records for the missing inputs.

## Review your own saved inputs

Use the generated files as format examples. The checker reads policy.json, detail.json, part-map.json, and product-matrix.json from the supplied directory. The development-only matrix pins supporting evidence by relative path and SHA-256. Use one or more --observed-part flags to supply part numbers from saved orders. Part numbers are normalized to uppercase and repeated observations are counted once.

A successful check writes the full JSON report to stdout and exits with status 0. A reconciliation conflict writes a FAIL report and exits with status 2. An unreadable or invalid input exits with status 2 and writes a diagnostic to stderr. The checker reads inputs without changing them and does not generate plans.

Use --authority-summary to emit the saved configuration-coverage.json input for the Planning Program Authority Verifier. That verifier's index must pin the new report bytes and declare the matching gate_b state. Integrity conflicts prevent summary export. A BLOCKED gate with passing integrity can still be reported for review.

For the six adapted tests, install the hash-pinned test requirements and run python -m pytest -q in the extracted directory. The release records cover fresh offline installations and six CLI checks on all four Windows and Ubuntu Python profiles.
