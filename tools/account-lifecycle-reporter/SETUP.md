# Offline Account Lifecycle Reporter

Classify a saved list of accounts using its lifecycle flags. The CLI returns each account ID and state, with a total for each state.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt, then extract the archive. Use Python 3.12.16 or 3.15.2. From the extracted directory on Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B account_lifecycle.py examples/accounts.json
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B account_lifecycle.py examples/accounts.json
~~~

The runtime uses hash-pinned Pydantic 2.14.3 and its pinned dependencies.

## Input and output

Use an accounts array with a unique account_id for each record. The active and password_change_required flags may be omitted and default to false. Use null or omit password_changed_at when no prior change is recorded. A nonempty value records that a change occurred. The classifier uses its presence alone.

Inactive accounts stay inactive. An active account requiring a password change is pending_first_sign_in when it has no prior change, or password_reset_required when it has one. Other active accounts report active.

The CLI reads only the saved snapshot. It prints account IDs, lifecycle states, and counts. Additional fields in the input are omitted from the output. Validation errors return status 2 and empty standard output.
