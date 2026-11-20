# Extract orders and part mappings from a saved workbook

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Download and verify the release ZIP against the published SHA-256 manifest, extract it, and open a terminal in the extracted directory. The runtime lock pins openpyxl 3.1.5, Pydantic 2.14.3, and their dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_orders.py fictional-orders.xlsx
$hash = (Get-FileHash -Algorithm SHA256 fictional-orders.xlsx).Hash
& $py order_mapping_workbook.py fictional-orders.xlsx --sha256 $hash
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_orders.py fictional-orders.xlsx
hash=$(sha256sum fictional-orders.xlsx | cut -d ' ' -f 1)
.venv/bin/python order_mapping_workbook.py fictional-orders.xlsx --sha256 "$hash"
~~~

The fictional example returns 118 customer orders, two panel orders, and nine part mappings. The example generator requires a new output path. For a workbook you received, obtain its expected digest from a trusted record before running the extractor.

## Workbook layout and report

- Use the generated workbook as the template for the three supported sheets. Customer orders use `C`, panel orders use `P`, and part mappings use `Mapping`. Headers start in row 3 and data in row 4. The extractor checks `B3:Y3` on both order sheets and `B3:G3` on the mapping sheet. Production and validation revision values are optional in columns J and K on the mapping sheet.
- For each row, `source_sheet` and `source_row` record its original location. Dates are ISO strings, quantities are integers, and decimal unit values are strings. Formula cells are read through their saved cached values. An Excel error such as `#REF!` in the lead-time cell is retained as text.
- An order row is skipped when its part number, quantity, or commit date is blank. A mapping row is skipped when its code or customer part number is blank. Order keys must be unique within each order sheet across part number, purchase order, line, quantity, and commit date. Mapping codes must be unique.
- The output is one JSON object with `source_sha256`, `customer_orders`, `panel_orders`, and `mappings`. For the Order Revision Comparator, combine the two order arrays into a JSON object with an `orders` array.
- The extractor checks the digest before ZIP/XML inspection, reads the workbook without changing it, and does not follow external links. Failed validation exits with status 2 and prints a diagnostic to stderr. It emits JSON only after every sheet passes.

## Reproduce validation

For the two adapted workbook tests, install the hash-pinned test requirements into the same environment and run `python -m pytest -q` from the source root. For the full matrix and copied-CLI checks, see the validation records attached to the release.
