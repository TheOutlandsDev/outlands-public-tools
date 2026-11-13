# Fictional GPT disk-image walkthrough

Extract the [Offline GPT Disk Image Inspector 0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/gpt-image-inspector-v0.1.0), verify SHA256SUMS and supply ordinary CPython 3.12, 3.13, 3.14 or 3.15. Qualification selects 3.15.2 for that minor. The runtime needs only Python's standard library; the ZIP includes no interpreter, disk image or other runtime binary. No installation or administrative privileges are needed.

## Choose a private workspace

Keep the unpacked source and an existing private work directory separate. Copy the Python block below into a new file named `fictional_gpt_walkthrough.py` outside the source directory. Substitute your actual absolute paths in these explicitly fictional PowerShell examples:

```powershell
$module = 'D:\Source\gpt-image-inspector-0.1.0'
$privateWork = 'D:\Private\gpt-work'
python --version
python -E -s -B .\fictional_gpt_walkthrough.py "$module" "$privateWork"
```

On Ubuntu, use your actual absolute paths:

```sh
python3 --version
python3 -E -s -B ./fictional_gpt_walkthrough.py "/absolute/source/gpt-image-inspector-0.1.0" "/absolute/private/gpt-work"
```

The work parent must already exist. Each run chooses a new `fictional-gpt-*` subdirectory and retains all generated examples and private reports for review. It creates seven tiny fictional image files; they are authored test structures, not usable disks, firmware, or a recovery set. Run the script with assertions enabled; `-O` is refused. The examples use `-E -s -B` to ignore Python environment overrides, disable user-site packages and prevent bytecode writes while allowing the script's own sibling imports.

## Execute the complete walkthrough

This single block calls the actual generator and inspector CLI on copied or unpacked source. It verifies both sector sizes, a bad header CRC, an overlap, escaped details and disagreement between tables whose individual CRCs match. It then checks six controlled refusals. Its independent bitwise IEEE CRC-32 implementation checks a known vector and 24 header/table comparisons; it does not reuse the inspector's `zlib.crc32` result as an expected value.

```python
"""Run this only on the generated fictional images below."""
import hashlib
import importlib.util
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
work = Path(tempfile.mkdtemp(prefix="fictional-gpt-", dir=parent))
assert work.parent == parent
runtime_names = ("gpt_inspector.py", "inspection_support.py", "examples/generate.py")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
runtime = {name: digest((module/name).read_bytes()) for name in runtime_names}

# Independent reflected IEEE CRC-32: no runtime helper or zlib call.
def crc32(raw):
    value = 0xffffffff
    for byte in raw:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xedb88320 if value & 1 else 0)
    return value ^ 0xffffffff
assert crc32(b"") == 0 and crc32(b"123456789") == 0xcbf43926

def crc_observations(raw, sector):
    result = {}
    for role, lba in (("primary", 1), ("backup", len(raw)//sector-1)):
        start = lba*sector
        size, stored = struct.unpack_from("<II", raw, start+12)
        header = bytearray(raw[start:start+size]); header[16:20] = bytes(4)
        table_lba, count, stride, table_crc = struct.unpack_from("<QIII", raw, start+72)
        table = raw[table_lba*sector:table_lba*sector+count*stride]
        result[role] = {"header_crc_matches": crc32(header) == stored,
                        "table_crc_matches": crc32(table) == table_crc}
    return result

outcomes = []
def command(case, script, args, expected_exit, expected_stdout):
    before = {path.relative_to(work).as_posix(): digest(path.read_bytes())
              for path in work.rglob("*") if path.is_file()}
    result = subprocess.run([sys.executable, "-E", "-s", "-B", str(module/script), *map(str, args)],
                            cwd=work, capture_output=True, timeout=30)
    assert result.returncode == expected_exit and result.stderr == b"", case
    assert json.loads(result.stdout) == expected_stdout, case
    assert result.stdout == (json.dumps(expected_stdout, sort_keys=True)+os.linesep).encode(), case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before == {name: digest((work/name).read_bytes()) for name in before}, case
    outcomes.append({"case": case, "exit_code": result.returncode})

command("create-fictional-images", "examples/generate.py", ["--output", work/"fixtures"], 0,
        {"status": "FICTIONAL_EXAMPLES_CREATED", "files": 4})
fixtures = work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"clean-512.img", "clean-4096.img", "review-crc.img", "review-overlap.img"}
spec = importlib.util.spec_from_file_location("fictional_generator", module/"examples/generate.py")
generator = importlib.util.module_from_spec(spec); spec.loader.exec_module(generator)
assert Path(generator.__file__).resolve() == module/"examples/generate.py"
crafted = work/"crafted"; crafted.mkdir()
(crafted/"details.img").write_bytes(generator.build_image(partitions=[(36, 40, "</pre><script>fiction</script>")]))
split = generator.build_image(); split[1024+56] ^= 1
# Recompute only the changed primary table/header CRC with the independent code.
table = split[1024:1024+16384]
struct.pack_into("<I", split, 512+88, crc32(table))
struct.pack_into("<I", split, 512+16, 0)
struct.pack_into("<I", split, 512+16, crc32(split[512:512+92]))
(crafted/"split.img").write_bytes(split)
(crafted/"truncated.img").write_bytes(b"fictional truncation")
inputs = {p.relative_to(work).as_posix(): digest(p.read_bytes()) for folder in (fixtures, crafted)
          for p in folder.iterdir()}
assert len(inputs) == 7
reports = []
crc_fields_checked = 0

def inspect_case(case, image, sector, report_name, expected_exit, findings, details=False, finding_count=None):
    global crc_fields_checked
    output = work/report_name
    status = "NO_SCOPE_FINDINGS" if not findings else "REVIEW_REQUIRED"
    expected = {"status": status, "metadata_bytes_read": 512+2*sector+32768,
                "findings": len(findings) if finding_count is None else finding_count, "coverage_issues": 0}
    args = ["--image", image, "--sector-size", sector, "--output", output]
    if details: args.append("--include-details")
    command(case, "gpt_inspector.py", args, expected_exit, expected)
    assert {p.name for p in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    raw = (output/"report.json").read_bytes(); report = json.loads(raw)
    assert report["status"] == status and report["details_included"] is details
    assert report["whole_image_hashed"] is False and report["primary_backup_metadata_compared"] is True
    assert {row["code"] for row in report["findings"]} == set(findings)
    assert report["metadata_bytes_read"] == expected["metadata_bytes_read"]
    original = image.read_bytes()
    expected_crcs = crc_observations(original, sector)
    for header in report["headers"]:
        assert header["table_inspected"] is True
        for key, expected in expected_crcs[header["role"]].items():
            assert header[key] is expected
            crc_fields_checked += 1
        if not details:
            assert "disk_guid" not in header
            assert all(not {"name", "unique_guid", "type_guid"} & row.keys() for row in header["partitions"])
    assert len(report["metadata_regions"]) == 5
    for region in report["metadata_regions"]:
        piece = original[region["offset"]:region["offset"]+region["bytes"]]
        assert len(piece) == region["bytes"] and digest(piece) == region["sha256"]
    payloads = {name: (output/name).read_bytes() for name in ("report.json", "report.html")}
    manifest = json.loads((output/"MANIFEST.json").read_bytes())
    assert manifest == {"schema_version": 1, "files": [
        {"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(payloads.items())]}
    html = payloads["report.html"].decode()
    assert "Content-Security-Policy" in html and "<script>" not in html
    assert str(work).encode() not in raw
    reports.append(report_name)
    return report, raw, html

inspect_case("clean-512", fixtures/"clean-512.img", 512, "clean512-report", 0, [])
inspect_case("clean-4096", fixtures/"clean-4096.img", 4096, "clean4096-report", 0, [])
inspect_case("header-crc-review", fixtures/"review-crc.img", 512, "crc-report", 1, ["GPT_HEADER_CRC_MISMATCH"])
inspect_case("partition-overlap-review", fixtures/"review-overlap.img", 512, "overlap-report", 1, ["PARTITION_OVERLAP_OBSERVED"], finding_count=2)
report, raw, html = inspect_case("details-and-escaped-html", crafted/"details.img", 512, "details-report", 0, [], True)
assert report["headers"][0]["partitions"][0]["name"] == "</pre><script>fiction</script>"
assert "&lt;script&gt;" in html and "disk_guid" in raw.decode()
inspect_case("matching-crcs-disagreeing-tables", crafted/"split.img", 512, "split-report", 1, ["PRIMARY_BACKUP_METADATA_MISMATCH"])

def refusal(case, script, args, code):
    command(case, script, args, 2, {"status": "INCOMPLETE", "error": code})
refusal("truncated-image", "gpt_inspector.py", ["--image", crafted/"truncated.img", "--sector-size", 512,
        "--output", work/"truncated-report"], "IMAGE_ALIGNMENT_INVALID")
refusal("refuse-existing-report", "gpt_inspector.py", ["--image", fixtures/"clean-512.img", "--sector-size", 512,
        "--output", work/"clean512-report"], "OUTPUT_EXISTS")
refusal("refuse-existing-generator-directory", "examples/generate.py", ["--output", fixtures], "OUTPUT_EXISTS")
refusal("refuse-relative-input", "gpt_inspector.py", ["--image", "relative.img", "--sector-size", 512,
        "--output", work/"relative-report"], "LOCAL_ABSOLUTE_PATH_REQUIRED")
refusal("refuse-unsupported-sector", "gpt_inspector.py", ["--image", fixtures/"clean-512.img", "--sector-size", 1024,
        "--output", work/"sector-report"], "ARGUMENTS_INVALID")
refusal("refuse-missing-arguments", "gpt_inspector.py", [], "ARGUMENTS_INVALID")
assert inputs == {name: digest((work/name).read_bytes()) for name in inputs}
assert runtime == {name: digest((module/name).read_bytes()) for name in runtime_names}
expected_files = set(inputs) | {name+"/"+file for name in reports for file in ("report.json", "report.html", "MANIFEST.json")}
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()} == expected_files
assert len(reports) == 6 and len(expected_files) == 25 and crc_fields_checked == 24
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
print(json.dumps({"outcomes": outcomes, "reports_verified": 6, "payload_hashes_verified": 12,
                  "independent_crc_fields_checked": 24, "metadata_regions_hashed": 30,
                  "fixture_files_preserved": 7, "expected_workspace_files": 25,
                  "unexpected_application_files": 0, "bytecode_files": 0,
                  "runtime_bytes_preserved": True, "image_executed_or_mounted": False,
                  "real_images_or_devices_used": False}, sort_keys=True))
```

The expected outcomes, in execution order, are:

```json
[
  {
    "case": "create-fictional-images",
    "exit_code": 0
  },
  {
    "case": "clean-512",
    "exit_code": 0
  },
  {
    "case": "clean-4096",
    "exit_code": 0
  },
  {
    "case": "header-crc-review",
    "exit_code": 1
  },
  {
    "case": "partition-overlap-review",
    "exit_code": 1
  },
  {
    "case": "details-and-escaped-html",
    "exit_code": 0
  },
  {
    "case": "matching-crcs-disagreeing-tables",
    "exit_code": 1
  },
  {
    "case": "truncated-image",
    "exit_code": 2
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
    "case": "refuse-unsupported-sector",
    "exit_code": 2
  },
  {
    "case": "refuse-missing-arguments",
    "exit_code": 2
  }
]
```

The final JSON also reports six complete report directories, twelve payload hashes, thirty metadata-region hashes and seven unchanged fixture files. There are exactly 25 files below the generated work directory: seven inputs and six sets of three report files. These are fictional-fixture acceptance results; the script's byte-preservation hashes intentionally read its tiny examples, while the inspector itself reports only bounded metadata-region hashes.

Four cases return 0, three return the expected review status 1, and six return the expected incomplete/refusal status 2. The script itself exits 0 only after all expected outcomes and invariants hold. A failed assertion means the walkthrough was not accepted; retain the files privately for investigation instead of editing a result to force a pass. No fixture image is executed, mounted, repaired or flashed.

## Read a report

Open a generated `report.html` locally, or read `report.json`. Each fresh report contains exactly those files plus `MANIFEST.json`, whose SHA-256 entries cover the two payload files. The walkthrough independently checks all six manifests and expected metadata regions. The manifest is unsigned and describes byte consistency, not authenticity.

`NO_SCOPE_FINDINGS` means the documented metadata subset produced no finding or explicit coverage issue. `REVIEW_REQUIRED` means read the findings and coverage. `INCOMPLETE` is a controlled invalid/refused-input or resource/I/O result; a complete report is not promised. The CLI prints one JSON status line. These examples assert its entire content, the host's normal line ending, and empty stderr.

Default reports omit declared partition names and GUID fields. They still reveal layout, sizes, counts and metadata hashes, which can identify a build; omission is not anonymization. The details example deliberately exposes an invented name and GUIDs, and checks that static HTML escapes the name. Keep every report private until you have reviewed its full contents. HTML has a restrictive CSP and no scripts or remote assets.

## Inspect an authorized raw image

Use this separate command only after reviewing [the exact format and limits](docs/FORMAT.md) and selecting a stable regular raw image you are permitted to inspect:

```text
python -E -s -B gpt_inspector.py --image ABSOLUTE_REGULAR_IMAGE --sector-size 512 --output ABSOLUTE_NEW_REPORT_DIRECTORY
```

Use `--sector-size 4096` only for a known 4096-byte logical-sector image; this tool does not guess the sector size. Every output directory must be new and its parent must exist. An output error can leave a partial newly created directory; resolve the cause and choose a fresh name. No existing report or image is overwritten.

The inspector reads the protective MBR, fixed primary/final backup header sectors and bounded declared entry arrays. It does not intentionally inspect partition payloads or calculate a whole-image hash. Malformed table ranges are not followed. It supports a documented GPT 1.0/128-byte-entry subset, not full UEFI conformance. Metadata CRCs are not cryptographic authenticity, filesystem validity, bootability, firmware compatibility or permission to deploy an image. Use regular local images, not physical drives or device routes.

Path and descriptor checks require a stable trusted local filesystem and a report parent you control. They are best-effort checks, not an OS sandbox, atomic snapshot or hard native I/O deadline. Links/reparse routes, Windows streams, unsupported device/UNC routes, changing files, limits and existing output are refused within the documented scope. See [security guidance](SECURITY.md).

## Validation and source

The [qualification contract](docs/QUALIFICATION.md) distinguishes the preserved 46-method suite, copied-runtime CLI/CRC/safeguard checks, host-specific native cases and fresh source-ZIP acceptance. The [release records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/gpt-image-inspector-v0.1.0) provide the actual matrix results and checksums. [Historical validation](docs/VALIDATION.md) is retained as historical evidence, not a claim that its original four-lane matrix is the current standalone qualification.

Review source changes before deliberately regenerating `SOURCE-MANIFEST.json`; a matching unsigned manifest alone is not trusted provenance. [MIT](LICENSE) covers the original source and authored examples. Interpreter/bundled-library terms and inspected-input rights remain separate. [Provenance](docs/PROVENANCE.md) records the primary format references; no third-party parser or fixture image is bundled.
