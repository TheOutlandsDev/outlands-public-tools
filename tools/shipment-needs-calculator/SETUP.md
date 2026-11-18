# Calculate open shipment demand from fictional records

Download the source ZIP and `SHA256SUMS.txt` from the release page.
Verify the ZIP digest before extracting it.

Windows PowerShell

```powershell
Get-FileHash -Algorithm SHA256 .\shipment-needs-calculator-0.1.0.zip
```

Ubuntu

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Open a terminal at the extracted root. Use CPython 3.12 or 3.15.

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

Save the following as `demo_shipment_report.py` at the extracted root.

```python
from pathlib import Path
from production_planning.what_is_needed import evaluate_comparison_case

folder = Path("data/flex_planning")
evaluated = evaluate_comparison_case(
    case_path=folder / "comparison_cases/demo_shipment_needs.json",
    mapping_path=folder / "demo_part_modality.json",
)
print(evaluated.result.open_need_count, evaluated.result.retained_demand_quantity)
print(evaluated.result.active_products)
```

Run `.\.venv\Scripts\python.exe demo_shipment_report.py` on Windows or
`.venv/bin/python demo_shipment_report.py` on Ubuntu.

The example prints `2 325` and `('7000011-DEMO',)`. It excludes rows with
nonpositive demand, a supplied shipped quantity, or a dock date. A supplied
shipped quantity of zero also excludes the row. Retained rows sort by ship
date and then source ID. Due-product dates on or after the earliest retained
ship date count toward the active product list.

Use `determine_parts_to_ship` to calculate results from your own trusted,
typed shipment and due-product records. Use `evaluate_comparison_case` to
check a saved result against the calculation. The bundled case uses a
fictional legacy filename and digest. The evaluator compares those metadata
values with the configuration. It executes no legacy program.

Install `requirements-test.txt` with the same pip flags to run the 12 test
cases. Use the virtual environment's interpreter for
`python -B -m pytest -q -p no:cacheprovider tests`. The release's
`VALIDATION.json` records the tested platforms, dependency pins, and
fresh-extraction API checks.
