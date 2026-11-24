# Offline Account Preset and Workspace Preview

Preview the assignment and landing workspace for a named preset or custom account request using local JSON.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt, then extract the archive. Use Python 3.12.16 or 3.15.2. From the extracted directory on Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B account_preset_workspace.py examples/request.json
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B account_preset_workspace.py examples/request.json
~~~

The runtime uses hash-pinned Pydantic 2.14.3 and its pinned dependencies.

## Input and output

Supply a username and display_name for validation against the original request schema. Use fictional values to preview a configuration. The optional account_preset defaults to flex_operator. The other named presets are flex_ptl, flex_engineer, and flex_manager. For custom, supply custom_access_level as standard or power and an optional custom_functional_roles list. Named presets reject custom access or roles. The active flag defaults to true.

The result contains the preset name, normalized assignment, and primary workspace path. Among the available assignments, PTL or manager roles take precedence over the planning workspace roles, and other roles land in the operator work center. The example resolves to the standard operator assignment. Identity fields are omitted from the result.

The CLI previews what the saved request resolves to. The live application separately checks account creation permissions. Invalid input returns exit status 2 with empty standard output.
