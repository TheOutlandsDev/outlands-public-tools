# Offline Activity Evidence Timeline Reporter

Read already-saved activity events and print a scoped timeline with counts and a page of matching events.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt, then extract the archive. Use Python 3.12.16 or 3.15.2. From the extracted directory on Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B activity_timeline.py examples/activity.json --page-size 2
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B activity_timeline.py examples/activity.json --page-size 2
~~~

The runtime uses hash-pinned Pydantic 2.14.3 and its pinned dependencies.

## Input and output

Supply an events array using the fictional example as a schema guide. Use an explicit UTC offset or Z in each occurred_at timestamp. Event details in the selected rows stay in the report.

The default operational scope covers os, production, lot_starts, panel_flex, and logistics. Use --scope developer to also include accounts and system. Scope is a view of the supplied file. The caller controls which saved evidence is supplied.

Use --domain to select one domain within the selected scope. Counts include zero for visible domains without matches. Results sort by timestamp descending, then event ID descending. Counts and total are calculated before paging. The first page is 1, page size defaults to 50, and sizes from 1 through 100 are accepted. The CLI reads only the supplied file and returns exit status 2 with empty standard output on invalid requests.
