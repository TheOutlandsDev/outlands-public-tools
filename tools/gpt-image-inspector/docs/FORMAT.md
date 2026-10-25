# Image metadata format and limits

The selected input must be a complete regular local raw image, nonempty, at most
16 TiB, a multiple of the explicitly supplied 512/4096 sector size and at least
four sectors. Block/character devices and links are refused before opening.
There is no decompression, sparse Android format reader, embedded-offset scan,
filesystem parse or repair/write mode. A virtual sparse regular file is still
read through its bounded metadata ranges; no whole-file checksum is promised.

Read regions are 512 bytes for the MBR, one sector each at LBA 1 and final LBA,
and each supported array's declared count times 128 bytes. The total read budget
is 2 MiB. Entry count must be 1–4096; active-partition collections have the common
4,000-row bound. No declared pointer is followed before validating arithmetic,
image bounds and that role's reserved metadata placement.

Supported header revision is 0x00010000. Header size is 92..sector bytes. Header
CRC32 is computed over that size with its CRC field zeroed; table CRC32 covers
the declared entry array. Nonzero reserved/padding bytes, wrong own/alternate
header locations, zero disk GUID and insufficient array reservation are review
findings. Nonzero extended header bytes require coverage review. Entry sizes
other than 128 are unsupported, not treated as corrupt solely for being larger.

The primary array must lie at/after LBA 2 and before the first usable LBA. The
backup array must lie after the last usable LBA and before the final header.
Each side must reserve at least 16 KiB for its array. CRC failure is a finding;
bounded observations may still be shown, but never imply trustworthy metadata.
Malformed geometry skips that array; over-budget counts fail the run.

The protective MBR check observes its signature, count of type-0xEE entries,
starting LBA/declared size and hybrid entry types. It does not fully validate MBR
boot code, CHS fields or every UEFI rule. Partition checks cover start/end bounds,
overlap existence, zero/duplicate unique GUIDs, UTF-16LE name encoding, embedded
controls, nonzero name padding and nonzero unused entry data. Overlap reporting
gives observations sufficient to flag overlapping ranges, not every overlapping
pair. Attribute bits and partition-type meaning are not evaluated.

Primary/backup usable bounds, disk GUID, table geometry and exact entry bytes are
compared only when both arrays are inspectable. All findings remain independent
of that comparison. Full partition payloads are not read; SHA-256 fields identify
only listed metadata regions. Metadata agreement is not authenticity or a whole
image integrity check.

Schema version 1 includes headers/partitions, metadata_regions with offsets and
SHA-256, metadata_bytes_read, whole_image_hashed=false, findings, coverage_issues
and status. Findings use region and entry_index (null for non-entry findings),
not a fictitious text line number. Partition names/GUIDs are details opt-in.
