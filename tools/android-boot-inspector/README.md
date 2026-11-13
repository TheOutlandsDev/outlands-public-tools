# Boot / Vendor Boot Header Inspector

Inspect declared Android boot and vendor_boot v3/v4 metadata in one selected regular local image. The tool reports component offsets, sizes, page-aligned boundaries and selected numeric vendor-ramdisk table issues. It reads bounded metadata and writes a private JSON report, escaped static HTML and a checksum manifest.

## Download and start

Download the [0.1.0 standalone source ZIP and checksums](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-boot-inspector-v0.1.0), keep its folder intact, and supply ordinary CPython 3.12-3.15 separately. The runtime uses only Python's standard library; no pip package, Android SDK, unpacking binary, administrator account or device connection is needed. Interpreters, images and firmware are excluded from the ZIP.

The [complete fictional walkthrough](USAGE.md) creates tiny non-bootable examples for boot v3/v4 and vendor_boot v3/v4, verifies metadata/report hashes, reviews invalid declarations and checks output/resource refusals. It checks only the declared boot-v4 signature placement; changing signature bytes must leave the same metadata report. All outputs use a new directory under an existing private work parent outside the source.

For a stable regular image you are authorized to inspect, run from this module folder:

```text
python -E -s -B boot_inspector.py --image ABSOLUTE_REGULAR_IMAGE --output ABSOLUTE_NEW_REPORT_DIRECTORY
```

Use `python3` where appropriate. Keep the inspector, `binary_reader.py`, `inspection_support.py` and example subfolder together. Each report directory must be new and its parent must exist. Read [the exact supported subset](docs/FORMAT.md) before interpreting results.

## Declared metadata scope

`ANDROID!` selects boot v3/v4 with exact 1580/1584-byte headers and 4096-byte pages. `VNDRBOOT` selects vendor_boot v3/v4 with exact 2112/2128-byte headers and the supported declared vendor page size. Section arithmetic checks declared data ends and padded boundaries without reading payloads/padding. Vendor headers can span multiple pages. Unsupported versions/extensions remain explicit coverage; they are not guessed.

Vendor-v4 tables use supported 108-byte entries. The inspector checks declared table size/count/stride and numeric fragment offsets, lengths and types, including observed gaps/overlaps and coverage of the declared ramdisk section. Names, board IDs, bootloader selection, decompression and actual ramdisk content are not evaluated. Zero-size components remain declarations without a boot-role decision. Extra tail bytes remain uninspected coverage, without inferring AVB/footer contents.

Every report keeps `whole_image_hashed`, `payloads_inspected` and `strings_and_hardware_identifiers_included` false. The boot-signature field supplies only a declared size used in layout arithmetic; signature content is neither read nor verified. No extraction, decompression, reconstruction, mounting, image execution, AVB/signature verification, live-device access or flashing is performed. An image with no scope findings can still be unusable or untrusted. Metadata observations do not establish authenticity, payload integrity, bootability, compatible devices or a complete usable firmware set.

## Reports and status

A completed report has exactly:

- `report.json`: schema-versioned metadata observations, findings and coverage.
- `report.html`: escaped static JSON with a restrictive CSP, no scripts or remote assets.
- `MANIFEST.json`: SHA-256 and lengths for the two report files.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No finding or explicit coverage issue in the documented metadata subset. |
| 1 | `REVIEW_REQUIRED` | Observed layout issues or unsupported/uninspected coverage require review. |
| 2 | `INCOMPLETE` | Arguments, paths, bounds, changed input or I/O prevented a normal result. |

Stdout is one fixed JSON status/count/error line, without input paths or upstream exception text. Existing reports are refused. A write error can leave a partial new directory; resolve it and choose a fresh name. The unsigned manifest checks report consistency, not authenticity.

Raw command lines, product/fragment names, board IDs and physical load addresses are omitted, with no `--include-details` switch. Hashes cover only listed metadata byte ranges, including header/table bytes that may contain private strings. Sizes, layouts and hashes can still identify a build; omission is not anonymization. Keep real images/reports private until fully reviewed. No inspection result grants redistribution or deployment rights.

## File and resource safeguards

Select one stable regular local image with an absolute path and controlled existing parents. Linked/reparse routes, traversal, Windows alternate streams, UNC/device routes and detected input changes are refused. Inputs are read-only; the inspector's only outputs are fresh reports. It does not discover images, scan a device or recursively inspect a system. Trusted stable paths and an output parent you control remain required; sampled path/descriptor identities and limits are not hostile-filesystem isolation, atomic snapshots or hard native I/O deadlines.

An image may be at most 16 TiB; cumulative metadata reads at most 512 KiB. Vendor-v4 tables have at most 2048 entries. Collections have a 4000-row bound and encoded JSON/HTML each an 8 MiB limit. Declared payload sizes never cause payload reads or allocation. The [format contract](docs/FORMAT.md) defines page-size, header/table and output details.

## Qualification and source verification

The [standalone qualification contract](docs/QUALIFICATION.md) requires eight Windows/Ubuntu lanes on pinned CPython 3.12, 3.13, 3.14 and 3.15 builds. Each selects all 53 original methods plus copied-runtime CLI/metadata/safeguard checks in a fresh no-pip environment with zero distributions and exact extracted-source affinity. Source ZIP/build-manifest rebuilds must match. Applicable hosted native links/hardlinks are mandatory; exact opposite-platform and actual local Windows error 1314 limitations are recorded separately from passes. Accepted results are in the [release validation record](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-boot-inspector-v0.1.0).

The inspector, bounded reader, shared support, generator and both original test files retain exact bytes. Historical [validation](docs/VALIDATION.md), [format](docs/FORMAT.md), [provenance](docs/PROVENANCE.md) and [examples](examples/README.md) retain their source/evidence boundary. Generated fixtures are not real firmware/device acceptance.

From this module folder, check the explicit source inventory:

```text
python -E -s -B source_check.py
```

Archive qualification invokes the original-test adapter inside its bound fresh environment using measured interpreter version/hash evidence. Plain unittest discovery also selects the copied-runtime tests; it does not replace strict native rules, source affinity or fresh archive acceptance. Regenerate `SOURCE-MANIFEST.json` only after deliberately reviewing source changes. This unsigned inventory is not trusted provenance or a universal privacy guarantee.

## License and feedback

[MIT](LICENSE) covers original source, authored documentation/tests and fictional generators. Python and bundled libraries retain their own terms, as do inspected inputs. No AOSP implementation, format header source or native executable is vendored. See [third-party notices](THIRD-PARTY-NOTICES.txt), [security guidance](SECURITY.md) and [CONTRIBUTING](CONTRIBUTING.md).

Use the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose) with a small fictional reproduction, expected result, source commit and OS/Python version. Keep real firmware, device identifiers, customer paths, raw logs and unredacted reports private.
