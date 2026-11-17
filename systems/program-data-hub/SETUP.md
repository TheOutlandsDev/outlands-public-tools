# Set up and run Program Data Hub

Download the source ZIP and compare its SHA-256 with `SHA256SUMS.txt` before
extracting it. On Windows, use `Get-FileHash .\program-data-hub-0.1.0.zip`.
On Ubuntu, use `sha256sum program-data-hub-0.1.0.zip`. Open a terminal in the
extracted directory. Use a Python 3.12 or 3.15 interpreter with SQLite FTS5.
The application uses the standard library, so there are no packages to install.

Use `py -3.15` or `py -3.12` on Windows if that is how you select Python.
On Ubuntu, use the installed `python3.15` or `python3.12` in place of `python`.
These examples write a new local database under `data/`.

```text
python -B -m program_data --database data/demo.sqlite3 init-db
python -B -m program_data --database data/demo.sqlite3 ingest-document tests/fixtures/sample_document.md
python -B -m program_data --database data/demo.sqlite3 search-documents calibration
python -B -m program_data --database data/demo.sqlite3 ingest-dataset tests/fixtures/sample_dataset.csv --key-column id
python -B -m program_data --database data/demo.sqlite3 ingest-sql-export tests/fixtures/sample_sql_export.jsonl --query-key demo-orders --query-file tests/fixtures/sample_query.sql --record-key-column order_id
python -B -m program_data --database data/demo.sqlite3 record-metric --metric-key demo-count --value 12 --value-kind numeric
python -B -m program_data --database data/demo.sqlite3 status
python -B -m program_data --database data/demo.sqlite3 backup --destination data/demo-backup.sqlite3
```

The search highlights `calibration`. The dataset and SQL export each contribute
two rows. Status shows SQLite integrity and foreign-key checks. The backup command
requires a new destination. Backups contain the source database's imported data.

SQLite paths passed to `--database` resolve relative to the extracted application
directory. Relative backup destinations resolve from the current directory.
Use absolute paths for both when working from another directory.

The following fictional candidate is rejected with exit 2. It lacks the evidence
required for the original static contract rules. The validator reads local text.

```text
python -B -m program_data validate-query-contract query_contracts/demo-movement.query-contract.json
```

Use trusted local inputs. The contract validator may read an input file while
reporting that its path falls outside the configured project directory. Static
contract results cannot establish permission to execute SQL on a real system.
Document text indexing covers the supported text formats. Binary documents are
cataloged with their file metadata and checksum.

`VALIDATION.json` lists the archive checksum, pinned interpreters, all 22 unit
test results per profile, and the workflows checked through the copied CLI. The
jobs extracted the ZIP and created fresh virtual environments without pip.
