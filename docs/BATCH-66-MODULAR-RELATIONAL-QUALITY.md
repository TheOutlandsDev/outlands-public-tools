# Batch 66 - Independent relational data-quality tools

Four fresh generic MIT modules use explicit fictional schemas, tables and query
strings. Private original implementation/schema/query files were not consulted,
selected or executed. No user/customer records, business rules, private paths,
credentials, operational configuration or assets are included. Original files and
filenames remain untouched; original-family/whole-drive clearance stays incomplete.

| Independent tool | Scope | Evidence limit |
| --- | --- | --- |
| [Relational Schema Diff](../tools/relational-schema-diff/README.md) | Declared tables/columns/types/nullability/keys/references | No rename inference, DDL or compatibility guarantee |
| [Key & Reference Integrity Checker](../tools/key-reference-checker/README.md) | Typed physical rows, duplicate primary keys and explicit foreign/null rules | Supplied scope only; empty tables can pass vacuously |
| [Join Cardinality Analyzer](../tools/join-cardinality-analyzer/README.md) | Exact equality-key frequencies, duplicate fanout, unmatched/outer counts | No joined-row output, optimizer/runtime prediction or row-level key-constraint verdict |
| [Query Result Contract Checker](../tools/query-result-contract-checker/README.md) | Actual embedded pins, ordered result shape/types and declared truncation | No SQL execution, semantic bindings, actual result truth or completeness proof |

Every full directory runs independently with Python 3.12/3.13 standard library.
Native file guards are pinned existing public code. The relational subset is new;
it does not claim compatibility with every SQL/database type or artifact format.
Physical duplicates are preserved. Invalid rows/keys/pins withhold summaries;
Schema Diff intentionally retains valid differences for explicit review.

The dedicated Windows/Ubuntu matrix checks source pins, known results, required
native fixtures and actual standalone/four-tool CLI interoperability. The connected
cohort uses public intake on invented CSV; Python fixture logic selects a supplied
result. No SQL engine, live database or private original application runs.
Reports omit data/query/binding values but schema IDs, counts, relationships and
hashes remain private. PASS does not establish rights or authorize publication.

Combined packages/workbenches and release assets stay deferred until remaining
drive candidates and the user's additional list are reconciled. Existing systems
and frozen Toolkit 0.6.0 downloads/package plans remain unchanged.
