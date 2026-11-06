# Relational data and query-result review methodology

These tools review explicit schema declarations, typed rows and supplied results.
They do not connect to a database or execute SQL. Select the complete bounded
input scope before interpreting any result.

| Term | Plain-language meaning | Exact meaning here |
| --- | --- | --- |
| Schema | The declared structure of selected tables | Ordered table/column/key lists in a bounded generic format; supported types are integer, decimal, text and boolean. This is not a database dialect. |
| Primary key | Columns declared to identify a row | An ordered typed tuple of nonnullable columns. Every member of a duplicate group is flagged; physical duplicates are preserved. Empty key means no primary-key constraint. |
| Foreign key | Columns declared to refer to another table | An exact typed tuple matching the target table's complete ordered primary key. skip_any skips any tuple containing null; reject reports it. Column nullability applies separately. |
| Schema difference | A descriptive change needing interpretation | Valid additions/removals, type/nullability, ordered keys, references and list-order changes return REVIEW_REQUIRED with changes retained. A renamed object is removal/addition, not an inferred rename. |
| Physical row | One supplied record occurrence | Identical repeated rows retain multiplicity. Per-table input_rows = accepted_rows + rejected_rows; there is no silent deduplication. |
| Join key and null policy | The explicit equality-matching rule | Ordered compatible typed columns. never_match excludes any null tuple from matching but keeps unmatched rows; match explicitly allows equal null components. |
| Cardinality and fanout | How many rows a match produces | Each shared key with left/right frequencies l/r contributes l*r inner rows. Matching-row multiplicity is separate from declared key integrity. |
| Outer row counts | Matches plus records without a partner | Left/right outer = inner + that side's unmatched rows; full outer adds both unmatched sides. Counts are bounded supplied-row calculations, not database performance estimates. |
| Query and bindings | Selected query text and separate named values | Query text is opaque UTF-8; bindings are bounded scalar declarations. The checker does not parse SQL or verify placeholder correspondence. |
| Result contract | Caller-selected shape and completeness rules | Ordered column declarations, minimum/maximum returned physical rows, require_complete and exact input pins. Returned values are checked for type/nullability, not query semantics. |
| Truncation | A caller assertion that rows were omitted | require_complete=true plus truncated=true requires review. When false, a truncated result can PASS with declared_complete=false. An untrue completeness assertion cannot be detected. |
| Pin and receipt | A reproducible input binding and its report | Query pin hashes exact query UTF-8 bytes without added LF. Dataset/bindings pins hash raw supplied objects as sorted-key compact escaped ASCII JSON plus LF, preserving list order and decimal spellings. Schema pins hash validated schema declarations. These domains are not interchangeable or signatures. |
| PASS | The selected rules were met | Identical valid schemas; selected key integrity; exact join counting; or result shape/pins/policy consistency. None establishes actual database correctness, query output or authority. |
| REVIEW_REQUIRED | Findings need interpretation | CLI exit 1. Schema Diff retains valid descriptive changes; the other tools withhold the whole summary after row/pin/constraint findings. Counts and fixed diagnostics remain. |
| Fixed refusal | The requested scope cannot be assessed | CLI exit 2; malformed outer input/schema, missing table coverage, invalid policy or parser bounds refuse entirely. Library operations raise a fixed refusal. |
| Independent package | One tool can be installed and called alone | Its own wheel/version, CLI, fictional demo and actual compare/check/analyze Python operation. The collection pins four exact member versions. |

## Apply the method

1. Declare the selected schema and exact column order. Review differences before
   separately deciding compatibility, migration rules or database actions.
2. Check typed rows and declared keys. Missing constraints requires review; empty
   tables with constraints may pass only for that empty supplied scope. Rejected
   rows and duplicate target keys cannot become a qualified summary.
3. Count the proposed equality join under an explicit null policy. Duplicate keys
   intentionally affect cardinality; use the separate key checker for integrity.
   With left a,a,b,null and right a,a,a,c,null, never_match gives inner=6 and
   full_outer=10; explicit null matching gives inner=7 and full_outer=9.
4. Bind actual embedded query, dataset and binding inputs to both contract and
   supplied result. Review exact column order, types, row limits and truncation.
   A structurally valid unrelated result can PASS; values were not checked against
   SQL. Dataset pins preserve raw decimal spellings even though row/key comparisons
   normalize decimal trailing zeros and negative zero.

The [installed exercise](../integrations/relational-review/exercise.py) shares
one invented inventory snapshot across all four tools. It distinguishes a schema
change, duplicate-key integrity from join fanout, required versus allowed truncation,
false pins, and structural result PASS from actual query-output verification.
The [component guide](../integrations/relational-review/components.json) gives
people and AI callers exact imports, operation names, formats, examples and limits.

The source guides specify 1..8 tables, 1..16 columns per table, at most 1,000
physical dataset rows globally, strict typed values and parser/I/O bounds. Real
schemas, records, query text, bindings and reports stay private. Hashes, identifiers,
constraints and counts can disclose information even when row values are omitted.
These tools do not establish privacy, rights or publication approval.
