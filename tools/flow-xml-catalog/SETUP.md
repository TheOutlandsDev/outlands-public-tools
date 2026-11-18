# Verify and compare fictional flow XML files

Verify the downloaded ZIP using `SHA256SUMS.txt` and extract it. Use
`Get-FileHash -Algorithm SHA256` on Windows or `sha256sum` on Ubuntu. Open a
terminal at the extracted root and use an x64 CPython 3.12 or 3.15 executable.
Substitute your chosen executable for `python` below.

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe
```

On Ubuntu:

```sh
python -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python
```

Run the following in the Python prompt:

```python
from pathlib import Path
from production_planning.flow_catalog import compare_flows, load_verified_catalog
from production_planning.flow_xml import export_normalized_flow_xml

catalog = load_verified_catalog(Path("data/flow_xml_manifest.json"), Path("data/flow_xml_inputs"))
flows = {entry.filename: catalog.documents[entry.sha256] for entry in catalog.manifest.sources}
left, right = flows["demo-panel-7.xml"], flows["demo-panel-9.xml"]
changes = compare_flows(left, right)
print(changes["step_count_delta"], changes["rework_path_count_delta"])
print([row["position"] for row in changes["changed_positions"]])
normalized_xml = export_normalized_flow_xml(right)
```

The example prints `4 3` and `[2, 39, 40, 41, 42]`. The normalized XML is a
reference format. It contains flow identifiers, step names and rework paths.
The exporter omits creator and modifier metadata and marks the result as
incompatible with MES import. The comparison reports rework-path count changes
alongside position-by-position step changes.

Use trusted UTF-8 flow exports and a trusted manifest. Each listed file must
match the manifest's hash, name, version and counts. Missing or changed files
and duplicate active versions raise `FlowCatalogError`. The preserved parser
accepts flow XML up to one megabyte. Qualification exercises the original
format and UTF-8 parser checks. Keep operational XML and derived reports private.

To run the tests, install `requirements-test.txt` in place of the runtime list
using the same pip flags. Then run `python -B -m pytest -q -p no:cacheprovider tests`
with the virtual environment's Python. The two requirements files pin Pydantic
2.14.3, pytest 9.2.0 and their dependencies. `WHEEL-LOCK.json` records the approved
wheel hashes. `VALIDATION.json` lists the four Windows and Ubuntu profiles with
Python 3.12.16 and 3.15.2, the wheels installed and their test results.
