# Compare saved CSV exports

Download the source ZIP and compare its SHA-256 with `SHA256SUMS.txt`. On Windows
use `Get-FileHash -Algorithm SHA256 .\query-result-csv-comparator-0.1.0.zip`.
On Ubuntu use `sha256sum query-result-csv-comparator-0.1.0.zip`.

Extract the ZIP and open a terminal in the extracted folder. Use Python 3.12 or
3.15. Substitute your Python executable for `python` in the examples. The CLI
uses the standard library and requires no package installation.

```text
python -B -m rdl_query_lab.compare_results examples/left.csv examples/same.csv
python -B -m rdl_query_lab.compare_results examples/left.csv examples/renamed.csv --mapping examples/columns.json
python -B -m rdl_query_lab.compare_results examples/left.csv examples/changed.csv --max-examples 0
python -B -m rdl_query_lab.compare_results examples/left.csv examples/invalid-header.csv
```

The first two commands each match three rows and exit 0. The third matches two
rows and reports one extra row on each side, then exits 1. The fourth rejects
duplicate headers, prints a diagnostic to stderr and exits 2.

Supply UTF-8 CSV with a header and a consistent number of fields per row. A UTF-8
BOM and properly quoted commas and multiline fields are supported. When names
differ, supply a JSON object mapping each left column name to a distinct right
column name. The mapping must cover both headers. Values retain their exact text,
including whitespace, case, numeric formatting and embedded line endings.

Use `--max-examples 0` to omit row fingerprints. The default is five per side and
the maximum is twenty. Fingerprints of predictable values can be guessed. Keep
reports and input diagnostics in a location suited to the sensitivity of the data.
Use files that fit in memory because comparison retains distinct rows from both
inputs. A match describes the supplied exports. Use matching report parameters
and export conventions when comparing results from two systems.

Run the original unit suite from the extracted folder with
`python -B -m unittest discover -s tests -v`. `VALIDATION.json` in the release
records all seven tests and nine file-based CLI checks per profile, together with
the source commit, ZIP checksum and interpreter pins.
