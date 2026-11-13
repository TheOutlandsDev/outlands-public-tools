# Fictional Android sparse-image walkthrough

Extract the [Android Sparse Image Inspector 0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-sparse-inspector-v0.1.0), verify SHA256SUMS and supply ordinary CPython 3.12, 3.13, 3.14 or 3.15. Qualification selects 3.15.2 for that minor. The runtime uses only Python's standard library; the ZIP includes no interpreter, sparse image, converter or firmware. No installation or administrative privileges are required.

## Choose a private workspace

Keep the unpacked source and an existing private work parent separate. Copy the Python block below into a new file named `fictional_sparse_walkthrough.py` outside the source directory. Substitute your actual absolute paths in these explicitly fictional PowerShell examples:

```powershell
$module = 'D:\Source\android-sparse-inspector-0.1.0'
$privateWork = 'D:\Private\sparse-work'
python --version
python -E -s -B .\fictional_sparse_walkthrough.py "$module" "$privateWork"
```

On Ubuntu, use your actual absolute paths:

```sh
python3 --version
python3 -E -s -B ./fictional_sparse_walkthrough.py "/absolute/source/android-sparse-inspector-0.1.0" "/absolute/private/sparse-work"
```

The private parent must already exist. Each run chooses a new `fictional-sparse-*` subdirectory and retains its generated examples and private reports for review. It authors eight tiny files, including deliberately incomplete and empty fixtures. These are test structures, not usable firmware or a reconstruction set. The script requires assertions; `-O` is refused. `-E -s -B` ignores Python environment overrides, disables user-site packages and prevents bytecode writes while allowing sibling imports from the selected source folder.

## Execute the complete walkthrough

The block invokes the actual generator and inspector CLI. It checks clean RAW/FILL/DONT_CARE accounting, explicit CRC32 and image-checksum coverage, a truncated chunk header, an unknown chunk type and six controlled refusals. A changed-payload example deliberately keeps all headers identical: its complete metadata report must equal the clean report. This demonstrates the documented boundary, not payload integrity.

The script performs no CRC calculation and never reconstructs an image. It independently checks 22 metadata-region SHA-256 entries and six report manifests. Its byte-preservation checks read only these tiny authored fixture files; that acceptance check is separate from the inspector's `whole_image_hashed: false` behavior.

```python
"""Run only on the tiny fictional sparse images authored below."""
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
work = Path(tempfile.mkdtemp(prefix="fictional-sparse-", dir=parent))
assert work.parent == parent
runtime_names = ("sparse_inspector.py", "binary_reader.py", "inspection_support.py", "examples/generate.py")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
runtime = {name: digest((module/name).read_bytes()) for name in runtime_names}
outcomes = []

def command(case, script, args, expected_exit, expected_stdout, wire=None):
    before = {p.relative_to(work).as_posix(): digest(p.read_bytes())
              for p in work.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-E", "-s", "-B", str(module/script), *map(str, args)],
                            cwd=work, capture_output=True, timeout=30)
    assert result.returncode == expected_exit and result.stderr == b"", case
    assert json.loads(result.stdout) == expected_stdout, case
    expected_wire = json.dumps(expected_stdout, sort_keys=True) if wire is None else wire
    assert result.stdout == (expected_wire+os.linesep).encode(), case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before == {name: digest((work/name).read_bytes()) for name in before}, case
    outcomes.append({"case": case, "exit_code": result.returncode})

command("create-fictional-images", "examples/generate.py", ["--output", work/"fixtures"], 0,
        {"status": "GENERATED", "files": 3}, '{"status":"GENERATED","files":3}')
fixtures = work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"valid.sparse", "crc-unverified.sparse", "truncated.sparse"}
valid = (fixtures/"valid.sparse").read_bytes()
assert len(valid) == 72
crafted = work/"crafted"; crafted.mkdir()
changed = bytearray(valid); changed[40:44] = b"ZZZZ"; changed[56:60] = b"YYYY"
(crafted/"payload-changed.sparse").write_bytes(changed)
checksum = bytearray(valid); struct.pack_into("<I", checksum, 24, 0x11223344)
(crafted/"checksum-declared.sparse").write_bytes(checksum)
unknown = bytearray(valid); struct.pack_into("<H", unknown, 28, 0xcac5)
(crafted/"unknown-type.sparse").write_bytes(unknown)
(crafted/"over-chunk-limit.sparse").write_bytes(struct.pack("<IHHHHIIII", 0xed26ff3a, 1, 0, 28, 12, 4, 4, 4001, 0))
(crafted/"empty.sparse").write_bytes(b"")
inputs = {p.relative_to(work).as_posix(): digest(p.read_bytes())
          for folder in (fixtures, crafted) for p in folder.iterdir()}
assert len(inputs) == 8
reports = []
region_hashes = 0
base_regions = [("file-header", 0, 28), ("chunk-1", 28, 12),
                ("chunk-2", 44, 12), ("chunk-3", 60, 12)]

def inspect_case(case, image, report_name, expected_exit, findings, coverage, regions, complete):
    global region_hashes
    output = work/report_name
    status = "REVIEW_REQUIRED" if findings or coverage else "NO_SCOPE_FINDINGS"
    expected = {"status": status, "metadata_bytes_read": sum(length for label, offset, length in regions),
                "findings": len(findings), "coverage_issues": len(coverage)}
    command(case, "sparse_inspector.py", ["--image", image, "--output", output], expected_exit, expected)
    assert {p.name for p in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    raw = (output/"report.json").read_bytes(); report = json.loads(raw)
    assert report["status"] == status and report["layout_walk_complete"] is complete
    assert report["payload_crc_checked"] is False and report["whole_image_hashed"] is False
    assert {row["code"] for row in report["findings"]} == set(findings)
    assert {row["code"] for row in report["coverage_issues"]} == set(coverage)
    assert report["metadata_bytes_read"] == expected["metadata_bytes_read"]
    original = image.read_bytes()
    expected_regions = [{"id": label, "offset": offset, "bytes": length,
                         "sha256": digest(original[offset:offset+length])}
                        for label, offset, length in regions]
    assert report["metadata_regions"] == expected_regions
    region_hashes += len(regions)
    assert report["header"]["declared_output_blocks"] == 4
    assert report["header"]["declared_output_bytes"] == "16"
    assert report["header"]["block_bytes"] == 4
    assert report["header"]["image_checksum_declared"] is ("IMAGE_CHECKSUM_UNVERIFIED" in coverage)
    assert all("crc" not in key.lower() and "checksum" not in key.lower() for row in report["chunks"] for key in row)
    if complete:
        assert report["observed_output_blocks"] == 4 and report["accounted_input_bytes"] == len(original)
    else:
        assert "observed_output_blocks" not in report and "accounted_input_bytes" not in report
    payloads = {name: (output/name).read_bytes() for name in ("report.json", "report.html")}
    manifest = json.loads((output/"MANIFEST.json").read_bytes())
    assert manifest == {"schema_version": 1, "files": [
        {"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(payloads.items())]}
    html = payloads["report.html"].decode()
    assert "Content-Security-Policy" in html and "<script>" not in html
    assert str(work).encode() not in raw
    assert all(marker not in raw for marker in (b"DEMO", b"ABCD", b"ZZZZ", b"YYYY"))
    reports.append(report_name)
    return report

clean = inspect_case("clean-structural-layout", fixtures/"valid.sparse", "clean-report", 0, [], [], base_regions, True)
assert [row["kind"] for row in clean["chunks"]] == ["RAW", "FILL", "DONT_CARE"]
inspect_case("crc-declaration-remains-unverified", fixtures/"crc-unverified.sparse", "crc-report", 1,
             [], ["CRC32_UNVERIFIED"], base_regions+[("chunk-4", 72, 12)], True)
inspect_case("truncated-chunk-header-review", fixtures/"truncated.sparse", "truncated-report", 1,
             ["CHUNK_HEADER_TRUNCATED"], [], base_regions[:3], False)
payload_changed = inspect_case("changed-payload-same-metadata", crafted/"payload-changed.sparse", "payload-report", 0,
                              [], [], base_regions, True)
assert payload_changed == clean
inspect_case("image-checksum-declaration-unverified", crafted/"checksum-declared.sparse", "checksum-report", 1,
             [], ["IMAGE_CHECKSUM_UNVERIFIED"], base_regions, True)
inspect_case("unknown-chunk-stops-layout-walk", crafted/"unknown-type.sparse", "unknown-report", 1,
             [], ["CHUNK_TYPE_UNSUPPORTED"], base_regions[:2], False)

def refusal(case, script, args, code):
    command(case, script, args, 2, {"status": "INCOMPLETE", "error": code})
refusal("refuse-chunk-count-limit", "sparse_inspector.py", ["--image", crafted/"over-chunk-limit.sparse",
        "--output", work/"limit-report"], "CHUNK_COUNT_LIMIT")
refusal("refuse-existing-report", "sparse_inspector.py", ["--image", fixtures/"valid.sparse",
        "--output", work/"clean-report"], "OUTPUT_EXISTS")
refusal("refuse-existing-generator-directory", "examples/generate.py", ["--output", fixtures], "OUTPUT_EXISTS")
refusal("refuse-relative-input", "sparse_inspector.py", ["--image", "relative.sparse",
        "--output", work/"relative-report"], "LOCAL_ABSOLUTE_PATH_REQUIRED")
refusal("refuse-missing-arguments", "sparse_inspector.py", [], "ARGUMENTS_INVALID")
refusal("refuse-empty-image", "sparse_inspector.py", ["--image", crafted/"empty.sparse",
        "--output", work/"empty-report"], "IMAGE_SIZE_LIMIT")
assert inputs == {name: digest((work/name).read_bytes()) for name in inputs}
assert runtime == {name: digest((module/name).read_bytes()) for name in runtime_names}
expected_files = set(inputs) | {name+"/"+file for name in reports for file in ("report.json", "report.html", "MANIFEST.json")}
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()} == expected_files
assert len(reports) == 6 and len(expected_files) == 26 and region_hashes == 22
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
print(json.dumps({"outcomes": outcomes, "reports_verified": 6, "payload_hashes_verified": 12,
                  "metadata_regions_hashed": 22, "fixture_files_preserved": 8,
                  "expected_workspace_files": 26, "unexpected_application_files": 0,
                  "bytecode_files": 0, "runtime_bytes_preserved": True,
                  "payload_change_preserves_metadata_report": True, "payload_crc_calculated": False,
                  "whole_image_hash_claimed": False, "image_executed_or_reconstructed": False,
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
    "case": "clean-structural-layout",
    "exit_code": 0
  },
  {
    "case": "crc-declaration-remains-unverified",
    "exit_code": 1
  },
  {
    "case": "truncated-chunk-header-review",
    "exit_code": 1
  },
  {
    "case": "changed-payload-same-metadata",
    "exit_code": 0
  },
  {
    "case": "image-checksum-declaration-unverified",
    "exit_code": 1
  },
  {
    "case": "unknown-chunk-stops-layout-walk",
    "exit_code": 1
  },
  {
    "case": "refuse-chunk-count-limit",
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
    "case": "refuse-missing-arguments",
    "exit_code": 2
  },
  {
    "case": "refuse-empty-image",
    "exit_code": 2
  }
]
```

The final JSON also reports six report directories, twelve payload-file hashes, twenty-two metadata-region hashes and eight unchanged input fixtures. There are exactly 26 files under the generated work directory: eight inputs and six three-file reports. Here "payload-file hashes" means hashes of `report.json` and `report.html`, not a checksum of sparse-image payload data.

Three cases return 0, four return the expected review status 1 and six return the expected refusal/incomplete status 2. The walkthrough itself exits 0 only after all outcomes and invariants match. A failed assertion means the walkthrough was not accepted; retain its private files for diagnosis instead of changing an expected result to force a pass. No image is reconstructed, extracted, mounted, executed or flashed.

## Interpret a report

A fresh report contains `report.json`, escaped static `report.html` and `MANIFEST.json`. Open HTML locally or read JSON. The manifest records SHA-256 and lengths for the two report files; it is unsigned consistency evidence, not authenticity. The script independently checks every manifest and hashes exactly the expected base-header byte ranges.

`NO_SCOPE_FINDINGS` means the supported structural metadata produced no finding or explicit coverage issue. It does not establish complete payloads, a valid CRC, successful reconstruction or a usable image. `REVIEW_REQUIRED` means read the findings and coverage; a partial walk can still produce a report. `INCOMPLETE` is a controlled argument/path/resource/I/O result, and a complete report is not promised. The examples assert the whole JSON status line, its host-normal line ending, and empty stderr.

Every inspected report keeps `payload_crc_checked` and `whole_image_hashed` false. `CRC32_UNVERIFIED` remains visible for CRC chunks, and `IMAGE_CHECKSUM_UNVERIFIED` for a nonzero header checksum declaration. The stored CRC/payload bytes are not read for verification. `layout_walk_complete` means the declared sequence was walked, not that all checks passed. Incomplete walks omit final output-accounting fields rather than inventing zeroes.

Report fields omit local filenames and raw payload bytes, but sizes, layouts and metadata-region hashes can correlate an input. These reports are not anonymized. Review all fields privately before sharing. Static HTML has escaped text, a restrictive CSP and no scripts or remote assets. The source/report manifest does not authorize redistribution of any inspected firmware or derived data.

## Inspect an authorized sparse image

After reviewing [the exact format and limits](docs/FORMAT.md), select a stable regular local Android sparse file you are permitted to inspect:

```text
python -E -s -B sparse_inspector.py --image ABSOLUTE_REGULAR_SPARSE_IMAGE --output ABSOLUTE_NEW_REPORT_DIRECTORY
```

Keep `sparse_inspector.py`, `binary_reader.py` and `inspection_support.py` adjacent; keep `examples/generate.py` in its example subfolder. Use `python3` where appropriate. The report parent must exist and every output directory must be new. A failed write can leave partial new output; resolve the cause and choose a fresh name. Existing images/reports are not overwritten.

The implementation decodes the base 28-byte file header and selected 12-byte chunk headers, seeks over payload and extension ranges, and applies exact size/block accounting with bounded arithmetic. Unknown types/unsupported major versions stop the walk; larger headers/minor versions remain explicit uninspected coverage. Declared input and output are bounded without allocating the expanded image. DONT_CARE describes a skipped output range; this report does not claim destination bytes are zero or erased.

The inspector does not combine numbered sparsechunk parts, infer their order, verify payload CRCs, reconstruct filesystems, validate Android Verified Boot, establish bootability/device compatibility or approve deployment. Use regular local images, not physical drives or device routes. Trusted stable paths and a report parent you control remain required. File identity checks and cooperative limits are best-effort defenses, not an OS sandbox, atomic snapshot or hard native I/O deadline. See [security guidance](SECURITY.md).

## Qualification and source

The [standalone qualification contract](docs/QUALIFICATION.md) covers the unchanged 45-method suite, copied-runtime CLI/safeguard checks and exact native skip rules. The [release records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/android-sparse-inspector-v0.1.0) contain actual matrix results and checksums. [Historical validation](docs/VALIDATION.md) remains a historical observation, not a substitute for fresh extracted-package acceptance.

[MIT](LICENSE) covers original authored source, documentation/tests and fictional generators. Python/bundled-library terms and inspected-input rights remain separate. [Provenance](docs/PROVENANCE.md) links primary AOSP references; no upstream implementation, binary or fixture is bundled. Review a deliberate source change before regenerating an unsigned source manifest; a matching manifest alone does not prove trusted authorship, rights or universal secret absence.
