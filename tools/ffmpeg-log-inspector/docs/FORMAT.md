# Supported log and report format — schema 1

The CLI reads one explicit ordinary local file. It decodes the bounded snapshot
as strict UTF-8 and removes at most one initial U+FEFF BOM. CR, LF and CRLF
separate segments. Whitespace-only segments are counted but not interpreted.
Tabs are accepted; C0/C1 controls other than tab/newline separators and Unicode
format characters are unsupported. ANSI escapes are not stripped or executed.

## Progress grammars

`Stderr` candidates start with optional whitespace followed by `frame`, optional
whitespace, and `=`. A supported record also has whitespace-separated `time=`.
Frame/time tokens end at whitespace. Frames are decimal digits, at most 13
digits and at most 1,000,000,000,000. Clock values use
`HH:MM:SS[.ffffff]`: hours have 2–6 digits, minutes/seconds 00–59, and fractions
have 1–6 decimal digits. Total time cannot exceed 1,000,000,000 seconds. Parsing
uses invariant culture. Signed clocks, decimal commas, NaN, exponent notation,
unsupported precision and overflows do not become values. Exact `N/A` means
unavailable. Zero remains an available numeric value.

Malformed recognized stderr records, including repeated `frame=` or `time=`
fields in one segment, are counted and discarded as whole records.
Other statistics and labels are not interpreted. A line with a wrapper prefix,
such as `[application] frame=...`, is outside this grammar and counted as ignored.

`Progress` candidates have an exact case-sensitive key of 1–64 ASCII letters,
digits or underscores followed by `=` and any bounded value. Leading whitespace
before the key is unsupported. Leading/trailing value whitespace is trimmed.
Blocks close on `progress=continue` or `progress=end`. Only `frame` and textual
`out_time` use the numeric grammar above. Unknown keys, including `out_time_ms`
and `out_time_us`, contribute only to counts; their names/values are not emitted
or converted. No unit assumptions are made for those numeric time keys.

Any duplicate key, unsupported known value/marker or non-key text inside an open
block invalidates that block. Its values are discarded rather than selecting
one ambiguous value. Unknown key duplicates also invalidate a block. The final
unclosed block is counted as unterminated and its values are not committed.
Empty marker-only blocks can close but provide no numeric progress evidence.

`Auto` chooses the structured grammar for standalone key/value segments. A
`frame=` segment with multiple non-whitespace value tokens is considered a
stderr candidate instead. Both formats can be observed in one input, but their
statistics stay separate and a mixed-format observation requires review. This
heuristic is not a universal classifier; choose an explicit mode for a known
supported log source. The tool never reconstructs individual FFmpeg runs.

## Output fields

| Field | Meaning |
| --- | --- |
| `schemaVersion`, `tool`, `requestedFormat` | Version 1, fixed tool identifier and selected parsing mode. |
| `status` | `observations` or `review` for a complete bounded parse; `error` on processing failure. |
| `input.bytes`, `input.sha256` | Exact snapshot size and lowercase SHA-256. No source path. |
| `coverage` | Segment/candidate/key counts, malformed/closed/invalid/unfinished blocks, duplicate keys, marker counts and last supported/unsupported marker category. |
| `stderrProgress`, `structuredProgress` | Separate numeric observation summaries for the two formats. |
| `signalSegments` | Number of nonempty segments matching each fixed phrase category. |
| `reviewReasons` | Ordered fixed reason codes; no raw input text. |
| `interpretation` | Fixed scope statement; not a media or device-health verdict. |

Each progress summary contains `records`, `numericFields`, frame/time observation
counts, unavailable counts, last available values, maxima and decrease counts.
If a later record says `N/A`, the last available numeric value remains and the
unavailable counter increments. Null means no available numeric value was seen.
Values are never added across records. A decrease is a comparison against the
preceding available observation in the same format, not a diagnosed cause.

Selected phrase categories use case-insensitive ordinal substring comparisons:
`inputOutputError` (`Input/output error`), `openError` (`Error opening`, `Could not
open`, `Failed to open`), `filterError` (`Could not run filter`, `Error reinitializing
filters`), `deviceLost` (both `device` and `lost` in one segment), `conversionFailed`
(`Conversion failed!`) and `decodeError` (`Error while decoding`). Each category
is counted at most once per segment, though categories can overlap. Quoted or
negated phrases may match; unsupported phrasings may not. These are literal text
signals, not independently verified FFmpeg errors, translations or root causes.

Review codes are `no_supported_numeric_progress`, `malformed_stderr_records`,
`invalid_structured_blocks`, `unterminated_structured_block`, `no_final_end_marker`,
`multiple_end_markers`, `mixed_progress_formats`, `counter_decrease_observed` and
`recognized_error_phrase`. Explicit stderr-only input has no required end marker
because its supported grammar has none. Structured data without a final `end`
marker requires review. Even an observed final `end` is not a process exit receipt.

## Processing failures and storage

Exit 2 produces a small error record with a fixed code and no source exception,
raw content or path. Invalid format/path, existing-link/path checks, size/line/key
bounds, changed reads, strict decoding, regex timeouts and output failures are
errors. Generic I/O/decoding failures use `input_or_output_error`; failures do
not masquerade as empty successful observations. PowerShell's own host/version
or parameter-binding errors happen outside the script's JSON error handler.

Hard limits: 16,777,216 input bytes; 100,000 segments; 16,384 UTF-16 characters
per segment; 128 distinct keys per block; 100 ms per fixed regex match; frame/
time numeric ceilings above. No caller-supplied regex is evaluated. Input
snapshots are immutable after reading. Source-length/mtime observations are
limited checks, not filesystem-race immunity.

An optional `-ReportPath` uses exclusive file creation and UTF-8 without BOM,
ending in one newline. The parent directory must exist. A write failure after
creation may leave the newly created file partial; it is never reported as a
complete report. Existing files, source logs and parent directory contents are
not replaced. No output directory is created by the inspector. The demo/test
helpers create their own explicitly requested new disposable directories.

Reports intentionally retain hashes and numerical characteristics. They may
still identify private work and require a separate review before publication.

[CLI instructions](../README.md) · [Source provenance](PROVENANCE.md)
