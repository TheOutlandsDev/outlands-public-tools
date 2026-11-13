# Offline GPT Disk Image Inspector

Review GPT partition metadata in one selected regular raw disk-image file. The inspector checks header/table CRCs, declared ranges, overlapping partitions and agreement between primary and backup metadata. It uses bounded metadata reads and writes a private JSON/escaped HTML report with a checksum manifest.

## Download and start

Download the [0.1.0 standalone source ZIP and checksums](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/gpt-image-inspector-v0.1.0), keep its folder intact, and supply ordinary CPython 3.12-3.15 separately. The runtime uses only the Python standard library: no pip package, SDK, administrator account or device connection is required. Interpreter binaries and image files are not bundled.

Follow the [complete fictional walkthrough](USAGE.md). It generates tiny authored examples, inspects known 512- and 4096-byte-sector images, demonstrates CRC and overlap review, verifies report manifests and exercises controlled refusals. All example output goes to a new directory under an existing private work parent outside the source.

For a regular raw image you are authorized to inspect, run from this module folder:

```text
python -E -s -B gpt_inspector.py --image ABSOLUTE_REGULAR_IMAGE --sector-size 512 --output ABSOLUTE_NEW_REPORT_DIRECTORY
```

Use `python3` where appropriate. Explicit sector size must be 512 or 4096; it is not guessed. Each output directory must be new and its parent must already exist. Add `--include-details` only when a private report needs the documented names/GUIDs. [Format and limits](docs/FORMAT.md) define the exact supported subset.

## Metadata scope

Supported GPT revision is 1.0 with 128-byte entries. The inspector reads the protective MBR, primary header at LBA1, backup header at the final LBA and bounded declared entry arrays. Malformed array ranges are not followed. Unsupported revisions/entry sizes and unexplored extensions remain explicit coverage issues. Corrupt/missing headers, hybrid MBR declarations, wrong geometry, overlaps and primary/backup disagreements remain visible.

Inputs must be complete regular local raw images with known 512- or 4096-byte logical sectors. There is no physical-drive mode, sector guessing, embedded-header scan, reconstruction, extraction, mount, repair or image execution. Partition payloads are not intentionally read or hashed; metadata-region hashes are not a whole-image integrity check. CRC agreement does not establish authenticity, filesystem validity, bootability, full UEFI conformance, device compatibility or a deployment plan.

## Reports and status

A completed report has exactly three files:

- `report.json`: schema-versioned metadata observations, findings and coverage.
- `report.html`: escaped static JSON with a restrictive CSP, no scripts or remote assets.
- `MANIFEST.json`: SHA-256 and lengths for the two report payloads.

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No finding or explicit coverage issue in the documented metadata subset. |
| 1 | `REVIEW_REQUIRED` | Findings or unsupported/uninspected coverage require review. |
| 2 | `INCOMPLETE` | Invalid/refused input, bounds or I/O failure prevented a normal result. |

Stdout is one fixed JSON status/count/error line; source filenames and raw upstream exceptions are omitted. Existing output is refused. A failed write can leave a partial new directory; fix the cause and choose a fresh name. The unsigned manifest checks consistency, not authenticity.

Default reports omit declared names and GUID fields, but layout, sizes, counts and hashes can still identify a build. This is not anonymization. `--include-details` exposes disk/partition/type GUIDs and decoded partition names privately. Review all report fields before sharing them.

## File and resource safeguards

Only explicitly supplied stable regular local files are inspected. Absolute paths are required; linked/reparse routes, parent traversal, Windows alternate streams, UNC/device routes and detected input changes are refused. Images are read-only. Fresh private reports are the inspector's only outputs. Path/descriptor checks and limits are best-effort defenses for trusted stable inputs, not hostile-filesystem isolation, atomic snapshots or hard native I/O deadlines.

The image limit is 16TiB logical size, with at most 2MiB total metadata reads and 4096 declared entries per inspected table. Common bounds limit report/finding collections and encoded JSON/HTML size. Bounds refuse a run instead of silently truncating a result. The inspector does not recursively scan a system, invoke a shell/subprocess/network, load an image, access a device or change configuration.

## Qualification and source verification

The [standalone qualification contract](docs/QUALIFICATION.md) requires eight Windows/Ubuntu lanes on pinned Python 3.12, 3.13, 3.14 and 3.15 builds. Each lane selects the preserved 46 original methods and copied-runtime CLI/CRC/safeguard methods in a fresh no-pip environment with zero installed distributions, exact source affinity and independently matching source ZIP rebuilds. Applicable hosted native-link cases are mandatory; exact platform/local permission skips are recorded separately from passes. Actual accepted results are in the [release validation record](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/gpt-image-inspector-v0.1.0).

The runtime, first-party support, fictional generator and both original test files retain their exact bytes. Historical [validation](docs/VALIDATION.md), [format](docs/FORMAT.md) and [example descriptions](examples/README.md) remain available; older local/four-lane observations do not substitute for fresh archived-package acceptance. The generated examples and tests do not establish real disk/device/runtime acceptance.

From this module folder, check the explicit source inventory:

```text
python -E -s -B source_check.py
```

The archive recipe invokes `tests/original_support.py` inside its bound fresh no-pip environment; the adapter requires the selected interpreter version/hash evidence, preserves original test bodies and rejects undocumented skips. A plain `unittest discover` also discovers the new copied-runtime suite; it does not replace the archived-package/source-affinity and strict native checks. Regenerate the unsigned source manifest only after deliberately reviewing a source change, then rerun the gates. A matching manifest alone does not prove trusted authorship, rights or universal secret absence.

## License and feedback

[MIT](LICENSE) covers the new original source, authored documentation/tests and fictional generators. Python and bundled libraries retain their applicable terms; inspected inputs retain their own rights. No upstream parser implementation is vendored. See [provenance](docs/PROVENANCE.md), [third-party notices](THIRD-PARTY-NOTICES.txt) and [security guidance](SECURITY.md).

Report a minimal fictional reproduction through the [issue chooser](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose), with expected behavior, OS/Python version and source commit. Keep real images, device identifiers, customer configurations, raw logs and unredacted reports private. See [CONTRIBUTING](CONTRIBUTING.md).
