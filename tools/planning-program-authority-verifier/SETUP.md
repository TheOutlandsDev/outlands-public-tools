# Verify a saved development program authority index

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the source ZIP against SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The verifier uses the Python standard library.

## Windows PowerShell

~~~powershell
python examples/make_authority.py demo
python program_authority.py demo
~~~

## Ubuntu

~~~bash
python3 examples/make_authority.py demo
python3 program_authority.py demo
~~~

The generator requires a new directory. The fictional example verifies eight source files and reports ten parity capabilities. The CLI prints JSON on success. A failed check returns exit status 2, prints a diagnostic on stderr, and produces no report.

## Verify your own saved evidence

Use the generated authority-index.json as a template. Supply a trusted index for the intended development program. The index declares the expected state, review blockers, and a development-only scope. Its source catalog identifies each report by ID, relative path, role, and SHA-256. It requires explicit false values for production authority, activation, and database reads and writes, and integer zeroes for executed calculations and generated plans.

- The planning, configuration coverage, fixture coverage, platform, and migration JSON files supply the observed state. The planning, configuration, fixture, and migration reports also supply their recorded fingerprint. The verifier uses those saved reports and their byte hashes, so refresh the reports at their source before updating the index.
- The Markdown parity matrix is counted directly by capability category and classification. The CSV business input register and JSON system logic file are checked for byte integrity.
- The source fingerprint covers all eight verified hashes. The authority fingerprint also covers the four supplied semantic fingerprints and the combined observed state. JSON key order does not affect these canonical calculations. Changing a report's bytes requires an updated trusted file pin.

The verifier leaves input files unchanged. For the five adapted tests, create a virtual environment, install the hash-pinned requirements-test.txt with pip --require-hashes --only-binary=:all:, and run python -m pytest -q in the extracted directory. The release records cover all four Windows and Ubuntu Python profiles, including six CLI checks run from the extracted ZIP before any test dependencies are installed.
