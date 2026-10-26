# Literal property snapshot grammar

Text is bounded UTF-8 with optional BOM, LF/CRLF, 1 MiB/file, 4 MiB/32 files total,
20,000 physical lines including final empty line, 8,192 characters per line.
Only blank/full-line # comments and literal key=value declarations are supported.
Keys are 1–128 ASCII letters/digits/underscore/dot/hyphen. Values may be empty;
split at the first equals sign and trim ASCII spaces/tabs around each field.
Do not strip inline #, unquote values, expand $, decode backslashes or join lines.

Import directives are never followed. Unsupported lines/keys/imports are
coverage with unidentified-row locations. No ro./ctl./persist semantics, Android
property validation/permissions, source/import precedence or actual overrides
are evaluated. This intentionally differs from an effective property service.

Build indexes across the explicitly supplied files on each side. Unique literal
keys match. Compare trimmed values exactly. Ordering/comment changes alone do
not change unique values. Renames produce removal/addition within the supported
scope. Duplicate keys on either side are held with all parsed record IDs, even
for equal values. No first/last winner is picked.

When the opposite side has unidentified rows/imports, unmatched identities are
held rather than claimed added/removed. Unique matched supported comparisons
remain visible alongside coverage. These are selected text observations, not
complete runtime changes. Empty snapshots are valid but prove no completeness.

Schema version 1: inputs, records, changes, held_identities, unidentified_rows,
comparison_counts/scope, findings, coverage_issues, status. Records carry opaque
IDs, side/source/line and supported flag. With --include-details they add
declared_identity and supported fields.value. Raw lines and local paths are
never copied. IDs are report-local and not persistent across edits.
