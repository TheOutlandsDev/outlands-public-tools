# Report format — version 1

`report.json` declares `schema: outlands-offline-elf-dependencies/1` and a tool
version. Unknown future schemas should be reviewed before processing them.

- `status`: NO_SCOPE_FINDINGS or REVIEW_REQUIRED; this is a limited-scope finding,
  never a runtime/loader/security verdict.
- `interpretation`: concise fixed boundary statement.
- `limits`: requested file/entry/depth/time budgets.
- `summary`: inspected/ignored/parsed/visited counts, dependency status counts,
  detailed plus omitted issue count, metadata bytes and optional hash bytes read.
- `roots`: neutral ordinal labels without original absolute folder names.
- `entry_files`: unique graph starting IDs. With no selected files, all supported
  inspected ELF files are entries.
- `files`: sorted metadata rows. `id` is a relative label, `name` a basename.
  `class` is 32/64; `endian` little/big; `machine` is the numeric e_machine value.
  `machine_name` labels a small known set or unlisted. `osabi`, `abi_version`,
  `flags`, `type`, `bytes`, interpreter, SONAME, ordered declared NEEDED names,
  RPATH/RUNPATH and metadata kind are reported. `sha256` exists only when requested
  and completed. No code sections or binary contents are serialized.
- `dependencies`: sorted edges with consumer ID, declared name, finding,
  `candidate` (ID only for a unique metadata match), candidate count, displayed
  candidate IDs and omitted count. Counts describe the compatibility-filtered
  set when one exists, otherwise the same-name alternatives. At most 16 IDs are
  displayed. See README for resolution and compatibility limits.
- `issues`: relative location label and fixed public code. Native exception
  values, full source roots and binary contents are omitted. Additional issues
  above 500 are counted in `summary.issues_omitted`.

## Optional runtime hints (tool 1.1.0)

Without `--runtime-hints`, no hint fields are emitted and no string scan is
performed. The schema remains version 1 because these are additive opt-in fields.
Consumers requiring an exact legacy field set should leave that option disabled.

When enabled, a top-level `runtime_hints` object contains the fixed interpretation,
hard `limits`, successfully retained `files_scanned`, `bytes_scanned`, retained
`observations`, `observation_slots_used` and `files_with_partial_hint_coverage`.
Bytes/slots include bounded reads or observations subsequently discarded on a
source-change error; retained observations count only files present in the report.
The byte/slot budgets are not refunded for discarded files.

Each successfully parsed `files` row gains `runtime_hint_scan`:

- `coverage`: `complete_ascii_scan` or `partial_ascii_scan`. Complete means all
  bytes were considered under this limited ASCII token heuristic; it does not
  mean all runtime references were found.
- `bytes_scanned`, `file_bytes`: prefix size considered and observed input size.
- `reasons`: sorted zero or more fixed codes: `PER_FILE_BYTE_LIMIT`,
  `GLOBAL_BYTE_LIMIT`, `FILE_HINT_COUNT_LIMIT`, `GLOBAL_HINT_COUNT_LIMIT`,
  `STRING_LENGTH_LIMIT`.
- `overlong_ascii_runs_omitted`: observed complete printable runs over 1,024
  bytes; their contents are omitted. The last run at a byte-limit cut is also
  omitted, and is covered by the byte-limit reason.
- `observations`: sorted unique `(kind, text)` records containing `kind`, `text`,
  `first_offset` (zero-based input byte position) and `occurrences` in the scanned
  portion. Kinds are `library_text` and `config_or_firmware_path_text`. Repetition
  does not spend another unique-observation slot. Counts can be partial.

Library tokens end in `.so` with optional numeric dotted suffixes; selected path
tokens begin with one of the documented config/firmware prefixes. Tokens use the
limited ASCII characters documented in README. They contain no surrounding text.
The same bytes can appear both in declared metadata and in hint observations.
No relationship to actual dynamic loading is inferred.

Every partial scan adds an issue code `RUNTIME_HINT_` plus its reason. Ordinary
observations do not create coverage issues, dependency edges, candidates, missing
file findings or graph traversal. They do not affect exit 0/2 except through
explicit scan-coverage limits. Their embedded text remains private metadata.

Filename labels and embedded ELF strings are still private metadata. The IDs are
unique within one report, not stable database identities or cross-report file
identities. A selected file can retain its selected-N label when also discovered
under a root. Hard-link aliases are not content-deduplicated and can yield
ambiguous providers. Matching is case-sensitive and does not use root priority.

`MANIFEST.json` declares `outlands-elf-report-files/1` and hashes/sizes the exact
report.json, index.html and README.txt bytes. It does not hash itself or authenticate
the producer. It is distinct from the module's source-only SOURCE-MANIFEST.json.
