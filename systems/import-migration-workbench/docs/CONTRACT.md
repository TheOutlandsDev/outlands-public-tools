# Data and journal contracts

All request objects use exact fields. JSON duplicate keys, nonfinite numbers,
non-UTF-8 content and nesting beyond 64 levels are refused. Selectors use a portable
ASCII path subset inside `inbox/`, at most eight components and 240 characters.
Parent segments, empty components, Windows device names, stream syntax, backslashes,
trailing spaces/dots, links/reparse points and nonregular included files are refused.
Selected input, preview and store files must have a single filesystem link.

Contracts have exactly `format`, `key`, `unknown_fields`, `trim_strings`,
`empty_as_null`, `fields`. Format is `outlands-import-contract-v1`. Field names are
ASCII letters followed by letters, digits or underscores, at most 32 characters.
Source and target names each must be unique ignoring case, but row lookup is exact
and case sensitive. A mapping has exactly `source`, `target`, `type`, `nullable`.
The key names one nonnullable text or integer target field. Missing/null values are
accepted only for nullable mappings. Unknown fields are rejected, or ignored and
counted by name when that explicit policy is selected. There are no defaults.

`trim_strings` strips surrounding Unicode whitespace before conversion.
`empty_as_null` converts an empty string to null. Otherwise an empty nullable text
value is retained; nonnullable text must contain nonwhitespace characters.

Types:

- Text: a string of at most 256 UTF-8 bytes; control characters below space are
  refused except tab, CR and LF. Unicode normalization is not performed.
- Integer: a JSON integer or optional-minus decimal digit string without redundant
  leading zeroes, bounded to +/-999999999999999999. Boolean/floating values fail.
- Boolean: a JSON Boolean or exact lowercase `true`/`false` string. Numeric and
  other truthy values fail.
- Decimal: a string or JSON integer with optional minus, up to 18 whole digits and
  six fractional digits. No exponent, plus sign, locale separator or redundant
  leading zero. Floating JSON values fail. Output is an exact decimal string with
  trailing fractional zeroes removed and negative zero normalized to `0`.

CSV uses Python's strict Excel-dialect reader and UTF-8 with optional initial BOM.
Header names must be nonempty and unique ignoring case, at most 32 names of at most
128 UTF-8 bytes each. Quoted multiline cells are supported; source provenance records
their physical first/last lines. Width mismatches reject that data row. Invalid CSV
syntax/field-size overflow or invalid UTF-8 aborts the attempt. Header-only CSV is
a valid empty preview. CSV field size is capped at 65,536 characters before mapped
normalization; this is not a claim of complete RFC conformance.

JSONL uses LF-separated JSON objects. A final LF is not a row. Blank interior lines,
nonobjects, malformed JSON, duplicate keys and invalid mapped values are visible
row rejections. Each object has at most 32 keys; key names are at most 128 UTF-8
bytes. Rejected entries retain fixed codes and source line/hash references, without
the raw rejected value. Invalid file encoding and global limits abort the attempt.

The preview format is `outlands-import-preview-v1`. It records canonical contract,
sorted selected source metadata, accepted groups, rejected references, conflicting
variants, ignored-field counts and exact summary. The fingerprint hashes that
complete canonical body. The preview SHA separately pins its exact bytes. For every
successful analysis: input rows = unique accepted + duplicate extra rows + rejected
rows + all conflicting rows. Conflicting keys contribute zero accepted rows and
zero duplicate extras. All variants and provenance remain visible for review.

Import requires the registered preview ID and exact SHA, current journal head, actor,
reason, four exact true review Booleans and explicit rejection acceptance if needed.
Any conflict, empty accepted set or already completed exact fingerprint blocks the
request before filesystem writes. Inputs must still match every preview source pin;
analysis is replayed before and after store creation. The fixed SQLite tables use
bound values. Actual schema and every logical row are compared with the reviewed
preview before the final marker and again when inspecting an import.

The typed journal contains `job_started`, `job_completed`, `job_failed` and
`job_interrupted` events. Each canonical event envelope contains sequence and parent
SHA. Replay verifies the complete chain, event types, state transitions, request and
result fields, counts, pins and references; it performs no file operations. One
pending attempt blocks another. A terminal slot is reserved when starting a job.
SQLite append-only triggers block ordinary updates/deletes; hashes and schema checks
are additional integrity checks, not signatures or protection from a local attacker
who can rewrite the complete instance consistently.
