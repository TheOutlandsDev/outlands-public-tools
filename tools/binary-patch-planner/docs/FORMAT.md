# Plan and report contract

Schema version 1 is an original deliberately small exact-edit declaration.
It does not implement IPS/BPS/xdelta, ELF/PE rewriting, PAK rebuilding, DMBU
modification, format checksum repair, signatures or any game's asset semantics.

## Input plan

The root object has exactly `schema_version`, `source`, `patches`.

- `schema_version`: actual JSON integer `1`, not boolean/string/float.
- `source`: exactly `bytes` and `sha256`; bytes is an integer 1–4,194,304 and
  hash is exactly 64 lowercase hexadecimal characters.
- `patches`: 1–1,000 objects, each with exactly `offset`, `expected_hex` and
  `replacement_hex`. Offset is an actual integer from zero to declared size−1.
- Hex strings contain 2–8,192 contiguous hexadecimal characters, an even count,
  with uppercase/lowercase accepted. They decode to 1–4,096 bytes. Spaces,
  signs, prefixes, wildcards and empty replacements are unsupported.
- Expected and replacement lengths are equal and the complete edit must fit in
  the declared source length. Total declared edit bytes are at most 1,048,576.
- Sort edits by offset to test half-open ranges `[offset, offset+length)`.
  Adjacent ranges are valid; any overlap or repeated range is invalid. Edits
  remain in their original declaration order in the report. A no-op is valid.

The selected source must independently match both the declared size and full
SHA-256, and every expected byte slice must agree. A source mismatch generates
review findings and no candidate, including when all slices happen to match.
An out-of-bounds selected source caused by a wrong actual source size is a
review finding; an edit outside the plan's own declared size is invalid input.

UTF-8 with an optional initial BOM is accepted. Plans are at most 1 MiB;
JSON nesting is at most eight and nodes at most 40,000. Strings have at most
8,192 characters, keys at most 256. Extra/missing fields, duplicate JSON keys,
floats/NaN/Infinity, booleans used as integers and unsupported control text fail
with fixed codes. JSON whitespace can include normal structural LF/CRLF/tabs;
embedded hex-value whitespace is invalid. No comments, expansion or code occurs.

## Result schema

- `schema_version`, `tool`, `scope`, `status` identify the result and boundary.
- `sources` describes the selected `source` and `plan` byte counts/SHA-256.
  The binary source is hashed in full, unlike a metadata-only image inspector.
- `declared_source` contains the plan's expected byte count/hash.
- `patches` records declaration index, `offset_bytes`, `bytes`,
  `within_selected_source`, `expected_bytes_match` and `changes_bytes`.
- `declared_patch_bytes` counts the lengths of all edits, including no-ops.
- `candidate_sha256` is null unless every source/expected-byte check passes.
  Otherwise it describes the fully computed candidate byte string in memory.
- `application` always has requested/created/verified booleans. A verified new
  output adds `bytes`, `sha256`, and a fixed `receipt_scope` message. Its filename
  is omitted. Requested application remains withheld when there are findings.
- `findings` contains fixed codes plus an optional patch index. Codes include
  `SOURCE_HASH_MISMATCH`, `SOURCE_SIZE_MISMATCH`,
  `PATCH_OUTSIDE_SELECTED_SOURCE` and `EXPECTED_BYTES_MISMATCH`.
- `coverage_issues` is empty for this closed schema; unsupported declarations
  fail the run instead of being interpreted partially.

Private report JSON/HTML omit actual source/expected/replacement payloads and
local paths. Input and candidate hashes, offsets and layout are identifying
information; omission is not anonymization. The plan itself contains byte data.

## Output semantics

Preview creates only report files. An explicit `--apply-output` creates a
distinct new candidate path with an existing local parent. Input aliases and
existing candidate/report destinations are refused. The source cap is 4 MiB
both before and after application. Entire candidate bytes and SHA-256 are
compared after an exclusive create, write, flush and readback.

`MANIFEST.json` hashes the JSON/HTML reports only. The separately selected
candidate has its own size/SHA-256 verification receipt in `application`; its
path mapping belongs to the caller. These unsigned records are consistency
checks, not a signature, author identity, trusted origin, safe-edit certificate
or proof of intended runtime behavior.

A failure after candidate creation can leave a partial/complete new candidate.
A later report failure can leave a verified candidate without a complete report.
No automatic deletion, overwrite, rollback or source rewrite occurs. Use a new
destination after review. Trusted stable inputs and parent directories are
required; these checks are not an OS sandbox against a concurrent hostile writer.
