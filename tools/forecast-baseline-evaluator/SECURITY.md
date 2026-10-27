# Privacy and execution boundary

Only fresh generic code, the public MIT ingestion snapshot, invented fixtures
and authored documentation are included. Original forecasting implementation,
business rules, formulas, queries, source mappings, records, credentials,
endpoints, deployment configuration and model assets remain private.

The evaluator has no file, network, process, environment-discovery or service
adapter. The demo accepts only `--demo` and static help; it reads no operator
file, stdin or connection setting. Python loads its own trusted source modules;
source import is not a sandbox for untrusted Python code. Use `-B` to prevent
interpreter caches. The application creates no output files.

Real input, normalized points, forecasts, scores and diagnostic positions/counts
can disclose operations. Keep them private even when they satisfy this neutral
contract. Fixed error codes do not make accepted records anonymous. No record
selection, import/export or downstream message is authorized by a passing score.

Bounds and typed checks are not hostile Python-object isolation, resource quotas,
source-rights clearance or proof that a private integration is safe. Frozen
classes do not prevent deliberate mutation by application code. The clean gate
does not authenticate the provenance of a manually constructed batch.

Publish issue reports with minimal invented examples. Do not attach real data,
forecasts, source schemas, business rules, credentials, private paths or logs.
Each future provider, model or notification integration needs separate review.
