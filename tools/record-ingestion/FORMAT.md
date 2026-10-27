# In-memory contracts and limits

The initial record shape has exactly `series`, `period`, `value`. It is a
neutral numeric-series example, not a private application's schema.

| Field | Contract |
| --- | --- |
| `series` | ASCII text, trimmed/lowercased at ingestion, then `[a-z][a-z0-9_-]{0,31}` |
| `period` | JSON integer, never boolean, 0 through 1,000,000; ordinal index without an implicit date, calendar or time zone |
| `value` | JSON integer/float, never boolean/string; finite and between -1,000,000,000 and 1,000,000,000; normalized to float with positive zero |

CSV requires the exact header order `series,period,value`. Period cells accept
one to seven decimal digits after trimming; leading zeros normalize to an
integer. Value cells use explicit finite float conversion. Wrong cell counts
create review issues. Wrong headers or malformed CSV refuse the whole input.
Quoted CSV multiline fields are parsed as records, then validated by the same
neutral domain rules; a newline in a series token remains invalid.

JSONL uses LF-separated JSON values with one optional trailing LF. CRLF JSON
whitespace is accepted. Blank records, duplicate keys, nonstandard constants,
malformed/deep JSON and wrong shapes/types create fixed review issues. Unknown
fields are not retained. An initial Unicode BOM is supported for either format;
midstream BOMs are not silently removed. NUL and invalid Unicode text are refused.

Maximum UTF-8 input bytes: 65,536 including an initial BOM. Maximum data records:
256, including duplicates/rejections. Maximum accepted series: 32. Byte/record
limits refuse the whole operation. Series-count and row failures create issues.
CSV positions count records plus the header, not physical multiline source
lines; JSONL positions count records. Empty input is not clean.

Accepted records sort by canonical `(series, period)`. An identical duplicate
increments the duplicate count. A conflicting duplicate produces
`RECORD_CONFLICT` and retains the first accepted record for review. No existing
record is silently replaced. `Batch.ok` is true only with records and no issues;
`require_clean()` otherwise raises `BATCH_REVIEW_REQUIRED`.

`Point`, `Issue` and `Batch` are frozen data classes. Public `Point` construction
requires an already canonical series token and validates its numeric fields.
`Issue` has only `record` and `code`. Accepted values remain data, not redacted
output. There is no automatic business-field mapping, missing-value imputation,
unit inference, business calendar, quarantine file, persistence or destination.

These limits bound the documented text parsers. They are not process memory/CPU
quotas, hostile Python-object isolation or a production throughput guarantee.
