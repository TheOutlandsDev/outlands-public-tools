# Fictional boot and vendor-boot walkthrough

Extract the [Boot / Vendor Boot Header Inspector 0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-boot-inspector-v0.1.0), verify SHA256SUMS and supply ordinary CPython 3.12, 3.13, 3.14 or 3.15. Qualification selects 3.15.2 for that minor. The runtime uses only Python's standard library; no interpreter, image, unpacking tool or firmware is bundled. No installation or administrative privileges are required.

## Choose a private workspace

Keep the unpacked source and an existing private work parent separate. Copy the Python block below into a new file named `fictional_boot_walkthrough.py` outside the source directory. Substitute your actual absolute paths in these explicitly fictional PowerShell examples:

```powershell
$module = 'D:\Source\android-boot-inspector-0.1.0'
$privateWork = 'D:\Private\boot-work'
python --version
python -E -s -B .\fictional_boot_walkthrough.py "$module" "$privateWork"
```

On Ubuntu, use your actual absolute paths:

```sh
python3 --version
python3 -E -s -B ./fictional_boot_walkthrough.py "/absolute/source/android-boot-inspector-0.1.0" "/absolute/private/boot-work"
```

The private parent must exist. Each run creates a new canonical `fictional-boot-*` subdirectory and retains its examples/reports for review. Ten tiny files are authored, including deliberately invalid and empty fixtures. None is bootable firmware or a usable recovery set. The script requires assertions; `-O` is refused. `-E -s -B` ignores Python environment overrides, disables user-site packages and prevents bytecode writes while allowing sibling imports from the selected source folder.

## Execute the complete walkthrough

The block invokes the actual generator and inspector CLI for boot v3/v4 and vendor_boot v3/v4. It independently checks declared section offsets/sizes/padded ends, the numeric vendor-v4 table fragments, exact status lines, metadata-region hashes and report manifests. It demonstrates truncated/unsupported/overlapping declarations and six controlled refusals.

The boot-v4 case checks only the declared signature section's offset and size. A paired fixture changes that section's bytes and must retain exactly the same metadata report. This demonstrates that no signature content or authenticity is verified. The script does not inspect payload formats, unpack, decompress, extract, reconstruct, mount or execute an image, validate AVB, or connect to a device. Its byte-preservation checks hash only these tiny authored fixtures; the inspector's `whole_image_hashed` flag remains false.

```python
"""Run only on the tiny fictional boot/vendor images authored below."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

if not __debug__:
    raise RuntimeError("ASSERTIONS_REQUIRED")
module = Path(sys.argv[1]).resolve(strict=True)
parent = Path(sys.argv[2]).resolve(strict=True)
assert module.is_absolute() and parent.is_absolute() and parent.is_dir()
assert not parent.is_relative_to(module) and not module.is_relative_to(parent)
assert not module.is_symlink() and not parent.is_symlink()
assert not getattr(parent, "is_junction", lambda: False)()
work = Path(tempfile.mkdtemp(prefix="fictional-boot-", dir=parent)).resolve()
assert work.parent == parent
runtime_names = ("boot_inspector.py", "binary_reader.py", "inspection_support.py", "examples/generate.py")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
runtime = {name: digest((module/name).read_bytes()) for name in runtime_names}
outcomes = []

def command(case, script, args, expected_exit, expected_stdout):
    before = {p.relative_to(work).as_posix(): digest(p.read_bytes())
              for p in work.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-E", "-s", "-B", str(module/script), *map(str, args)],
                            cwd=work, capture_output=True, timeout=30)
    assert result.returncode == expected_exit and result.stderr == b"", case
    if isinstance(expected_stdout, str):
        wire = expected_stdout
    else:
        assert json.loads(result.stdout) == expected_stdout, case
        wire = json.dumps(expected_stdout, sort_keys=True)
    assert result.stdout == (wire+os.linesep).encode(), case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before == {name: digest((work/name).read_bytes()) for name in before}, case
    outcomes.append({"case": case, "exit_code": result.returncode})

command("create-fictional-images", "examples/generate.py", ["--output", work/"fixtures"], 0,
        "Generated fictional metadata fixtures: 6")
fixtures = work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"boot-v3.img", "boot-v4.img", "vendor-v3.img",
       "vendor-v4.img", "truncated-vendor.img", "unsupported-legacy.img"}
crafted = work/"crafted"; crafted.mkdir()
signature_changed = bytearray((fixtures/"boot-v4.img").read_bytes())
signature_changed[12288:12297] = b"changed!!"
(crafted/"signature-content-changed.img").write_bytes(signature_changed)
overlap = bytearray((fixtures/"vendor-v4.img").read_bytes())
struct.pack_into("<II", overlap, 12396, 8, 4)
(crafted/"fragment-overlap.img").write_bytes(overlap)
limit = bytearray((fixtures/"vendor-v4.img").read_bytes())
struct.pack_into("<I", limit, 2116, 2049)
(crafted/"over-table-limit.img").write_bytes(limit)
(crafted/"empty.img").write_bytes(b"")
inputs = {p.relative_to(work).as_posix(): digest(p.read_bytes())
          for folder in (fixtures, crafted) for p in folder.iterdir()}
assert len(inputs) == 10
reports = []
region_hashes = 0
boot3 = [("header", 0, 1580, 4096, True), ("kernel", 4096, 11, 8192, True),
         ("ramdisk", 8192, 7, 12288, True)]
boot4 = [("header", 0, 1584, 4096, True), ("kernel", 4096, 11, 8192, True),
         ("ramdisk", 8192, 7, 12288, True), ("boot_signature", 12288, 9, 16384, True)]
vendor3 = [("header", 0, 2112, 4096, True), ("vendor_ramdisk", 4096, 12, 8192, True),
           ("dtb", 8192, 5, 12288, True)]
vendor4 = [("header", 0, 2128, 4096, True), ("vendor_ramdisk", 4096, 12, 8192, True),
           ("dtb", 8192, 5, 12288, True), ("ramdisk_table", 12288, 216, 16384, True),
           ("bootconfig", 16384, 6, 20480, True)]
fragments = [{"index": 1, "offset_bytes": 0, "declared_bytes": 5, "type": 1, "within_ramdisk_section": True},
             {"index": 2, "offset_bytes": 5, "declared_bytes": 7, "type": 3, "within_ramdisk_section": True}]


def inspect_case(case, image, report_name, expected_exit, kind, version, section_rows, region_rows,
                 findings, coverage, table=False, fragment_rows=None):
    global region_hashes
    output = work/report_name
    status = "REVIEW_REQUIRED" if findings or coverage else "NO_SCOPE_FINDINGS"
    expected = {"status": status, "metadata_bytes_read": sum(n for label, offset, n in region_rows),
                "findings": len(findings), "coverage_issues": len(coverage)}
    command(case, "boot_inspector.py", ["--image", image, "--output", output], expected_exit, expected)
    assert {p.name for p in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    raw = (output/"report.json").read_bytes(); report = json.loads(raw)
    assert report["status"] == status and report["image_kind"] == kind and report["header_version"] == version
    for key in ("whole_image_hashed", "payloads_inspected", "strings_and_hardware_identifiers_included"):
        assert report[key] is False
    assert {row["code"] for row in report["findings"]} == set(findings)
    assert {row["code"] for row in report["coverage_issues"]} == set(coverage)
    assert report["metadata_bytes_read"] == expected["metadata_bytes_read"]
    original = image.read_bytes()
    expected_regions = [{"id": label, "offset_bytes": offset, "bytes": length,
                         "sha256": digest(original[offset:offset+length])}
                        for label, offset, length in region_rows]
    assert report["metadata_regions"] == expected_regions
    region_hashes += len(region_rows)
    assert report["sections"] == [{"role": role, "offset_bytes": offset, "declared_bytes": length,
                                   "padded_end_bytes": end, "within_file": within}
                                  for role, offset, length, end, within in section_rows]
    assert report["ramdisk_table_inspected"] is table
    assert report["ramdisk_fragments"] == ([] if fragment_rows is None else fragment_rows)
    if section_rows:
        assert report["declared_padded_layout_bytes"] == section_rows[-1][3]
        assert report["trailing_bytes"] == 0
    else:
        assert "declared_padded_layout_bytes" not in report and "header_bytes" not in report
    payloads = {name: (output/name).read_bytes() for name in ("report.json", "report.html")}
    assert json.loads((output/"MANIFEST.json").read_bytes()) == {"schema_version": 1, "files": [
        {"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(payloads.items())]}
    html = payloads["report.html"].decode()
    assert "Content-Security-Policy" in html and "<script>" not in html
    assert str(work).encode() not in raw
    assert all(marker not in raw for marker in (b"fictional-example", b"orchard", b"grove", b"notakernel!",
                                                b"notcpio", b"unsigned!", b"changed!!", b"demo=1"))
    reports.append(report_name)
    return report

inspect_case("boot-v3-layout", fixtures/"boot-v3.img", "boot3-report", 0, "boot", 3, boot3,
             [("header", 0, 8), ("header", 0, 44), ("header", 0, 1580)], [], [])
clean_boot4 = inspect_case("boot-v4-signature-placement", fixtures/"boot-v4.img", "boot4-report", 0, "boot", 4, boot4,
             [("header", 0, 8), ("header", 0, 44), ("header", 0, 1584)], [], [])
inspect_case("vendor-v3-layout", fixtures/"vendor-v3.img", "vendor3-report", 0, "vendor_boot", 3, vendor3,
             [("header", 0, 8), ("header", 0, 12), ("header", 0, 2112)], [], [])
inspect_case("vendor-v4-table-fragments", fixtures/"vendor-v4.img", "vendor4-report", 0, "vendor_boot", 4, vendor4,
             [("header", 0, 8), ("header", 0, 12), ("header", 0, 2128), ("ramdisk-table", 12288, 216)],
             [], [], True, fragments)
truncated_rows = [(*row[:4], row[0] not in ("ramdisk_table", "bootconfig")) for row in vendor4]
inspect_case("truncated-vendor-review", fixtures/"truncated-vendor.img", "truncated-report", 1, "vendor_boot", 4,
             truncated_rows, [("header", 0, 8), ("header", 0, 12), ("header", 0, 2128)],
             ["SECTION_OUTSIDE_FILE", "SECTION_OUTSIDE_FILE"], [])
inspect_case("unsupported-legacy-review", fixtures/"unsupported-legacy.img", "legacy-report", 1, "boot", 2, [],
             [("header", 0, 8), ("header", 0, 44)], [], ["HEADER_VERSION_UNSUPPORTED"])
changed_boot4 = inspect_case("signature-bytes-are-not-verified", crafted/"signature-content-changed.img", "signature-report", 0,
             "boot", 4, boot4, [("header", 0, 8), ("header", 0, 44), ("header", 0, 1584)], [], [])
assert changed_boot4 == clean_boot4
changed_fragments = [fragments[0], {"index": 2, "offset_bytes": 4, "declared_bytes": 8, "type": 3,
                                  "within_ramdisk_section": True}]
inspect_case("declared-fragment-overlap-review", crafted/"fragment-overlap.img", "overlap-report", 1, "vendor_boot", 4,
             vendor4, [("header", 0, 8), ("header", 0, 12), ("header", 0, 2128), ("ramdisk-table", 12288, 216)],
             ["FRAGMENT_OVERLAP_OBSERVED"], [], True, changed_fragments)

def refusal(case, script, args, code):
    command(case, script, args, 2, {"status": "INCOMPLETE", "error": code})
refusal("refuse-existing-report", "boot_inspector.py", ["--image", fixtures/"boot-v4.img",
        "--output", work/"boot4-report"], "OUTPUT_EXISTS")
refusal("refuse-existing-generator-directory", "examples/generate.py", ["--output", fixtures], "OUTPUT_EXISTS")
refusal("refuse-relative-input", "boot_inspector.py", ["--image", "relative.img",
        "--output", work/"relative-report"], "LOCAL_ABSOLUTE_PATH_REQUIRED")
refusal("refuse-missing-arguments", "boot_inspector.py", [], "ARGUMENTS_INVALID")
refusal("refuse-empty-image", "boot_inspector.py", ["--image", crafted/"empty.img",
        "--output", work/"empty-report"], "IMAGE_SIZE_LIMIT")
refusal("refuse-table-entry-limit", "boot_inspector.py", ["--image", crafted/"over-table-limit.img",
        "--output", work/"limit-report"], "TABLE_ENTRY_LIMIT")
assert inputs == {name: digest((work/name).read_bytes()) for name in inputs}
assert runtime == {name: digest((module/name).read_bytes()) for name in runtime_names}
expected_files = set(inputs) | {name+"/"+file for name in reports for file in ("report.json", "report.html", "MANIFEST.json")}
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()} == expected_files
assert len(reports) == 8 and len(expected_files) == 34 and region_hashes == 25
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
print(json.dumps({"outcomes": outcomes, "reports_verified": 8, "payload_hashes_verified": 16,
                  "metadata_regions_hashed": 25, "fixture_files_preserved": 10,
                  "expected_workspace_files": 34, "unexpected_application_files": 0,
                  "bytecode_files": 0, "runtime_bytes_preserved": True,
                  "signature_content_change_preserves_metadata_report": True,
                  "signature_or_avb_verified": False, "payloads_inspected": False,
                  "whole_image_hashed": False, "strings_and_hardware_identifiers_included": False,
                  "image_executed_or_extracted": False, "real_images_or_devices_used": False}, sort_keys=True))
```

The expected outcomes, in execution order, are:

```json
[
  {
    "case": "create-fictional-images",
    "exit_code": 0
  },
  {
    "case": "boot-v3-layout",
    "exit_code": 0
  },
  {
    "case": "boot-v4-signature-placement",
    "exit_code": 0
  },
  {
    "case": "vendor-v3-layout",
    "exit_code": 0
  },
  {
    "case": "vendor-v4-table-fragments",
    "exit_code": 0
  },
  {
    "case": "truncated-vendor-review",
    "exit_code": 1
  },
  {
    "case": "unsupported-legacy-review",
    "exit_code": 1
  },
  {
    "case": "signature-bytes-are-not-verified",
    "exit_code": 0
  },
  {
    "case": "declared-fragment-overlap-review",
    "exit_code": 1
  },
  {
    "case": "refuse-existing-report",
    "exit_code": 2
  },
  {
    "case": "refuse-existing-generator-directory",
    "exit_code": 2
  },
  {
    "case": "refuse-relative-input",
    "exit_code": 2
  },
  {
    "case": "refuse-missing-arguments",
    "exit_code": 2
  },
  {
    "case": "refuse-empty-image",
    "exit_code": 2
  },
  {
    "case": "refuse-table-entry-limit",
    "exit_code": 2
  }
]
```

The final JSON reports eight report directories, sixteen report-file hashes, twenty-five metadata-region hashes and ten unchanged input fixtures. There are exactly 34 files under the generated work directory: ten inputs and eight three-file reports. Here "payload hashes" means SHA-256 of `report.json` and `report.html`, not a hash of kernel, ramdisk, DTB, signature or bootconfig contents.

Six cases return 0, three return the expected review status 1, and six return the expected incomplete/refusal status 2. The walkthrough itself exits 0 only after every expected outcome and invariant matches. A failed assertion means the walkthrough was not accepted; retain its private outputs for diagnosis instead of changing an expected result to force a pass. No real device or firmware is used.

## Interpret the reports

A complete report contains `report.json`, escaped static `report.html` and `MANIFEST.json`. Open HTML locally or read JSON. The manifest records SHA-256 and lengths for the two report files; it is unsigned consistency evidence, not authenticity. The walkthrough independently verifies every manifest and the expected metadata byte ranges, including intentionally overlapping prefix/header reads.

The four supported examples have no scope finding. The truncated vendor example leaves the table uninspected and records outside-file sections. Header version 2 is unsupported coverage with no inferred section layout. The overlap example observes numeric fragment intervals; it does not select, decompress or inspect actual ramdisks. For the supported vendor-v4 fixture, five declared sections begin at 0, 4096, 8192, 12288 and 16384 bytes. Two numeric fragments cover the 12-byte ramdisk declaration; only 2364 metadata bytes are read, including repeated prefixes.

Every report keeps `whole_image_hashed`, `payloads_inspected` and `strings_and_hardware_identifiers_included` false. Raw command lines, product/fragment names, board IDs and load addresses are omitted, with no details option to expose them. Header/table region hashes can still identify bytes containing those values, and layouts/sizes can identify a build. Omission is not anonymization. Review all reports privately before sharing; static HTML has escaped text, a restrictive CSP and no scripts or remote assets.

`NO_SCOPE_FINDINGS` means only that the supported declared metadata produced no finding or explicit coverage issue. Zero-size components are declarations, not a decision that the image suits a boot role. `REVIEW_REQUIRED` means read both findings and coverage. `INCOMPLETE` is a controlled argument/path/resource/I/O result; a complete report is not promised. The CLI emits one JSON status/count/error line. The generator emits one fixed text line. The examples check each entire line, its host-normal ending, and empty stderr.

## Inspect an authorized image

After reading [the exact supported format](docs/FORMAT.md), select a stable ordinary boot/vendor_boot image that you are permitted to inspect:

```text
python -E -s -B boot_inspector.py --image ABSOLUTE_REGULAR_IMAGE --output ABSOLUTE_NEW_REPORT_DIRECTORY
```

Keep `boot_inspector.py`, `binary_reader.py`, `inspection_support.py` and `examples/generate.py` in their existing layout. Use `python3` where appropriate. The report parent must exist, and each output directory must be new. A failed write can leave a partial new directory; resolve the cause and choose a fresh name. Existing images/reports are not overwritten.

The inspector supports exact v3/v4 header subsets, declared section alignment and selected numeric vendor-table extents. Unknown versions, header sizes/page sizes and entry formats remain findings or explicit unsupported coverage. It does not read or hash kernel, ramdisk, DTB, signature, bootconfig or padding payloads. Tail bytes remain uninspected coverage; their contents are not classified as a particular footer or signature. These are structural observations, not AVB/signature verification, payload integrity, authenticity, bootability, device compatibility or permission to flash an image.

Use stable regular local files, not physical drives or device routes. Trusted input/output parents remain required. Sampled file identity checks and cooperative budgets are best-effort defenses, not an OS sandbox, atomic filesystem snapshot or hard native I/O deadline. See [security guidance](SECURITY.md).

## Qualification and source

The [standalone qualification contract](docs/QUALIFICATION.md) covers the preserved 53-method suite, copied-runtime CLI/metadata/safeguard checks and exact native skip rules. [Release records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-boot-inspector-v0.1.0) supply the actual matrix outcomes and checksums. [Historical validation](docs/VALIDATION.md) remains a historical observation, not a substitute for fresh source-archive acceptance.

[MIT](LICENSE) covers original authored source, documentation/tests and fictional generators. Interpreter/bundled-library terms and inspected-image rights remain separate. [Provenance](docs/PROVENANCE.md) links the primary Android/AOSP format references; no upstream implementation, native executable or fixture is bundled. Deliberately review source changes before regenerating an unsigned source manifest; a matching manifest alone does not establish trusted authorship, rights or universal secret absence.
