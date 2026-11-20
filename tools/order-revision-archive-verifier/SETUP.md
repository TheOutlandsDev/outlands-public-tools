# Using the order revision archive verifier

Download the source ZIP and SHA256SUMS.txt from the [release page](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/order-revision-archive-verifier-v0.1.0). Compare the ZIP hash before extracting. On Windows use Get-FileHash -Algorithm SHA256 with the ZIP path. On Ubuntu use sha256sum -c SHA256SUMS.txt.

From the extracted directory, use Python 3.12.16 or 3.15.2.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.\.venv\Scripts\python.exe -B examples/make_demo_archive.py demo-archive
.\.venv\Scripts\python.exe -B revision_archive.py demo-archive --limit 1
~~~

~~~bash
python -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python -B examples/make_demo_archive.py demo-archive
.venv/bin/python -B revision_archive.py demo-archive --limit 1
~~~

The fixture generator creates a new directory with two fictional XLSX files. The verifier checks both and prints one detail because the limit is one. The active pointer points to the older workbook and is verified even when that workbook is outside the display limit.

Each candidate uses the same 64-character lowercase SHA-256 as the name stem of its workbook and metadata file in the candidates directory. Metadata carries the same hash, byte size, original filename, status and upload time. An optional active.json contains the hash of a stored revision. With no active pointer, the reported active hash is null.

The verifier reads ordinary files and directories, checks every candidate before limiting the report, and returns exit code 2 for invalid archives. It allows up to 1,000 revisions, 25 MiB per workbook and 1 MiB per JSON file. The display limit is 1 to 100. It checks workbook bytes for integrity. Workbook contents and review events are outside the archive verification.
