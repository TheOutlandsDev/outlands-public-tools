# Using the order revision comparator

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/order-revision-comparator-v0.1.0). Compare the ZIP hash before extracting. On Windows use Get-FileHash -Algorithm SHA256 with the ZIP path. On Ubuntu use sha256sum -c SHA256SUMS.txt.

From the extracted directory, use Python 3.12.16 or 3.15.2.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe -B order_revisions.py examples/active.json examples/candidate.json --limit 1
~~~

~~~bash
python -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python -B order_revisions.py examples/active.json examples/candidate.json --limit 1
~~~

The report shows two additions, two removals, and two changes, with one detail from each category. The limit affects each detail list and leaves the full counts intact. The original truncation flag indicates that the combined count exceeds the specified limit. The default limit is 100, and zero returns counts with empty detail lists.

An identity is the source sheet, part number, purchase order, purchase order line, and commit date. Changing an identity field appears as an addition and a removal. A change to the source row is ignored. Both snapshots must have unique identities, and identity fields cannot contain a pipe because it separates the fields in the reported key.

Inputs are ordinary UTF-8 JSON files up to 1 MiB each, with an orders array of at most 1,000 records. See the examples for the required fields. Invalid snapshots return exit code 2. The CLI prints results to stdout and leaves both files untouched.
