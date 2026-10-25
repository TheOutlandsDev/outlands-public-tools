# Declared copy-map format

Supported logical lines are `PRODUCT_COPY_FILES += WORD ...`. ASCII spaces/tabs
separate words. A single final backslash joins the next physical line; joined
text is capped at 8,192 characters. Blank/comment lines interrupt an unfinished
continuation and require review. A dangling final continuation requires review.
Text after `#` is a comment. Quoting and backslash escaping within the resulting
statement are unsupported, including escaped `#`. Other Make statements always
produce coverage issues: no Make evaluation or conditional branch selection.

Each word has two or three colon-separated fields: source, destination, optional
owner. Owner is 1–128 ASCII letters/digits/dot/underscore/hyphen. Paths are bounded
relative strings with forward slash components. Absolute, traversal, empty,
dot, backslash, colon, wildcard, control, Windows reserved-name and trailing
dot/space components are refused as review coverage. This deliberately portable
subset is narrower than all names Make/build hosts might accept. No path is read.

A root JSON must have exactly `schema_version` (integer 1) and `roots` (object):

```json
{"schema_version":1,"roots":{"LOCAL_PATH":"fictional","TARGET_COPY_OUT_VENDOR":"vendor"}}
```

At most 16 roots; names are uppercase ASCII identifiers up to 64 characters,
values are supported literal relative paths. JSON is at most 64 KiB, depth 8 and
1,000 nodes; duplicate keys, floating numbers and control-bearing strings fail.
Only a whole leading `$(NAME)` optionally followed by `/suffix` is substituted.
There are no implicit partition defaults, environment access or nested variables.
Unresolved expressions/paths remain entries with resolution `unresolved` and are
excluded from collision pairing. The roots file hash is recorded separately.

Fully resolved pairs are compared: same source/destination/owner is a duplicate;
same destination with a different source/owner is a declared conflict; equal
NFC-normalized casefolded destinations are portability collisions; prefix paths
at a slash boundary are file/parent conflicts. No file availability, filesystem
case policy, Make de-duplication, effective overrides or actual build is inferred.
All candidate pairs are bounded by the 4,000-entry/conflict collections; dense
conflict sets may reach a limit and fail rather than truncate.

Schema version 1: inputs, root_count, entries, conflicts, findings,
coverage_issues, status, details_included and optional roots_input. Entry IDs are
local to input order. Details opt-in adds raw fields and resolved paths.
