# OUTLANDS | Query Result Contract Checker

Check supplied result columns, types, actual embedded pins and declared truncation without SQL execution. Independent MIT CLI/library, Python 3.12/3.13 standard library only.
Fresh generic code and fictional tables; no private original implementation reused.

From the complete tool directory:

```text
python -B results.py --input examples/input.json
python -B results.py --input examples/needs-review.json
```

The second intentionally returns REVIEW_REQUIRED (exit 1). Optional
`--out ../fictional-new-report.json` needs an existing trusted external parent and
a destination that does not exist. No database connection is required or opened.

## Contract and interpretation

Library: `results.check(raw_json_bytes)`. Exact fields:
format (`outlands-query-result-contract-v1`), contract, result, query, dataset,
bindings. Contract contains columns, require_complete, min_rows, max_rows,
query_sha256/dataset_sha256/bindings_sha256. Columns use the shared column schema;
min/max are exact integers 0..1,000 with min<=max and require_complete is boolean.
Result contains ordered column-name list, rows, strict boolean truncated and the
same three pins. Result column names must be unique and match contract order.

Query is explicit nonempty text <=4,096 code points. It is opaque text: no SQL
syntax, placeholder/binding correspondence, statement permission or query semantics
are checked. Bindings is an object with <=32 symbolic keys and scalar values:
null, boolean, bounded integer or <=256-character text; no nested structures or
float coercion. No interpolation. Dataset uses the shared typed input contract.

Both contract and result pins must match actual embedded inputs: query UTF-8 bytes
without an added newline; raw supplied dataset and binding objects encoded as
sorted-key compact ASCII JSON plus LF. Dataset pins cover the supplied decimal
spellings/order, not normalized rows. Matching two false pin declarations cannot
pass. Any invalid dataset/result row, pin mismatch, column mismatch, returned-row
range violation or required-complete/truncated conflict withholds all summaries.
Dataset row diagnostics use dataset:TABLE; result/contract diagnostics use those
scope labels, so a dataset table named result remains distinguishable.

If require_complete=false, a declared truncated result can PASS shape/pin checks
while summary.declared_complete remains false. Min/max constrain returned physical
rows only, not unknown total rows. A false truncated flag cannot be independently
detected; completeness_authority_verified always stays false. A structurally valid
unrelated result or non-SQL query string may PASS if types/pins match. The tool
does not execute the query, verify returned values against it, establish actual
query/dataset provenance or prove source completeness. The example checks one
invented row. Query text, binding values, dataset rows and result values are omitted
from reports; hashes/counts/identifiers remain private. No database or target writes.

## Shared schema and supplied-row contract

Schema is exactly `{tables: [...]}`, with 1..8 unique table declarations. Each
table is `{name, columns, primary_key, foreign_keys}`. Names match
`[a-z][a-z0-9_-]{0,47}`. Columns (1..16, unique name) are exactly
`{name, type, nullable}` with strict boolean nullability and type integer, decimal,
text or boolean. These are a fresh generic subset, not a database dialect or
complete SQL type system. Real/float/date/binary/collation/default/expression
declarations are unsupported. Unknown fields refuse entirely.

Primary key is an ordered list of 0..4 unique existing nonnullable columns;
empty means no primary-key constraint. Foreign keys (0..16 per table, unique
constraint name) are exactly `{name, columns, table, references, null_policy}`.
Columns/references are ordered unique lists of 1..4 equal-length components.
References must exactly equal the target table's nonempty primary key, and paired
column types must match. Null policy is skip_any/reject. Source column nullability
still applies independently. Self/cyclic references are declarations only.

Dataset is exactly `{schema, tables}`. Each data table is `{name, rows}` and every
declared table must occur exactly once, including empty tables. Rows are arrays in
declared column order, matching its exact width. At most 1,000 physical rows
globally (and per table); the result checker additionally accepts at most 1,000
result rows. Malformed outer/schema/table coverage or bounds refuse entirely.
Malformed data rows receive fixed 1-based row diagnostics and counts; rejected
values are omitted. Per-table input_rows = accepted_rows + rejected_rows. Every
accepted physical row, including identical duplicates, is preserved. No latest
selection, deduplication, guessed mapping or silent truncation.

Integer is a strict JSON integer in +/-10^12; boolean is strictly true/false.
Decimal is a base-10 string with <=6 fractional places and absolute value <=10^12;
no exponent, whitespace, leading plus, ambiguous leading zeros or float coercion.
Trailing fractional zeros and negative zero normalize for key/row comparisons.
Text is <=256 Unicode code points, allows tab/CR/LF, refuses other C0/C1/DEL
controls and preserves Unicode without normalization. Empty text is valid.
Null is accepted only for nullable columns. Typed tuple encoding distinguishes
booleans, integers, decimal/text values; join/reference types must also match.

Schema Diff intentionally retains valid differences with REVIEW_REQUIRED.
The other tools withhold their whole summary after any row/pin/constraint issue;
counts and fixed diagnostics remain. PASS describes only the explicit supported
scope. No source/store authenticity, privacy, rights, useful dataset coverage,
SQL semantics or actual database correctness is established.

## CLI, file safety and privacy

One explicit JSON input <=4 MiB; no source-system, directory, include, URI,
environment expansion, network, clock, SQL execution, process launch or model.
JSON refuses duplicate keys, floats/nonfinite values, invalid Unicode, strings
>4,096, depth >32, >100,000 nodes and integers outside +/-10^18. Output is escaped
ASCII JSON <=8 MiB. Input SHA-256 covers exact raw JSON; other pins have their
explicit encoding scopes above. Hashes do not authenticate or anonymize data.

The CLI uses pinned public [Windows/POSIX file guards](IO-SAFETY.md), ordinary
single-link inputs and trusted, quiescent parents. No hostile filesystem/process
sandbox. Default output is private stdout JSON. Optional --out exclusively creates
a new external report beneath an existing parent outside the source tree; no
replacement or mkdir. Failed writes can retain partial/unconfirmed output; inspect
privately and select a fresh path. Windows inherits parent ACLs with no confidentiality
guarantee. Shell redirection lacks --out guards. Exit 0 PASS, 1 REVIEW_REQUIRED,
2 fixed refusal, 130 interruption; supplied paths/values are omitted from errors.

Reports omit row values, join keys, query/binding bodies, but schema names, counts,
relationships, findings and hashes may remain private. Keep actual inputs/reports
private. Structure, pins and an audit do not establish publication rights.
See [origins](ORIGINS.md) and [validation limits](VALIDATION.md).

```text
python -B source_check.py
python -B -W error -m unittest discover -s tests -v
```
