# Offline Operator Workflow Transition Preview

Preview an acknowledgement, a note, or an exception command against a saved action status. The CLI prints the current and proposed status and the command name.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt. Use Get-FileHash -Algorithm SHA256 in Windows PowerShell or sha256sum -c SHA256SUMS.txt on Ubuntu. Extract the ZIP and open its top-level directory.

Use Python 3.12.16 or 3.15.2. In Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B operator_transition.py examples/flag-exception.json
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B operator_transition.py examples/flag-exception.json
~~~

The requirements pin Pydantic 2.14.3 and the runtime wheels qualified on Windows and Ubuntu x64.

## Prepare a request

Set current_status to OPEN, ACKNOWLEDGED, EXCEPTION, or RESOLVED. The change object carries command, expected_version, and any note or exception_code required by the command. The examples use fictional actions.

- ACKNOWLEDGE moves OPEN to ACKNOWLEDGED.
- ADD_NOTE requires a note and keeps the current status.
- FLAG_EXCEPTION requires a note and an exception code and moves the action to EXCEPTION. An action already in EXCEPTION rejects another flag.
- RESOLVE_EXCEPTION requires a note and moves EXCEPTION to RESOLVED.

The command schema requires a nonnegative expected_version. A live application compares that value with saved state during a write. This preview validates the command field and uses only the supplied status.

The example flag-exception request prints ACKNOWLEDGED as the current status and EXCEPTION as the proposed status. Invalid requests and disallowed transitions return exit status 2 with a message on stderr and empty stdout. The CLI reads the request without saving actions or echoing note contents.
