# Policy and report format (version 1)

Policies are strict UTF-8 JSON objects, at most 1 MiB, maximum JSON depth 16.
Comments, trailing commas, duplicate/unknown fields and null values for supported
fields are rejected. Field names are case sensitive. Every numeric field is an
integer JSON token representable as Int64; strings, booleans and fractions fail.

| Field | Type | Default / rule |
| --- | --- | --- |
| `schemaVersion` | integer | Required; exactly 1. |
| `requiredMembers` | string array | Optional; files that must exist. |
| `forbiddenMembers` | string array | Optional; files that must not exist. |
| `allowedMembers` | string array | Omit to allow extras; present empty array denies every file. |
| `expectedSha256` | string | Optional; 64 hexadecimal digits; compared case-insensitively as hex. |
| `expectedSize` | integer | Optional; archive bytes, range 0..67,108,864. |
| `limits` | object | Optional; only the four keys below. |
| `textRules` | object array | Optional; at most 64 rules, unique file member per rule. |

Member arrays contain at most 4,096 unique exact strings each. Member strings are
1..1,024 UTF-16 code units, use `/` separators, never end in `/`, and obey the
portable safe-name restrictions in the README. A required name cannot be
forbidden or absent from a present allowed list. A forbidden name may appear in
the allowed list: the forbidden rule still rejects it.

Limits accept integers 1..their hard maximum:

| Key | Default and hard maximum |
| --- | ---: |
| `maxEntries` | 4,096 (includes directory records) |
| `maxTotalUncompressedBytes` | 268,435,456 (declared sizes) |
| `maxMemberBytes` | 67,108,864 (declared size for each entry) |
| `maxTextBytes` | 262,144 (declared and actual selected text bytes per entry) |

The non-configurable limits are archive 67,108,864 bytes, policy 1,048,576 bytes,
central directory 8,388,608 bytes, total selected actual text 1,048,576 bytes.
The byte snapshot prevents hashing one file while inspecting a later reopened
copy. It does not freeze a hostile Unix filesystem or verify unselected bodies.

Each text rule has `member` (required file name), and optional `containsAll` and
`containsNone` arrays. At least one marker is required. Total markers per rule
must be 1..256; each is 1..4,096 UTF-16 code units. Duplicates within an array and
identical markers in both arrays are rejected. Tabs, CR and LF are supported in
markers; NUL and other ASCII/C1 controls are rejected. Literal matching is ordinal
and case sensitive, across the entire bounded strict UTF-8 text. A UTF-8 BOM is
treated as a literal character, not removed. No normalization, regex, template,
shell interpolation or application-specific parsing occurs.

## JSON result

Completed results have `schemaVersion:1`, `tool:"zip-package-policy"`,
`status:"pass"` or `"findings"`, `archive` summary (`bytes`, lowercase `sha256`,
`entries`, `files`, `declaredUncompressedBytes`), `inspectedTextBytes`, `findings`
array, and a textual `coverage` statement. Each finding has `code` and, where
relevant, `member`. Hash and size findings precede membership findings; required
and forbidden checks follow policy order; unexpected files use ordinal order;
text findings follow policy/marker order. The report never includes body text,
literal marker values, absolute input paths or timestamps.

An incomplete result contains `schemaVersion`, `tool`, `status:"error"`, a short
`error` code and `coverage`. Generic parse, I/O and .NET errors become
`invalid_input`; more specific guard errors include `input_size_limit`,
`zip_metadata_limit`, `zip_member_size_limit`, `zip_text_size_limit`,
`zip_unsafe_member_name`, `zip_duplicate_or_portable_collision`,
`zip_file_directory_collision`, `zip_local_name_mismatch` and
`zip_multidisk_or_zip64_unsupported`. These are diagnostic categories, not a
promise of a complete forensic diagnosis. The process exit status is authoritative.

Reports are UTF-8 JSON with a final newline. `-ReportPath` creates exactly one new
file after completed checks using `CreateNew`; it never overwrites existing files
or creates missing parents. If writing fails, exit 2 replaces stdout with the
error record. As with ordinary file writes, an I/O failure after file creation
may leave a partial new output; review/delete that file before rerunning with a
new name. Existing input and output files are never deliberately modified.
