# Review a saved planning source candidate

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the ZIP against the release's SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The runtime requirements pin openpyxl 3.1.5, Pydantic 2.14.3, and their dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_bundle.py demo-bundle
& $py source_candidate_review.py demo-bundle --baseline demo-bundle/baseline.json
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_bundle.py demo-bundle
.venv/bin/python source_candidate_review.py demo-bundle --baseline demo-bundle/baseline.json
~~~

The generator requires a new directory. The demo shows one added order, 32 source-row moves, four shipping updates, one dock update, and three potential lot ID collisions. With no baseline, the report sets the order comparison to null.

## Supported bundle

Use the generated files as format examples. Supply a manifest from a trusted source. It declares the status PRESERVED_PENDING_SOURCE_REVIEW, sets production_included to false, and lists exact lengths and SHA-256 digests for these files in order.

1. **orders.xlsx** holds the C, P and Mapping sheets used by the Order and Part Mapping Workbook Extractor. The manifest also declares the counts in that order and the expected panel row identities. A row ID is the first 24 characters of SHA-256 over the UTF-8 sheet, source row, part number, purchase order, and line joined with a pipe. Missing purchase orders and lines use an empty string.
2. **wip.csv** uses the generated column headers and dates in month/day/year and 12-hour time format. The manifest gives the expected WIP row count and the product names to include in panel totals.
3. **lot-log.xlsx** uses one LotStartLog sheet, with visible month numbers on row 3 and lot IDs in column D starting at row 5. IDs are ten uppercase letters or digits. The manifest gives the expected unique log count and the year and cutoff month for the WIP overlap check.
4. **last-lot.xlsx** uses one LastLotStarted sheet with headers on row 2. The manifest gives the expected registry row count. The reviewer checks proposed next lots against both the log and the WIP IDs.

The optional baseline JSON contains an orders array in the public Order Revision Comparator format. The reviewer verifies every bundle file before parsing the candidate data. It reads cached workbook values and leaves the input files unchanged. It writes JSON to stdout on success. Validation failures return exit status 2 and a diagnostic on stderr.

Install the pinned test requirements and run python -m pytest -q from the extracted source directory to run the two adapted tests. The release's validation records cover fresh offline dependency installs, reproducible builds, and copied-runtime CLI checks on all four platforms and Python combinations.
