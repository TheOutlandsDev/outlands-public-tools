# Boot / Vendor Boot Header Inspector

Inspect declared **Android boot and vendor_boot header versions 3 and 4** in one
explicitly selected, ordinary local image file. It reports component offsets,
sizes, page-aligned boundaries and selected vendor ramdisk table extent issues.
It reads bounded metadata and writes a private JSON report, escaped static HTML
and a checksum manifest. Python 3.12 or newer, standard library only.

This original MIT tool is useful when comparing build artifacts or diagnosing a
truncated image before deeper investigation. It does not extract, decompress,
mount, execute, reconstruct or flash anything. It does not verify AVB, signatures,
kernel/ramdisk content, bootability, compatible devices or a usable firmware set.
An image with no scope findings can still be unusable. Zero-size components are
reported as declarations without deciding whether they suit an image's role.

## Install and try generated examples

Clone or download [outlands-public-tools](https://github.com/TheOutlandsDev/outlands-public-tools)
and enter `tools/android-boot-inspector`. Run `python --version`; no package
installation, Android SDK, administrative privileges or device connection is
required. Use `python3` if that is your Python 3.12+ command.

Choose an existing private directory outside the source checkout. Inputs and
outputs below use absolute paths; every output directory must be new. Keep real
firmware and reports private. See the [private workspace guide](../../docs/PRIVATE-WORKSPACE.md).

Windows PowerShell, after setting `$privateWork` to your own existing directory:

```powershell
python -B examples/generate.py --output "$privateWork/boot-demo"
python -B boot_inspector.py --image "$privateWork/boot-demo/boot-v4.img" --output "$privateWork/boot-report"
python -B boot_inspector.py --image "$privateWork/boot-demo/vendor-v4.img" --output "$privateWork/vendor-report"
```

Linux/macOS shell, using a private directory you control:

```sh
private_work="$HOME/private-outlands"
mkdir -p "$private_work"
python3 -B examples/generate.py --output "$private_work/boot-demo"
python3 -B boot_inspector.py --image "$private_work/boot-demo/vendor-v4.img" --output "$private_work/vendor-report"
```

The generator creates six tiny **fictional, non-bootable** image fixtures. The
four supported v3/v4 examples return exit **0**, `NO_SCOPE_FINDINGS`. For the
generated vendor-v4 example, declared section offsets are 0, 4096, 8192, 12288 and
16384 bytes, with two fragments covering the 12-byte vendor ramdisk declaration.
The file is 20480 bytes; only 2364 metadata bytes are read, including repeated
prefix reads. The table holds only invented numbers and names.

```text
python -B boot_inspector.py --image ABSOLUTE_PATH/truncated-vendor.img --output ABSOLUTE_PATH/new-review-report
python -B boot_inspector.py --image ABSOLUTE_PATH/unsupported-legacy.img --output ABSOLUTE_PATH/new-legacy-report
```

Replace each placeholder with an actual absolute local path. Both review
examples return exit **1**. The first reports declared sections outside the
file. The second records unsupported header version 2 and leaves layout
inspection undone. Read [examples](examples/README.md) and the exact
[supported format/report contract](docs/FORMAT.md) before using real inputs.

## Command and results

```text
python -B boot_inspector.py --image ABSOLUTE_IMAGE_FILE --output ABSOLUTE_NEW_DIRECTORY
python -B boot_inspector.py --help
```

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | `NO_SCOPE_FINDINGS` | No finding or unexpected coverage issue in the documented metadata scope. |
| 1 | `REVIEW_REQUIRED` | Observed layout issue, unsupported version/extension or uninspected trailing bytes. |
| 2 | `INCOMPLETE` | Invalid arguments/input path, resource limit, changed input, I/O or output error. |

Successful inspection creates `report.json`, `report.html` and `MANIFEST.json` in
one fresh directory. Existing output is refused. Stdout contains only status,
metadata-read count and finding/coverage counts; errors use fixed codes, never
input paths or upstream exception text. No source filename is embedded in the
report. A partial output directory may remain after an I/O failure; use a new
output name after resolving the cause.

Reports always omit command lines, product/fragment names, board IDs and physical
load addresses. Metadata hashes, sizes, numeric layout and file fingerprints can
still identify a build. Omission is **not anonymization**. The region hashes
describe only inspected byte ranges, including header bytes that may contain
private strings; they are not whole-image hashes or authenticity checks. HTML
uses escaped text and a restrictive CSP, with no JavaScript, remote assets or
network calls. It is a formatted report, not an interactive application.

## Supported checks and limits

- `ANDROID!` boot v3/v4 uses fixed 4096-byte pages and exact 1580/1584-byte
  headers. `VNDRBOOT` v3/v4 uses exact 2112/2128-byte headers. Other versions
  and larger header extensions are explicit coverage issues.
- Vendor page sizes in this subset are powers of two from 512 through 65536;
  a header may span multiple pages. Other nonzero sizes are unsupported.
- Header/section data and padded ends are checked against file size without
  reading payloads or padding. Trailing bytes, including possible AVB metadata,
  remain uninspected and require review; their contents are never classified.
- Vendor v4 tables use exact 108-byte entries and at most 2048 entries. Checks
  cover declared table length, fragment extents, observed overlaps/gaps and
  numeric types 0 through 3. Names, uniqueness, board selection and boot order
  are not evaluated. Extended entry formats are unsupported.
- At most 16 TiB per image, 512 KiB of total metadata reads, 4000 rows per
  collection, and 8 MiB each for JSON and HTML. One selected file per invocation.
- Only stable, regular local files with absolute paths and existing controlled
  parents are accepted. Symlinks/reparse points, traversal, UNC/device paths and
  Windows alternate streams are rejected. No discovery scans or device reads.
  These checks are not a defense against a hostile process replacing parent
  paths concurrently; use a private workspace you control.

## Test, contribute and licensing

```text
python -B -W error -m unittest discover -s tests -v
python -B source_check.py
```

The [validation guide](docs/VALIDATION.md) explains generated test coverage,
platform skips and the boundary between source checks and real device behavior.
The source gate verifies the explicit source-only SHA-256 inventory; it is not
a signature or provenance guarantee. Python is separately installed and remains
under its own applicable terms.

Suggestions and useful real-world format requests are welcome through the
[repository issue forms](https://github.com/TheOutlandsDev/outlands-public-tools/issues/new/choose).
Share a small fictional reproduction rather than real firmware, identifying
reports or device configuration. See [CONTRIBUTING](CONTRIBUTING.md),
[SECURITY](SECURITY.md), [provenance](docs/PROVENANCE.md),
[third-party notices](THIRD-PARTY-NOTICES.txt) and [MIT license](LICENSE).
