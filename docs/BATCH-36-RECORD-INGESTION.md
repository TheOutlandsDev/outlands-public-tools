# Offline Record Ingestion reference

This batch adds a fresh, neutral CSV/JSONL ingestion reference, its fictional
demo, tests, format and design notes. It is the first selected module of a
larger engineering example; forecasting and notification drafts remain private
and require separate review before publication.

The implementation accepts bounded text already supplied in memory, validates
an invented numeric-series contract, normalizes identifiers, orders records,
counts exact duplicates and flags conflicts. `require_clean()` blocks normal
downstream consumption when review issues remain. Review results retain valid
records; they are not anonymous and must be handled privately for real inputs.

No original application source bodies, business schema, query, formula, field
mapping, operational configuration, record or source history is included.
Only freshly authored generic code and invented examples are selected. The
module has no application file, network, environment discovery, process or
service adapter. No production integration or original application parity is
claimed. The MIT grant covers these original additions, not private inputs or
separately supplied runtimes.

Validation consists of 21 fictional tests, an actual CLI demo, independent
generated CSV/JSONL agreement checks, and exact selected-file privacy review.
The dedicated workflow runs on Windows/Ubuntu with Python 3.12/3.13 and refuses
test skips. See [validation boundaries](../tools/record-ingestion/VALIDATION.md),
[format](../tools/record-ingestion/FORMAT.md) and
[architecture decisions](../tools/record-ingestion/ARCHITECTURE.md).

Text scanning is evidence for selected bytes; it does not establish that
arbitrary data or unrelated private source is safe to release.
