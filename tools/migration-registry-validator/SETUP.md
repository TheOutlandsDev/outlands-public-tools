# Verify a fictional migration registry

Download the source ZIP and `SHA256SUMS.txt` from the release page.
Verify the ZIP before extracting. On Windows, compare the command output
to the ZIP digest in the checksum file.

```powershell
Get-FileHash -Algorithm SHA256 .\migration-registry-validator-0.1.0.zip
```

On Ubuntu, run the following command from the download directory.

```sh
sha256sum -c SHA256SUMS.txt --ignore-missing
```

Open a terminal at the extracted root. Use Python 3.12 or 3.15. The
validator runs with the standard library.

```text
python -B -c "from production_planning.migration_authority import load_migration_authority; report = load_migration_authority(); print(report.status, len(report.records)); print(report.source_fingerprint)"
```

The first line prints `SOURCE_AUTHORITY_NO_EXECUTION 26`. The second prints
the source fingerprint. If the inputs stay the same, the fingerprint stays
the same when you rerun the command on either platform.

The fixture has 17 PostgreSQL records and nine ClickHouse records. The
registry is at `data/platform/database_migration_registry_v1.json`. The
validator checks the listed files under `postgres/init` and
`database/migrations`, plus `database/create_tables.sql`. The fixture also
includes an explicitly excluded `database/load_test_data.sql`. The lexical
ledger tests use illustrative comments about a read-only grant and storage
engine. The SQL fixtures contain comments and simple read-only selections.

The validator reads the SQL as bytes and checks the recorded hashes. It
requires sorted, unique sequence values per database and rejects uncovered
files or a registry that authorizes execution. It performs no database
connections and executes no SQL. Use a trusted local registry. The
fingerprint documents the reviewed inputs and the registry labels do not
establish how a script behaves when executed.

To run the six tests, create a disposable virtual environment and install
the pinned test dependencies with the interpreter from that environment.

```text
python -m venv .venv
```

For the following commands, use `.\.venv\Scripts\python.exe` on Windows
or `.venv/bin/python` on Ubuntu in place of `python`.

```text
python -m pip install --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-test.txt
python -B -m pytest -q -p no:cacheprovider tests
```

`VALIDATION.json` records test runs and extracted-API checks for each
qualified platform and interpreter.
