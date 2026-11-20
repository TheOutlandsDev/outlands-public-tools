# Using the order revision review ledger verifier

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/order-revision-review-ledger-verifier-v0.1.0). Compare the ZIP hash before extracting. On Windows use Get-FileHash -Algorithm SHA256 with the ZIP path. On Ubuntu use sha256sum -c SHA256SUMS.txt.

From the extracted directory, use Python 3.12.16 or 3.15.2.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe -B review_ledger.py examples/ledger.json --limit 1
~~~

~~~bash
python -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python -B review_ledger.py examples/ledger.json --limit 1
~~~

The example verifies two events and displays one, with AWAITING_REVIEW as the latest decision. Change the older event's decision in a copy and run again with a limit of one. The verifier returns exit code 2 and emits no report because it checks every supplied event before limiting the output.

The input is one ordinary UTF-8 JSON file up to 1 MiB. Put the revision hash in revision_sha256 and the saved event objects in the events array. Each event must reference that revision and include a timestamp with a time zone. The display limit is 1 to 100 and defaults to 20. An empty array reports AWAITING_REVIEW and zero verified events.

Event IDs check the consistency of the supplied event fields after canonical serialization. To establish completeness or reviewer identity, compare against a trusted copy or an independently authenticated record.
