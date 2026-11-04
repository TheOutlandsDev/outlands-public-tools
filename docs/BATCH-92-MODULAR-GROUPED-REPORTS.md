# Batch 92: grouped-report integrity sources

Four independent MIT source tools check caller-supplied grouped reports: definitions, exact contributor coverage, aggregate values, and scenario changes. Each tool has its own copy of the core and public MIT helpers. The examples are fictional HVAC records; the contract also supports game and AI/software records of the same typed shape.

Groups use one to four typed keys. Measures support row count, nonnull value count, exact sum, minimum, and maximum. Null numeric values do not contribute to those value measures. Sum/minimum/maximum of an all-null group are null. Rows, definitions, snapshots, and claims have explicit identities and pins. A missing, duplicate, or misplaced contributor blocks a qualified report.

These tools process supplied JSON only. They do not execute SQL, read a database, inspect a browser, verify source completeness, or update a target. Reports can expose supplied row IDs, keys, and numeric values. Keep reports made from private inputs private. The source tools are outside combined package releases.
