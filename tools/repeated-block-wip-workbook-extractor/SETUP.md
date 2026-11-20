# Using the repeated-block WIP workbook extractor

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/repeated-block-wip-workbook-extractor-v0.1.0). Compare the ZIP hash before extracting. On Windows use Get-FileHash -Algorithm SHA256 with the ZIP path. On Ubuntu use sha256sum -c SHA256SUMS.txt.

Run from the extracted directory with Python 3.12.16 or 3.15.2.

~~~powershell
python -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $python -B examples/make_inventory.py fictional-inventory.xlsx
$digest = (Get-FileHash -Algorithm SHA256 fictional-inventory.xlsx).Hash
& $python -B wip_workbook.py fictional-inventory.xlsx --sha256 $digest --expected-count 131
~~~

~~~bash
python -m venv .venv
python=.venv/bin/python
"$python" -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
"$python" -B examples/make_inventory.py fictional-inventory.xlsx
digest=$(sha256sum fictional-inventory.xlsx | cut -d ' ' -f 1)
"$python" -B wip_workbook.py fictional-inventory.xlsx --sha256 "$digest" --expected-count 131
~~~

The generator creates a new workbook with 26 headers and 131 fictional lot rows. For a real saved snapshot, get the expected digest from your accepted manifest before extraction. The report preserves source row numbers and skips blank, total, and incomplete identity rows. An expected item count is optional.

The sheet name is FPC_Production_Inventory. The extractor checks the original column band and 26 repeated header blocks, limits sheets to 10,000 rows, and reads cached cell values through openpyxl. Whole-number quantities must fit within 53 bits and satisfy the typed record constraints. A checksum mismatch, malformed header, invalid quantity, or duplicate material ID returns exit code 2 with no JSON report.

To normalize the result, copy its records array into the bundled examples/normalization.json structure and supply the normalization configuration that applies to your snapshot. Run the bundled wip_supply.py with --input and that JSON file. Extraction reads the workbook and writes its report to stdout.
