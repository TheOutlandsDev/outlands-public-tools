# Provenance and MIT scope

The local owner-authored `inspect_vendor_boot_offline.sh` helper used external
Android build tools to unpack a fixed vendor image and examine its extracted
files. This publication retains the generic need to inspect image structure in
a fresh reusable metadata-only implementation. It includes none of that
helper's device paths, firmware, extraction recipe, external binaries or
vendor-specific content. The original is unchanged and fingerprinted in the
private review record.

The parser, generated fixtures, tests and documentation are original code.
`binary_reader.py` derives its bounded regular-file descriptor design from the
collection's original MIT GPT inspector; `inspection_support.py` and its tests
reuse first-party MIT collection safeguards. No AOSP implementation, header
source, third-party parser or native executable is copied or bundled. Format
facts were consulted to write independent Python field reads and arithmetic.
The selected-source review is not independent proof of every historical file's
exclusive authorship.

Primary format references checked on 2026-10-26:

- [Android boot header documentation](https://source.android.com/docs/core/architecture/bootloader/boot-image-header)
- [Vendor boot structure and table documentation](https://source.android.com/docs/core/architecture/partitions/vendor-boot-partitions)
- [AOSP bootimg format declarations](https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/heads/main/include/bootimg/bootimg.h)

The public implementation deliberately supports a narrower documented subset.
The referenced documentation and upstream code retain their applicable terms;
inspection does not grant publication or relicensing rights to input firmware.
MIT covers the selected original source, authored guides/tests and generated
fictional examples. Python is a separately installed runtime under its own
terms. There are no bundled runtime packages, original device reports or real
firmware bytes. Detailed attribution boundaries are retained in
[third-party notices](../THIRD-PARTY-NOTICES.txt).
