# Validation

All fixtures are invented records and text. No historical corpus, private
application code, business formula/query, production source or operational
record is read, copied or executed.

The 21 standard-library methods cover format agreement, normalization/order,
duplicate/conflict decisions, unknown/duplicate fields, finite/type/identifier/
period rules, BOM, malformed/deep input, byte/record/series caps, multiline CSV
positions, frozen values, clean-batch refusal, payload execution canaries,
deterministic demonstration, actual CLI behavior, fixed errors and source/output
preservation. The suite has no platform-specific skips.

Run from the collection root:

```text
python -B -W error -m unittest discover -s tools/record-ingestion/tests -v
python -B tools/record-ingestion/demo.py --demo
```

Windows/Ubuntu Python 3.12/3.13 CI runs the same suite and demo with bytecode
disabled, then validates collection documentation. Exact-commit evidence and
the publication file list are reviewed before merge. Generated fixtures, logs
and comparison reports stay outside publication.

The tests establish the documented bounded parser and review behavior. They
do not validate a real ingestion source, arbitrary business schema, private
adapter, database transaction, production load, forecast model, email service,
source rights or complete privacy clearance. Each real integration needs its
own authorized data, private configuration and validation.
