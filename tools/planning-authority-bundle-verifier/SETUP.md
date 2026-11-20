# Verify a saved planning authority bundle

Use 64-bit CPython 3.12.16 or 3.15.2 on Windows or Ubuntu. Verify the source ZIP against SHA256SUMS.txt, extract it, and open a terminal in the extracted directory. The runtime lock pins Pydantic 2.14.3 and its dependencies.

## Windows PowerShell

~~~powershell
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
& $py examples/make_bundle.py demo
& $py planning_bundle.py demo
~~~

## Ubuntu

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-runtime.txt
.venv/bin/python examples/make_bundle.py demo
.venv/bin/python planning_bundle.py demo
~~~

The generator requires a new directory. The demo verifies 11 fictional artifacts and prints both fingerprints. The inputs remain unchanged. Failed validation returns status 2 and a diagnostic on stderr.

## Verify a bundle from saved records

Use the demo directory structure as a template. The artifacts directory holds the 11 source files. The semantic-inputs.json file holds the source fingerprint and the saved runtime status plus normalized planning, part mapping, WIP, and Kanban settings. Export those settings from a trusted source. The verifier consumes the saved normalized settings, checks the declared policy mode and development safety fields, and verifies the active policy file hash. It does not load or activate the planning runtime.

The source fingerprint covers the sorted map of artifact names and byte hashes. The semantic fingerprint adds the saved runtime status and normalized settings using the original canonical JSON field layout. JSON key order in the semantic snapshot does not affect the result. Changing an artifact changes the source fingerprint, and a stale semantic snapshot is rejected. Every artifact must be present under the provided root.

The default mode is authoritative_gate_a. For legacy snapshots, use --mode legacy. The example generator also accepts --mode legacy to generate a matching fictional snapshot.

Add --authority-summary to emit the planning.json report used by the Planning Program Authority Verifier. Update that verifier's trusted index with the report's SHA-256 and matching planning_authority state.

For the four adapted tests, install the hash-pinned test requirements into the same environment and run python -m pytest -q from the extracted directory. The release records include six packaged CLI checks across all four Windows and Ubuntu profiles.
