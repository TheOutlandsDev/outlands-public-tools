# Source provenance

The selected first-party source consists of 14 original Python modules, two SQL
migrations, and five original test modules containing 22 tests. All application
modules and migrations retain their original byte content except for neutral
database and profile labels in `program_data/mes_policy.py`. The SQLite schema,
CLI, ingestion and static validation logic are preserved.

The SQL export test uses fictional server and database labels. The policy tests
use fictional table, database and reporting labels. The candidate test uses a
fictional SQL and contract pair with the same expected rejection reasons and a
hash pinned to its fictional SQL. The source project’s operational query, data
and evidence files are excluded. All four ingestion fixtures were written for
this release. The tests still exercise the same original conditions and
assertions. The candidate test retains a distinct negative baseline.

The source manifest, build and qualification tools, and release documentation
support the public source distribution. The included Python lock identifies
the interpreters used for qualification. The ZIP contains text source and
fictional examples.
