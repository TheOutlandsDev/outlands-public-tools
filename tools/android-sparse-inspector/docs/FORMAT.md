# Sparse metadata format and report contract

This is a deliberately bounded, original metadata inspector. Android's
[sparse-format header](https://android.googlesource.com/platform/system/core/+/refs/heads/main/libsparse/sparse_format.h)
documents the base format. This implementation has its own narrower acceptance
scope; it is not an AOSP `simg2img` replacement or a complete sparse-file library.
The inspection source never imports, invokes or bundles AOSP code/binaries.

## File header

Fields are decoded little-endian from the first 28 bytes. The 32-bit signature
must be `0xed26ff3a`. Major version must be 1 for chunk inspection. Minor version
0 has the understood base layout. Other minor versions generate coverage while
the known base fields are walked; this does not certify the extensions.

File-header size must be at least 28, chunk-header size at least 12. A file header
whose declared extent exceeds the file is truncated. Larger headers are skipped,
never parsed, and produce `FILE_HEADER_EXTENSION_UNINSPECTED` or
`CHUNK_HEADER_EXTENSION_UNINSPECTED`. Their extension contents are not hashed.

Block size must be positive and divisible by four. This inspector caps it at
1 MiB. Declared chunk count is capped at 4,000; declared output bytes and input
file size are capped at 16 TiB each. Python integer multiplication is exact.
`declared_output_bytes` is serialized as a decimal string so consumers need not
round a declared size. No expanded-image buffer is allocated.

A zero chunk count and zero output blocks can describe an empty layout. Other
zero-count combinations are checked through normal block accounting. A nonzero
file-header image-checksum declaration produces `IMAGE_CHECKSUM_UNVERIFIED`.
The checksum value itself is not included in the report.

## Chunk walk

The first chunk starts at the declared file-header size. Each chunk's base
12-byte header declares its type, reserved field, output block count and total
input size including the entire declared chunk header. Input offset advances by
that total size. The header must fit; total size must not be smaller than the
declared chunk-header size; the complete declared chunk extent must fit the file.
These failures stop the walk, avoiding invented subsequent boundaries.

The recognized payload-size rules are:

| Type | Declared payload bytes | Accumulated output blocks |
| --- | --- | --- |
| RAW (`0xcac1`) | `blocks * block_bytes` | `blocks` |
| FILL (`0xcac2`) | 4 | `blocks` |
| DONT_CARE (`0xcac3`) | 0 | `blocks` |
| CRC32 (`0xcac4`) | 4 | 0 |

Known-type size mismatches are findings. When the declared extent still fits,
the walk can continue at the next declared boundary; these are observations on
declared structure, not a corrected interpretation. Nonzero reserved chunk fields
are findings. Under the supported CRC convention, nonzero CRC output-block
declarations are flagged and never advance the accumulated output position.
Zero-length data chunks follow the same size/count equations; they are not
silently changed or expanded.

CRC32 chunks always produce `CRC32_UNVERIFIED`. Neither their stored CRC nor RAW
or FILL bodies are read. DONT_CARE ranges are counted without generating zeroes.
The inspector therefore cannot detect changed payload bytes when headers, file
length and ordinary file metadata are unchanged. A metadata pass never proves
payload integrity.

Unknown chunk types produce `CHUNK_TYPE_UNSUPPORTED` coverage and stop the walk.
The tool does not guess unknown types' output contribution. Consequently an
unknown/stopped walk does not invent a final output-count mismatch. When all
declared chunks have been walked, output blocks are compared with the file
header; trailing input bytes are flagged. Accumulated output beyond the header's
declared total is flagged as soon as observed.

## Report fields

`schema_version` is 1. The tool name, scope, image size, `whole_image_hashed: false`
and `payload_crc_checked: false` are always present. `header` is null if too short
or its signature does not match. A recognized header exposes version/sizes,
declared counts, decimal-string expanded bytes and the checksum-presence boolean.

`chunks` contains only the chunks whose base headers were read. Every row has a
1-based index, known name or `UNKNOWN`, four-digit hex type, declared input
offset/length, declared output blocks and accumulated output start block.
`findings` and `coverage_issues` contain fixed `code` and nullable `chunk_index`;
they never embed arbitrary input bytes. Counts are not a severity score.

`layout_walk_complete` is false until all declared chunks have been walked. It
can be true in a review-required report with known-type size mismatches, coverage
or trailing data. `observed_output_blocks` and `accounted_input_bytes` are present
only after the complete walk. Their absence means not determined, not zero.

`metadata_regions` records each base-header read with a fixed synthetic ID,
offset, byte count and SHA-256. Only the read bytes are covered. Payload and
extension ranges do not enter those hashes. `metadata_bytes_read` is the sum of
actual header bytes. These are private correlation metadata, not an input hash,
an authenticity proof or a reconstruction manifest.

Report files have the common source collection's static escaped HTML rendering
and unsigned report-file hash manifest. A fresh output directory with an
existing parent is mandatory; existing reports cannot be overwritten.
