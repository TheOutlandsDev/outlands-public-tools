# Offline Account Directory Filter and Paginator

Read a saved account directory, apply status and assignment filters, and return one page of matching accounts.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt, then extract the archive. Use Python 3.12.16 or 3.15.2. From the extracted directory on Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B account_directory_filter.py examples/directory.json --status pending-first-sign-in
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B account_directory_filter.py examples/directory.json --status pending-first-sign-in
~~~

The runtime uses hash-pinned Pydantic 2.14.3 and its pinned dependencies.

## Input and output

Supply an accounts array using the fictional example as a schema guide. Account records carry a unique username, display name, access level, role and lab lists, active flag, and password-change-required flag. A saved prior password-change value distinguishes reset-required from first sign-in when a change is required.

Use --status, --access-level, --functional-role, and --lab-scope to narrow results. A blank lab scope means Any lab scope. The all scope selects records explicitly assigned All labs. The flex scope selects records explicitly assigned Flex. Multiple filters must all match.

The reporter sorts by lowercase display name and then lowercase username. The page size is 25, and --page accepts 1 through 100. The reported total is the number of matches before pagination. The output contains only the display fields used by this report. The CLI reads local files and invalid requests return exit status 2 with empty standard output.
