# Offline Operator Action ID Generator

Generate the action ID used by the authoritative operator work center from saved order and work-in-progress (WIP) snapshot hashes and action fields. The CLI reads local JSON and writes a report to standard output.

## Install and run

Compare the ZIP SHA-256 with SHA256SUMS.txt. Use Get-FileHash -Algorithm SHA256 in Windows PowerShell or sha256sum -c SHA256SUMS.txt on Ubuntu. Extract the ZIP and open its top-level directory.

Use Python 3.12.16 or 3.15.2. In Windows PowerShell run the following commands.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.\.venv\Scripts\python.exe -I -B operator_action_id.py examples/actions.json --product DEMO-PART-A
~~~

On Ubuntu run the following commands.

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements-runtime.txt
.venv/bin/python -I -B operator_action_id.py examples/actions.json --product DEMO-PART-A
~~~

The requirements pin Pydantic 2.14.3 and the runtime wheels qualified on Windows and Ubuntu x64.

## Input and output

Pass a JSON object with an actions array. Each action supplies source_revision_sha256, wip_source_sha256, part_number, order_id, lot_id, kanban, and operation. Use lowercase SHA-256 hex for source hashes and a Kanban integer from 1 to 6. Text and identifiers are hashed as supplied, including case and whitespace.

The output preserves the selected rows in input order and adds action_id to each row. Filtering by an exact part number or reordering rows leaves each action's ID unchanged. Changing an identity field changes the hash. The supplied source hashes are identity inputs. Verify the underlying snapshot files separately if you need evidence of their contents.

Invalid batches exit with status 2 and empty standard output. The tool reads the batch without saving actions. The examples contain fictional actions and snapshot hashes.
