# OUTLANDS | Offline Record Ingestion

A small CSV/JSONL ingestion core for neutral numeric-series records. It
validates, normalizes, orders and checks duplicates using in-memory text.
Python 3.12+, standard library only, [MIT licensed](LICENSE).

This is fresh generic code and invented fixtures. No private application,
business schema, query, operational rule, source mapping or record is copied.
The record format is a neutral example contract, not an export of an existing
system. Forecasting, email delivery and operational adapters are separate work.

## Run the fictional example

From the collection root:

```text
python -B tools/record-ingestion/demo.py --demo
```

The summary identifies `FICTIONAL_INGESTION_DEMO`. Six records are accepted and
one identical duplicate is counted. An additional conflicting duplicate produces
`RECORD_CONFLICT`; the downstream gate refuses that review batch. CSV and JSONL
produce equal normalized records. No operator file, service, installed program
or environment inventory is read. No application output files are written.
No arguments or `--help` show static help. Use `-B` to avoid bytecode caches.

## Use the library

From this module directory:

```python
from ingestion import ingest_csv, ingest_jsonl

batch = ingest_csv("series,period,value\n SAMPLE ,0,2\nsample,1,4\n")
points = batch.require_clean()
assert points[0].series == "sample"

same = ingest_jsonl('{"series":"sample","period":0,"value":2}\n'
                    '{"series":"sample","period":1,"value":4}\n')
assert same.require_clean() == points
```

`Batch.records` contains accepted immutable `Point` values. `Batch.issues`
contains only record positions and fixed codes. `Batch.duplicates` counts
identical repeats. Valid rows are retained for review even when other rows fail;
call **`require_clean()` before downstream processing**. It refuses a batch
with any issue or no accepted records. It does not repair, silently select a
conflicting value or authorize ignoring rejected rows.

The library accepts text supplied by its caller, not paths, URLs, credentials
or connection strings. A private adapter can read an authorized source and map
its own fields into this contract. The module never discovers files, imports
selected data, executes input, opens a network connection or stores rejected
payloads. It is not a general file-I/O, ETL service or deployment system.

See [format and limits](FORMAT.md), [architecture and rationale](ARCHITECTURE.md),
[validation](VALIDATION.md) and [privacy boundaries](SECURITY.md). Keep real
inputs, accepted records, rejected payloads, diagnostics and exports private.
Validation is not anonymization or source-rights clearance.
