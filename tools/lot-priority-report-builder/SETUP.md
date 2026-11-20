# Build a lot priority report from a saved plan

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the source ZIP against SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The runtime lock pins Pydantic 2.14.3 and its dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_plan.py demo.json
& $py lot_priority.py demo.json
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_plan.py demo.json
.venv/bin/python lot_priority.py demo.json
~~~

The generator requires a new file. The example prints four ranked lots with shipment due dates, remaining days, current steps, and risk labels. The input file is unchanged.

## Input and output

Use the demo JSON as a template. The input holds a case ID, source status, and saved plan. The plan contains a planning date, product modality, and orders with due dates and saved allocations. Other fields in the nested plan are ignored. Use ISO dates and integer quantities and day counts. The limit is 250 orders and 250 allocations total in a 2 MiB file.

Rows sort by priority rank, shipment due date, remaining completion days, and lot ID. The projection uses the saved day counts and risk values. Overdue lots receive past-due emphasis, and yield is emitted as null. An empty plan or a plan with no allocations yields an empty report. Invalid input exits with status 2, prints a diagnostic to stderr, and produces no report.

To run the adapted original projection test, install the hash-pinned test requirements in the same environment and run python -m pytest -q from the extracted directory. The release records also include six copied-runtime CLI checks across all four Windows and Ubuntu Python profiles.
