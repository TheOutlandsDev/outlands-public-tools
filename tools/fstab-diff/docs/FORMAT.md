# Fstab parsing and comparison

Mode is required. Fields split on ASCII space/tab before escape decoding. Blank
lines and full-line `#` comments are ignored. A separate field starting `#`
begins a trailing comment; embedded `#` remains data. Supported escapes are
`\040` (space), `\011` (tab), `\134` (backslash), decoded once. Other/malformed
escapes require coverage review. Quotes have no shell quoting meaning and remain
ordinary field text; a quoted literal space still separates fields.

| Mode | Supported fields |
| --- | --- |
| linux | source, target, fstype, options, optional dump, optional pass_number |
| android | source, target, fstype, options, fs_mgr_flags (exactly five) |

Linux dump/pass are decimal nonnegative values 0–65535 with at most 5 digits;
omitted values are zero. Options and Android fs_mgr flags are ordered comma text,
not evaluated sets. Empty/duplicate option tokens are findings. Equivalent
runtime semantics, flag overrides, labels, UUID lookup and filesystem existence
are not inferred. This subset does not support all platform-specific fstab
extensions; malformed rows remain coverage issues, never silently equal.

Match exact decoded mount targets only when unique on both sides. A target
duplicated on either side is an ambiguous group: its rows are shown, but never
arbitrarily paired as changed/added/removed. Unique unmatched targets are
added/removed; unique matches list fields_changed. Whitespace/comments and
numeric leading zeroes do not constitute a value change; option order does.

`relative_order_changed` compares only the sequence of unique common supported
targets. Adding or removing other rows does not imply reorder. Unsupported or
ambiguous rows are excluded, and `order_scope` states that limitation.

Schema version 1: format, inputs, parsed_counts, records, changes,
ambiguous_targets, relative_order_changed, order_scope, findings,
coverage_issues, details_included, status. Default target IDs are opaque and
assigned in first-seen order across before/after; they are not persistent IDs.
Details opt-in adds decoded private fields and before/after values.
