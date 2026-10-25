# Supported format and report contract

## Project subset

The selected `.vpd` must be strict UTF-8 JSON with an object root containing:

- `projinfo`, an object with string `projectfile`;
- `timeline`, an object with list `subitems`;
- `videolist`, `audiolist`, `imagelist` and `subtitlelist`, each an object with
  list `subitems`.

These positions reflect observed owner-held VPD JSON structures, not a vendor
published schema. Observed nonempty references were video-bin paths; the same
documented structural list/path shape for other bins is covered by authored
fixtures. It has not been validated against every editor version or bin type.
No field is evaluated, imported, deserialized as native objects, or decoded as
an embedded blob. Unknown fields are retained only while parsing and are not
copied wholesale into reports. Numeric fields unrelated to counting are not
interpreted as timings, trims, speed curves or effects.

Known direct `/BIN/subitems/INDEX/path` strings receive `BIN_path` roles, where
BIN is one of the four listed media bins. This means a media-bin path candidate,
not verified media usage. `/projinfo/projectfile` receives `project_record_path`.
Other string-valued keys named `path` receive `unclassified_path`: they may be
output, cache, auxiliary or unsupported reference fields. Their semantics are
not guessed. Unknown keys named `projectfile` outside `projinfo` are not part of
this subset. Missing/nonstring direct bin paths and unknown path fields become
explicit coverage issues.

`timeline_track_entries` is the number of direct timeline `subitems` entries.
`timeline_block_entries` sums direct `subitems` lengths in entries whose list
shape is supported. An unrecognized entry records `UNCOUNTED_TIMELINE_ENTRY`;
the sum then covers only the recognized entries. These are structure counts,
not a claim that all entries are playable clips or tracks.

References are sorted by full JSON pointer before receiving `ref-000001` style
IDs. Known schema locations are reported by default. Unclassified pointer text
is replaced by `outside_supported_bin_structure`, because user-defined keys
can contain identifying text. `--include-path-text` adds `embedded_path_text`
and full `json_pointer` fields. IDs are bound to an exact project SHA-256 in a
mapping; editing/reordering references can change IDs.

`path_kind` describes text only: `empty`, `windows_absolute`, `posix_absolute`,
`network_or_device_text`, `scheme_or_device_text`, `portable_relative`, or
`unsupported_relative_text`. No embedded path is resolved or followed.

## Explicit mapping

Mapping JSON has exactly `schemaVersion` (integer 1, never boolean),
`projectSha256` (64 hexadecimal characters matching the project's exact bytes)
and `files` (list). Every entry has exactly string `referenceId` and
`relativePath`. Unknown/duplicate fields, stale hashes, unknown/repeated IDs,
and project-record/unclassified roles fail before any mapped file observation.

Relative paths use `/`, have no empty/`.`/`..` components, drive/scheme/colon,
backslash, control/format characters, Windows reserved names or
`<>"|?*` characters, and no trailing dots/spaces. Each component has at most
255 characters, the path at most 4096 characters and at most 64 components.
Casefold/NFC collisions between different spellings are rejected conservatively
for portable mapping. Exact repeated target paths for different reference IDs
are allowed as an explicit assertion. Shared `mapped_copy_id` fields and
`mapping_summary` counts expose reuse; they are not independent media copies.

Both `--mapping` and `--media-root` are required together. The root is an
explicit existing local directory, not a filesystem root. Only joined validated
relative mapping components are checked with `lstat`; code does not call
`resolve` to follow components. Symlinks/junctions/reparse points stop a check.
No media file descriptor is opened, content read, hash calculated or extension
used as proof of content type. User-supplied mappings can point at the wrong
copy; correspondence is not verified.

Each mapped reference has `metadata_check_attempted: true`, including attempts
stopped before reaching a leaf. `availability` distinguishes:

| Value | Observation |
| --- | --- |
| `uninspected` | No mapping selected this reference. |
| `present_regular_file` | The mapped leaf was observed as a regular file. |
| `missing` | A required selected component was not found. |
| `linked_path_rejected` | A component was linked/reparse metadata. |
| `non_directory_component` | A non-leaf component was not a directory. |
| `not_regular_file` | The leaf was not a regular file. |
| `metadata_unavailable` | A metadata operation failed for another reason. |

Every reference retains `media_content_read: false` and `rights_verified: false`.
`metadata_check_attempt_count` counts attempts, not successfully opened files.
`unmapped_media_reference_count` excludes the project-record and unclassified
roles. Mapped metadata checks are sequential observations under trusted,
quiescent parents; they are not a hostile-filesystem sandbox or atomic snapshot.

## Fixed bounds and strict parsing

| Bound | Ceiling |
| --- | ---: |
| Project bytes | 8 MiB |
| Mapping bytes | 1 MiB |
| JSON container nesting | 32 |
| JSON values visited | 100,000 |
| JSON key length | 256 characters; control/format characters rejected |
| JSON string length | 65,536 characters; lone surrogate codepoints rejected |
| Number token length | 128 characters |
| Decimal exponent magnitude | 4096 |
| References / mapping entries | 5,000 |
| Each generated JSON/HTML report | 16 MiB |

Nesting is checked lexically before the recursive decoder. Duplicate JSON keys,
NaN/Infinity, invalid UTF-8/JSON, oversized structures and limits fail. Decimal
tokens are kept as exact `Decimal` objects during structural traversal, avoiding
float overflow/underflow; they are not emitted or interpreted as project timings.
Regular input files are read through bounded descriptors with identity/length/
mtime observations before/after. Changes observed during reading fail. Some
same-size, timestamp-restored or concurrent replacement races cannot be excluded
on every filesystem; stop producers and use trusted private copies.

## Outputs and exits

The required fresh output directory contains `report.json`, static escaped
`report.html`, and `MANIFEST.json`. The manifest covers the first two files by
relative name, byte length and SHA-256; it cannot include its own hash. Hashes
are not signatures. Output inside the explicitly checked media root is refused.
Existing output paths are refused; parents must exist and be free of links.
Exclusive writes never replace an existing report. I/O failure can leave a new
partial directory, and no completed set is claimed then.

Exit 0 / `INVENTORY_ONLY` means supported structural inventory only, with no
mapping. Exit 0 / `NO_MAPPING_FINDINGS` requires no coverage issue and all
supported media-bin references mapped to observed regular leaves. Empty media
bins can produce a vacuous no-findings mapping result with zero attempts; it
still proves no playback or archive completeness. Exit 1 / `REVIEW_REQUIRED`
indicates coverage issues, unmapped candidates, or non-present mapped states.
Exit 2 / `INCOMPLETE` is a stable input/coverage/I/O error, with a safe code on
stdout and no success claim. It can occur after creating new partial outputs.

Default reports omit embedded path text, titles, unknown pointer text and local
input/root names. Hashes, sizes, structural positions and counts remain private
metadata. Opting into path text intentionally expands report sensitivity.
Reports do not establish permissions, ownership, safe content, full editor
compatibility, renders, a complete archive, or a successful migration.
