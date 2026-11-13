# Android Sparse Image Inspector

Review the structure of one selected regular Android sparse-image file using bounded metadata-header reads. The inspector checks file/chunk boundaries, declared expanded sizes and RAW/FILL/DONT_CARE accounting. CRC32 and image-checksum declarations remain explicitly unverified. It skips payload bytes and never reconstructs an image.

## Download and start

Download the [0.1.0 standalone source ZIP and checksums](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-sparse-inspector-v0.1.0), keep its folder intact, and supply ordinary CPython 3.12-3.15 separately. The runtime uses only Python's standard library; no pip package, Android SDK, AOSP converter, administrator account or device connection is needed. Interpreters, images and firmware are not bundled.

Follow the [complete fictional walkthrough](USAGE.md). It generates tiny authored fixtures and demonstrates clean layout accounting, unverified CRC declarations, truncation, changed payloads with identical metadata, unknown types and controlled refusals. All outputs use a new directory under an existing private work parent outside the source.

For a stable regular sparse file you are authorized to inspect, run from this module folder:

```text
python -E -s -B sparse_inspector.py --image ABSOLUTE_REGULAR_SPARSE_IMAGE --output ABSOLUTE_NEW_REPORT_DIRECTORY
```

Use `python3` where appropriate. Keep `sparse_inspector.py`, `binary_reader.py`, `inspection_support.py` and the example subfolder together. The report parent must exist; each output directory must be new. [Format and limits](docs/FORMAT.md) define the exact supported subset.

## Structural scope and CRC boundary

The known base layout is sparse major version 1 with little-endian fields, a file header of at least 28 bytes, chunk headers of at least 12 bytes and a positive block size divisible by four. Supported chunk types are RAW, FILL, DONT_CARE and CRC32. Unknown types and unsupported major versions stop inspection. New minor versions and larger headers are explicit coverage; extension contents are skipped rather than interpreted.

The walk reads only known metadata headers and skips RAW/FILL/CRC payload ranges. Every report has `payload_crc_checked: false` and `whole_image_hashed: false`. CRC32 chunks produce `CRC32_UNVERIFIED`; a nonzero file-header checksum produces `IMAGE_CHECKSUM_UNVERIFIED`. Stored checksums are not verified. Header hashes cover only listed metadata regions, not the whole image or reconstructed output.

No conversion, extraction, mount, flashing, image execution or physical-drive mode exists. One file is inspected at a time; numbered sparsechunk parts are not combined or ordered. A structural pass does not establish payload integrity, complete/compatible reconstruction sets, filesystem contents, Android Verified Boot, authenticity, device compatibility or bootability. DONT_CARE declares a skipped output range, not observed zero or erased destination data.

## Reports and exit status

A completed report has exactly:

- `report.json`: structural header/chunk observations, findings, coverage and metadata-region hashes.
- `report.html`: escaped static JSON with a restrictive CSP, no scripts or remote assets.
- `MANIFEST.json`: SHA-256 and lengths for the two report files.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No finding or explicit coverage issue within the supported structural subset. |
| 1 | `REVIEW_REQUIRED` | A finding or explicit limitation requires review; the walk can be partial. |
| 2 | `INCOMPLETE` | Arguments, paths, resource limits or I/O prevented a normal result. |

`layout_walk_complete` means all declared chunks were walked, not that every check passed. Final output-accounting fields are absent for stopped walks. Stdout is one fixed JSON status/count/error line, without local filenames or raw payload bytes. A successful manifest checks report byte consistency, not authenticity.

Existing output is refused. A write failure may leave partial new output; resolve the cause and choose a fresh directory. Reports omit local paths and payload contents but are not anonymized: sizes, layouts and metadata hashes can identify an image. Keep real inputs and reports private until fully reviewed; no inspection result grants redistribution or deployment rights.

## File and resource safeguards

Inputs must be stable regular local files with absolute paths. Linked/reparse routes, parent traversal, unsupported device/UNC routes, Windows alternate streams and detected input changes are refused. Inputs are read-only; fresh reports are the inspector's only outputs. Use directories and stable trusted inputs you control. Sampled path/descriptor identities and limits are not hostile-filesystem isolation, atomic snapshots or hard native I/O deadlines.

Input size and declared expanded size are each capped at 16 TiB; block size at 1 MiB; chunk count at 4,000; metadata reads at 1 MiB. JSON and HTML each have an 8 MiB limit. Base headers normally account for `28 + 12 * inspected_chunks` metadata bytes. Declared output is reported as an exact decimal string, without allocating an expanded-image buffer. A bound refuses the run instead of silently truncating a result.

## Qualification and source verification

The [standalone qualification contract](docs/QUALIFICATION.md) requires eight Windows/Ubuntu lanes on pinned CPython 3.12, 3.13, 3.14 and 3.15 builds. Each selects the unchanged 45 original methods plus copied-runtime CLI/metadata/safeguard checks in a fresh no-pip environment with zero distributions and exact extracted-source affinity. Independent source ZIP/build-manifest rebuilds must match; applicable hosted native link cases are mandatory. Exact opposite-platform and actual local Windows 1314 skips are recorded separately from passes. Accepted results are in the [release validation record](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-sparse-inspector-v0.1.0).

The inspector, bounded reader, shared support, generator and both original test files retain exact bytes. [Historical validation](docs/VALIDATION.md), [format](docs/FORMAT.md) and [examples](examples/README.md) retain their original scope/evidence. Generated fixtures do not prove real-firmware, conversion, device or deployment acceptance.

From this module folder, check the explicit source inventory:

```text
python -E -s -B source_check.py
```

Archive qualification invokes the original-test adapter inside its bound fresh environment with actual interpreter version/hash evidence. Plain unittest discovery also includes copied-runtime methods and does not replace source affinity, native skip rules or fresh archived-package acceptance. Deliberately review source changes before regenerating `SOURCE-MANIFEST.json`; this unsigned inventory is not trusted provenance or a universal privacy guarantee.

## License and feedback

[MIT](LICENSE) covers new original source, authored documentation/tests and fictional generators. Python and bundled libraries retain their own terms, as do inspected inputs. No AOSP implementation or binary is vendored. See [provenance](docs/PROVENANCE.md), [third-party notices](THIRD-PARTY-NOTICES.txt) and [security guidance](SECURITY.md).

Use the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose) for a small invented reproduction, expected behavior, OS/Python version and source commit. Keep actual firmware, customer paths, device identifiers, raw logs and unredacted reports private. Read [CONTRIBUTING](CONTRIBUTING.md) before sharing inputs.
