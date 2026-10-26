# Supported metadata and report format

This document defines the narrow implementation contract, not full Android image
validation. Integer fields are little-endian. Arithmetic uses Python integers;
declared payload lengths never cause payload allocations or reads.

## Recognition and header subset

The first eight bytes select `ANDROID!` boot or `VNDRBOOT` vendor_boot. An
unrecognized magic is a finding. A shorter magic/header is `HEADER_TRUNCATED`.
Boot versions are read at byte 40; vendor versions at byte 8. Versions other than
3 or 4 produce `HEADER_VERSION_UNSUPPORTED` coverage and no section layout.

| Kind | Version | Exact header bytes | Page bytes |
| --- | --- | --- | --- |
| boot | 3 | 1580 | 4096 |
| boot | 4 | 1584 | 4096 |
| vendor_boot | 3 | 2112 | supported declared vendor page size |
| vendor_boot | 4 | 2128 | supported declared vendor page size |

A declared smaller header is `HEADER_SIZE_INVALID`; a larger one is
`HEADER_SIZE_UNSUPPORTED` coverage. Neither is used to infer a component layout.
Boot's four reserved words are checked for nonzero bytes. Other header strings,
OS metadata, addresses and hardware-selection fields are not interpreted or
included. There is no `--include-details` option that exposes these strings.

A vendor page size of zero is invalid. Supported nonzero page sizes are powers
of two from 512 to 65536 inclusive; other values are coverage issues. The header
can occupy multiple pages. This is an intentionally bounded subset, not a claim
that every nonzero page size outside it violates an Android specification.

## Sections and alignment

Each section starts immediately after the previous section's padded end. The
first section is the header at offset zero. Padded length is the smallest
multiple of the relevant page size at least as large as declared length. A
zero-byte section consumes no pages. Zero-size components are allowed as
declarations; this inspector does not decide the artifact's role or bootability.

- Boot v3: header, kernel, ramdisk.
- Boot v4: header, kernel, ramdisk, boot signature.
- Vendor v3: header, vendor ramdisk, DTB.
- Vendor v4: header, vendor ramdisk, DTB, ramdisk table, bootconfig.

For each section `within_file` means that its declared data end is no later than
the file size. It does not include required padding and does not mean payload
inspection passed. `SECTION_OUTSIDE_FILE` identifies a declared data end outside
the file; `SECTION_PADDING_TRUNCATED` means data fits but its declared padded
layout does not. Padding contents are not read or checked. All bytes beyond the
derived padded layout are counted as `trailing_bytes` and produce
`TRAILING_BYTES_UNINSPECTED` coverage, even if they might be ordinary partition
padding or AVB data. No footer or tail format is inferred.

## Vendor v4 table subset

The declared table length must equal entry count multiplied by entry size.
More than 2048 entries is `TABLE_ENTRY_LIMIT` and makes inspection incomplete.
An inconsistent product is `TABLE_LENGTH_MISMATCH`. For nonempty tables only
108-byte entries are supported; another stride is coverage and entries are not
read. A truncated table is not read. An empty table with zero table bytes needs
no entry read; its declared stride is irrelevant.

Each supported entry contributes only numeric size, offset within the vendor
ramdisk section and type. Names and 16 board-ID words are omitted. Type values
0, 1, 2 and 3 are supported; another numeric type is reported as coverage without
making up a role. Fragment ends are checked against the declared vendor ramdisk
size. Positive-length in-range intervals are sorted for observed overlaps and
gaps. The final covered end is compared with that size. Out-of-range entries are
reported and excluded from this interval calculation. Zero-byte entries have no
interval; their offset still must not exceed section size. Gap/overlap findings
describe supplied offsets, not actual bootloader selection or decompression.
The table may be in any order; declared source order is retained in report rows.

## Schema version 1

`report.json` has these fields:

- `schema_version`, `tool`, `scope`, `status`, `image_bytes`, `image_kind`.
- `header_version` when a version could be read; `header_bytes` and `page_size`
  when a supported header could be read.
- `sections`: role, `offset_bytes`, `declared_bytes`, `padded_end_bytes` and
  `within_file`; empty if layout could not be interpreted.
- `declared_padded_layout_bytes` and `trailing_bytes` when layout was derived.
- `table_declared_entries` and `table_entry_bytes` for a readable vendor v4
  header. `ramdisk_table_inspected` is true only when a nonempty supported table
  was actually read; false also covers a supported empty table.
- `ramdisk_fragments`: 1-based index, offset, length, numeric type and
  `within_ramdisk_section`, without embedded strings or board IDs.
- `metadata_bytes_read` counts every read including repeated prefixes.
  `metadata_regions` holds labeled offsets, lengths and SHA-256 hashes for
  exactly the bytes read. These hashes can fingerprint sensitive header data.
- `whole_image_hashed`, `payloads_inspected` and
  `strings_and_hardware_identifiers_included` are always false.
- `findings` and `coverage_issues`: fixed `code`, region and nullable entry index.

Only a complete result with both arrays empty has `NO_SCOPE_FINDINGS`. Findings
or coverage produce `REVIEW_REQUIRED`; no pass for real device safety is implied.
Input/output/argument/resource errors emit a fixed-code `INCOMPLETE` JSON object
on stdout and exit 2. No complete report is emitted for a changed input detected
on descriptor close. Output-write errors can leave an incomplete fresh directory.

The report manifest hashes `report.json` and `report.html`; it is unsigned and
does not authenticate the source file. HTML is a static escaped presentation of
the same JSON. No input pathname or raw input text appears in either report.

## Resource and I/O contract

One regular file, greater than zero and at most 16 TiB, is selected explicitly.
At most 512 KiB are read cumulatively. Header reads overlap intentionally; the
largest supported table is 221184 bytes. Collections are limited to 4000 rows,
and each rendered JSON/HTML file to 8 MiB. File identity, size, timestamps and
descriptor metadata are checked before and after inspection. Inputs must remain
unchanged. No kernel, ramdisk, DTB, signature, bootconfig or padding payload is
read. No hashing of the entire image or proof of consistent unrelated bytes is
performed. The caller must control the input and output parent directories.
