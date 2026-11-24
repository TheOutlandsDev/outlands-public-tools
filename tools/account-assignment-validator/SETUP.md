# Offline Account Assignment Validator

Check a saved account assignment and return the normalized access level, functional roles, lab scopes, and active flag. The CLI reads local JSON and makes no account changes.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt, then extract the archive. Use Python 3.12.16 or 3.15.2. From the extracted directory on Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B account_assignment.py examples/assignment.json
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B account_assignment.py examples/assignment.json
~~~

The runtime uses hash-pinned Pydantic 2.14.3 and its pinned dependencies.

## Assignment rules

Set access_level to standard, power, or developer. The optional functional_roles list defaults to empty, lab_scopes defaults to flex, and active defaults to true. The validator checks role and scope names against the bundled vocabulary. The fictional example shows how duplicate entries are removed in first-occurrence order.

The all scope is valid only for developer access and must be the sole scope. Standard access cannot use roles that require Power User access. Unknown fields and invalid combinations return exit status 2 with empty standard output.

A passing result confirms the saved combination satisfies the assignment schema. A live application separately checks who may apply an assignment.
