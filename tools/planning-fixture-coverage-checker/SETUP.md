# Check saved planning fixture coverage

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the source ZIP against SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The runtime lock pins Pydantic 2.14.3 and its dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_fixture_catalog.py demo
& $py fixture_coverage.py demo --configuration-report demo/configuration-report.json
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_fixture_catalog.py demo
.venv/bin/python fixture_coverage.py demo --configuration-report demo/configuration-report.json
~~~

The generator requires a new directory. The demo has 11 required scenarios, four reusable scenarios, seven partial scenarios and zero authoritative expected-value fixtures. It passes integrity checks while the fixture gate remains BLOCKED.

## Audit your evidence

- Use the generated fixture-catalog.json as a template. Give the checker the full saved report from the Planning Configuration Authority Checker. The checker recomputes the report fingerprint and reconciles the product classifications and counts. Use reports and catalog pins from a trusted source.
- List required scenarios in their defined order. Each scenario declares test references in relative/path.py::test_function form and a gap statement when coverage is partial. The checker verifies a file's SHA-256 before reading its test definitions. It parses Python source without importing or running it.
- Dedicated legacy fixtures remain comparison evidence. Aggregate snapshots and missing test fixtures remain visible in the output. The checker leaves all inputs unchanged.
- The CLI prints a JSON report and exits with status 0 for integrity PASS, including a BLOCKED fixture gate. An integrity conflict returns status 2 with a FAIL report. Unreadable or invalid inputs return status 2 with a diagnostic on stderr.

Add --authority-summary to export the fixture-coverage.json report consumed by the Planning Program Authority Verifier. Pin the exported bytes in that verifier's index and declare the matching gate_c state. Integrity conflicts prevent authority-summary export.

To run the 11 adapted tests, install the hash-pinned test requirements and run python -m pytest -q from the extracted directory. The release validation records include six copied-runtime CLI checks across all four Windows and Ubuntu Python profiles.
