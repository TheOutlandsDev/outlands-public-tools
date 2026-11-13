# Fictional exact-byte preview and separate candidate walkthrough

This guide uses invented source bytes and plans only. It previews first, then
explicitly creates a new separate candidate and independently reads/hashes it.
No source or plan is edited. No candidate is executed, and no real game,
firmware, application or device is patched. Matching byte checks do not establish
format semantics, safety, origin, compatibility or intended runtime behavior.

Use Python 3.12–3.15 without third-party packages. Formal guide evidence uses a
fresh no-pip CPython 3.15.2 environment and external copies of the actual three
runtime/generator files. Assertions must remain enabled. Actual CLI commands use
`-E -s -B` to retain sibling support imports while disabling environment/user
site settings and bytecode writes. The driver itself uses `-I -B`.

From the extracted module folder, save the single Python block below as
`fictional_patch_walkthrough.py` in an existing absolute private directory
outside the source tree. Replace the fictional path with a directory you own;
do not select links/reparse routes, network paths or real binary collections.
The script creates one new private workspace and never deletes prior artifacts.

PowerShell 5.1 or newer:

```powershell
$module = (Get-Location).Path
$privateParent = 'D:\Private-Review'
python -I -B "$privateParent/fictional_patch_walkthrough.py" "$module" "$privateParent"
```

POSIX shell, using an existing owned private directory:

```sh
module="$PWD"
privateParent="$HOME/private-review"
python3 -I -B "$privateParent/fictional_patch_walkthrough.py" "$module" "$privateParent"
```

The fictional source is sixteen bytes, `ORCHARD-DEMO-v1` plus LF. The ordinary
two-edit plan declares six bytes and predicts `ORCHARD-TEST-v2` plus LF. Preview
creates only three report files. Explicit application creates a separate file
and an application receipt. A no-op is valid; adjacent unsorted ranges are valid
and keep their declaration order in the report. Each candidate is checked against
independent expected bytes and SHA-256, without running it.

Four review cases request application but withhold candidates for wrong whole
source hash, wrong size, wrong expected bytes and ranges outside a shorter
selected source. Fifteen refusals check strict JSON/numeric types, range/overlap,
hex/length/count bounds, aliases, existing destinations, output overlap, relative
paths and the 4 MiB source bound. A final instrumented case uses a standard-library
mock only around report writing, after the actual CLI main has created and read
back a candidate. It returns an incomplete error and retains that candidate;
the driver independently verifies the artifact. This is not a real hardware I/O
failure, power-loss simulation or transactional rollback test.

The driver checks exact status/count/error stdout bytes and empty stderr. It
independently recomputes full selected source/plan hashes and both report payload
hashes in every normal manifest. The manifest covers JSON/HTML only; candidates
are verified separately. Reports omit paths and byte payloads, but hashes,
offsets and sizes identify material: omission is not anonymization. Plans contain
actual byte payloads and must be reviewed separately before sharing.

Expected review/incomplete exits are checked internally. The complete driver
exits 0 only when every assertion passes. Input/runtime hashes, exact created
files and absence of bytecode are checked at the end.

## Executable driver

```python
"""Preview and create only fictional bytes; never execute any candidate."""
import copy
import hashlib
import json
import os
from pathlib import Path
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
work = Path(tempfile.mkdtemp(prefix="fictional-byte-plan-", dir=parent)).resolve()
assert work.parent == parent
runtime_names = ("binary_patch_planner.py", "inspection_support.py", "examples/generate.py")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
runtime = {name: digest((module/name).read_bytes()) for name in runtime_names}
outcomes = []

def command(case, script, args, expected_exit, expected_stdout, wire=None):
    before = {p.relative_to(work).as_posix(): digest(p.read_bytes()) for p in work.rglob("*") if p.is_file()}
    invocation = ["-c", *map(str, args)] if script == "-c" else [str(module/script), *map(str, args)]
    result = subprocess.run([sys.executable, "-E", "-s", "-B", *invocation],
                            cwd=work, capture_output=True, timeout=30)
    assert result.returncode == expected_exit and result.stderr == b"", case
    assert json.loads(result.stdout) == expected_stdout, case
    expected_wire = json.dumps(expected_stdout, sort_keys=True) if wire is None else wire
    assert result.stdout == (expected_wire+os.linesep).encode(), case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before == {name: digest((work/name).read_bytes()) for name in before}, case
    outcomes.append({"case": case, "exit_code": result.returncode})

command("create-fictional-bytes-and-plans", "examples/generate.py", ["--output", work/"fixtures"], 0,
        {"status": "FICTIONAL_EXAMPLES_CREATED", "files": 4},
        json.dumps({"status": "FICTIONAL_EXAMPLES_CREATED", "files": 4}))
fixtures = work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"source.bin", "verified-plan.json", "unexpected-plan.json", "overlap-plan.json"}
source_bytes = b"ORCHARD-DEMO-v1\n"; candidate_bytes = b"ORCHARD-TEST-v2\n"
assert (fixtures/"source.bin").read_bytes() == source_bytes and len(source_bytes) == len(candidate_bytes) == 16
plan = json.loads((fixtures/"verified-plan.json").read_bytes())
assert plan == {"schema_version": 1, "source": {"bytes": 16, "sha256": digest(source_bytes)}, "patches": [
    {"offset": 8, "expected_hex": "44454d4f", "replacement_hex": "54455354"},
    {"offset": 13, "expected_hex": "7631", "replacement_hex": "7632"}]}
crafted = work/"crafted"; crafted.mkdir()
plans = {}
plans["wrong-hash.json"] = copy.deepcopy(plan); plans["wrong-hash.json"]["source"]["sha256"] = "0"*64
plans["wrong-size.json"] = copy.deepcopy(plan); plans["wrong-size.json"]["source"]["bytes"] = 17
plans["no-op.json"] = copy.deepcopy(plan)
plans["no-op.json"]["patches"] = [{"offset": 0, "expected_hex": source_bytes.hex(), "replacement_hex": source_bytes.hex()}]
plans["adjacent-unsorted.json"] = copy.deepcopy(plan)
plans["adjacent-unsorted.json"]["patches"] = [
    {"offset": 8, "expected_hex": b"DEMO-v1\n".hex(), "replacement_hex": b"TEST-v2\n".hex()},
    {"offset": 0, "expected_hex": b"ORCHARD-".hex(), "replacement_hex": b"ORCHARD-".hex()}]
plans["boolean-offset.json"] = copy.deepcopy(plan); plans["boolean-offset.json"]["patches"][0]["offset"] = True
plans["outside-plan-range.json"] = copy.deepcopy(plan); plans["outside-plan-range.json"]["patches"][1]["offset"] = 15
plans["hex-whitespace.json"] = copy.deepcopy(plan); plans["hex-whitespace.json"]["patches"][0]["expected_hex"] = "44 54d4f"
plans["unequal-length.json"] = copy.deepcopy(plan); plans["unequal-length.json"]["patches"][0]["replacement_hex"] = "54"
plans["too-many-patches.json"] = copy.deepcopy(plan)
plans["too-many-patches.json"]["patches"] = [copy.deepcopy(plan["patches"][0]) for _ in range(1001)]
for name, value in plans.items():
    (crafted/name).write_bytes((json.dumps(value, indent=2)+"\n").encode())
(crafted/"short-source.bin").write_bytes(b"ORCHARD-")
(crafted/"duplicate-key.json").write_bytes(b'{"schema_version":1,"schema_version":1}')
(crafted/"float-number.json").write_bytes(b'{"schema_version":1.0}')
(crafted/"over-source-bound.bin").write_bytes(b"F"*(4*1024*1024+1))
inputs = {p.relative_to(work).as_posix(): digest(p.read_bytes())
          for folder in (fixtures, crafted) for p in folder.iterdir()}
assert len(inputs) == 17
reports = []; candidates = []; source_hashes_checked = 0

def inspect_case(case, source, selected_plan, report_name, expected_exit, patches, findings=(), expected_candidate=None, apply_name=None):
    global source_hashes_checked
    output = work/report_name
    args = ["--source", source, "--plan", selected_plan, "--output", output]
    if apply_name: args.extend(["--apply-output", work/apply_name])
    applied = bool(apply_name and expected_candidate is not None)
    expected = {"status": "NO_SCOPE_FINDINGS" if expected_exit == 0 else "REVIEW_REQUIRED",
                "patches": len(patches), "findings": len(findings), "application_requested": bool(apply_name),
                "output_created": applied, "output_verified": applied}
    command(case, "binary_patch_planner.py", args, expected_exit, expected)
    assert {p.name for p in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    raw = (output/"report.json").read_bytes(); report = json.loads(raw)
    assert set(report) == {"schema_version", "tool", "scope", "sources", "declared_source", "patches",
                           "declared_patch_bytes", "candidate_sha256", "application", "findings", "coverage_issues", "status"}
    assert report["schema_version"] == 1 and report["tool"] == "Verified Binary Patch Planner"
    assert report["scope"] == "Exact declared equal-length byte replacements in one selected regular file."
    assert report["status"] == expected["status"] and report["coverage_issues"] == []
    actual_plan = json.loads(selected_plan.read_bytes())
    assert report["declared_source"] == actual_plan["source"]
    assert report["declared_patch_bytes"] == sum(len(bytes.fromhex(row["expected_hex"])) for row in actual_plan["patches"])
    expected_sources = []
    for label, path in (("source", source), ("plan", selected_plan)):
        data = path.read_bytes(); expected_sources.append({"id": label, "bytes": len(data), "sha256": digest(data)})
        source_hashes_checked += 1
    assert report["sources"] == expected_sources
    assert report["patches"] == [{"index": i, "offset_bytes": offset, "bytes": count,
        "within_selected_source": within, "expected_bytes_match": match, "changes_bytes": changes}
        for i, offset, count, within, match, changes in patches]
    assert report["findings"] == [{"code": code, "patch_index": index} for code, index in findings]
    assert report["candidate_sha256"] == (digest(expected_candidate) if expected_candidate is not None else None)
    application = {"requested": bool(apply_name), "created": applied, "verified": applied}
    if applied:
        data = (work/apply_name).read_bytes()
        assert data == expected_candidate
        application.update(bytes=len(data), sha256=digest(data), receipt_scope="Separate explicitly selected output file; local filename omitted.")
        assert application["sha256"] == report["candidate_sha256"]
        candidates.append(apply_name)
    elif apply_name:
        assert not os.path.lexists(work/apply_name)
    assert report["application"] == application
    assert all(marker not in raw for marker in (b"ORCHARD", b"expected_hex", b"replacement_hex", str(work).encode(), str(module).encode()))
    payloads = {name: (output/name).read_bytes() for name in ("report.json", "report.html")}
    assert json.loads((output/"MANIFEST.json").read_bytes()) == {"schema_version": 1, "files": [
        {"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(payloads.items())]}
    html = payloads["report.html"].decode()
    assert "Content-Security-Policy" in html and "<script>" not in html and "&quot;schema_version&quot;" in html
    reports.append(report_name)
    return report

clean_rows = [(1, 8, 4, True, True, True), (2, 13, 2, True, True, True)]
preview = inspect_case("preview-default-creates-no-candidate", fixtures/"source.bin", fixtures/"verified-plan.json", "preview-report", 0,
                       clean_rows, expected_candidate=candidate_bytes)
applied = inspect_case("explicit-new-candidate-and-independent-readback", fixtures/"source.bin", fixtures/"verified-plan.json", "applied-report", 0,
                       clean_rows, expected_candidate=candidate_bytes, apply_name="candidate.bin")
normalized = copy.deepcopy(applied); normalized["application"] = preview["application"]
assert normalized == preview
inspect_case("no-op-is-valid-and-reported", fixtures/"source.bin", crafted/"no-op.json", "no-op-report", 0,
             [(1, 0, 16, True, True, False)], expected_candidate=source_bytes, apply_name="no-op-candidate.bin")
inspect_case("adjacent-unsorted-ranges-preserve-declaration-order", fixtures/"source.bin", crafted/"adjacent-unsorted.json", "adjacent-report", 0,
             [(1, 8, 8, True, True, True), (2, 0, 8, True, True, False)], expected_candidate=candidate_bytes)
inspect_case("wrong-whole-source-hash-withholds-request", fixtures/"source.bin", crafted/"wrong-hash.json", "wrong-hash-report", 1,
             clean_rows, [("SOURCE_HASH_MISMATCH", None)], apply_name="withheld-hash.bin")
inspect_case("wrong-source-size-withholds-request", fixtures/"source.bin", crafted/"wrong-size.json", "wrong-size-report", 1,
             clean_rows, [("SOURCE_SIZE_MISMATCH", None)], apply_name="withheld-size.bin")
inspect_case("wrong-expected-bytes-withholds-request", fixtures/"source.bin", fixtures/"unexpected-plan.json", "wrong-bytes-report", 1,
             [(1, 8, 4, True, False, True), (2, 13, 2, True, True, True)],
             [("EXPECTED_BYTES_MISMATCH", 1)], apply_name="withheld-bytes.bin")
inspect_case("short-selected-source-holds-outside-ranges", crafted/"short-source.bin", fixtures/"verified-plan.json", "short-source-report", 1,
             [(1, 8, 4, False, False, True), (2, 13, 2, False, False, True)],
             [("SOURCE_SIZE_MISMATCH", None), ("SOURCE_HASH_MISMATCH", None),
              ("PATCH_OUTSIDE_SELECTED_SOURCE", 1), ("PATCH_OUTSIDE_SELECTED_SOURCE", 2)], apply_name="withheld-short.bin")

def refusal(case, selected_plan, code, source=None, report_name=None, apply_path=None):
    args = ["--source", source or fixtures/"source.bin", "--plan", selected_plan,
            "--output", work/(report_name or case+"-output")]
    if apply_path: args.extend(["--apply-output", apply_path])
    command(case, "binary_patch_planner.py", args, 2, {"status": "INCOMPLETE", "error": code})
refusal("refuse-duplicate-json-key", crafted/"duplicate-key.json", "DUPLICATE_JSON_KEY")
refusal("refuse-floating-point-json", crafted/"float-number.json", "JSON_NUMBER_UNSUPPORTED")
refusal("refuse-boolean-offset", crafted/"boolean-offset.json", "PATCH_OFFSET_INVALID")
refusal("refuse-overlapping-ranges", fixtures/"overlap-plan.json", "PATCH_OVERLAP")
refusal("refuse-outside-declared-plan-range", crafted/"outside-plan-range.json", "PATCH_RANGE_INVALID")
refusal("refuse-hex-whitespace", crafted/"hex-whitespace.json", "PATCH_HEX_INVALID")
refusal("refuse-unequal-replacement-length", crafted/"unequal-length.json", "PATCH_LENGTH_MISMATCH")
refusal("refuse-patch-count-bound", crafted/"too-many-patches.json", "PATCH_COUNT_LIMIT")
refusal("refuse-source-plan-alias", fixtures/"source.bin", "DUPLICATE_INPUT_FILE")
refusal("refuse-existing-report", fixtures/"verified-plan.json", "OUTPUT_EXISTS", report_name="preview-report")
refusal("refuse-existing-candidate", fixtures/"verified-plan.json", "OUTPUT_EXISTS", apply_path=work/"candidate.bin")
refusal("refuse-overlapping-output-destinations", fixtures/"verified-plan.json", "OUTPUT_DESTINATIONS_OVERLAP",
        report_name="same-destination", apply_path=work/"same-destination")
command("refuse-existing-generator-directory", "examples/generate.py", ["--output", fixtures], 2,
        {"status": "INCOMPLETE", "error": "OUTPUT_EXISTS"})
refusal("refuse-relative-source", fixtures/"verified-plan.json", "LOCAL_ABSOLUTE_PATH_REQUIRED", source="relative.bin")
refusal("refuse-source-byte-bound", fixtures/"verified-plan.json", "INPUT_BYTE_LIMIT", source=crafted/"over-source-bound.bin")

# A test-only mock injects a report failure after the actual candidate write and readback.
# This exercises main/run/apply_candidate; it never runs the candidate as a program.
failure_worker = '''import sys
sys.path.insert(0,sys.argv[1])
from unittest.mock import patch
import binary_patch_planner as tool
with patch.object(tool,"write_report",side_effect=OSError("FICTIONAL_REPORT_FAILURE")):
    raise SystemExit(tool.main(sys.argv[2:]))
'''
command("injected-report-failure-leaves-verified-candidate", "-c", [failure_worker, module,
        "--source", fixtures/"source.bin", "--plan", fixtures/"verified-plan.json",
        "--output", work/"failed-report", "--apply-output", work/"retained-after-report-failure.bin"], 2,
        {"status": "INCOMPLETE", "error": "IO_OR_INPUT_ERROR"})
assert not os.path.lexists(work/"failed-report")
assert (work/"retained-after-report-failure.bin").read_bytes() == candidate_bytes
assert digest((work/"retained-after-report-failure.bin").read_bytes()) == digest(candidate_bytes)
candidates.append("retained-after-report-failure.bin")
assert inputs == {name: digest((work/name).read_bytes()) for name in inputs}
assert runtime == {name: digest((module/name).read_bytes()) for name in runtime_names}
expected_files = set(inputs) | set(candidates) | {name+"/"+file for name in reports for file in ("report.json", "report.html", "MANIFEST.json")}
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()} == expected_files
assert len(reports) == 8 and len(candidates) == 3 and len(expected_files) == 44 and source_hashes_checked == 16
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
print(json.dumps({"outcomes": outcomes, "reports_verified": 8, "payload_hashes_verified": 16,
                  "source_and_plan_hashes_checked": 16, "candidate_files_verified": 3, "fixture_files_preserved": 17,
                  "expected_workspace_files": 44, "unexpected_application_files": 0,
                  "preview_and_application_observations_match": True, "withheld_candidates": 4,
                  "injected_report_failure_cases": 1, "verified_candidate_preserved_after_report_failure": True,
                  "bytecode_files": 0, "runtime_bytes_preserved": True,
                  "real_user_binaries_used": False, "candidate_files_executed": False,
                  "game_files_patched": False, "firmware_files_patched": False, "physical_devices_opened": False,
                  "format_semantics_verified": False, "runtime_behavior_verified": False,
                  "transactional_rollback_claimed": False}, sort_keys=True))
```

## Exact expected case outcomes

```json
[
  {
    "case": "create-fictional-bytes-and-plans",
    "exit_code": 0
  },
  {
    "case": "preview-default-creates-no-candidate",
    "exit_code": 0
  },
  {
    "case": "explicit-new-candidate-and-independent-readback",
    "exit_code": 0
  },
  {
    "case": "no-op-is-valid-and-reported",
    "exit_code": 0
  },
  {
    "case": "adjacent-unsorted-ranges-preserve-declaration-order",
    "exit_code": 0
  },
  {
    "case": "wrong-whole-source-hash-withholds-request",
    "exit_code": 1
  },
  {
    "case": "wrong-source-size-withholds-request",
    "exit_code": 1
  },
  {
    "case": "wrong-expected-bytes-withholds-request",
    "exit_code": 1
  },
  {
    "case": "short-selected-source-holds-outside-ranges",
    "exit_code": 1
  },
  {
    "case": "refuse-duplicate-json-key",
    "exit_code": 2
  },
  {
    "case": "refuse-floating-point-json",
    "exit_code": 2
  },
  {
    "case": "refuse-boolean-offset",
    "exit_code": 2
  },
  {
    "case": "refuse-overlapping-ranges",
    "exit_code": 2
  },
  {
    "case": "refuse-outside-declared-plan-range",
    "exit_code": 2
  },
  {
    "case": "refuse-hex-whitespace",
    "exit_code": 2
  },
  {
    "case": "refuse-unequal-replacement-length",
    "exit_code": 2
  },
  {
    "case": "refuse-patch-count-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-source-plan-alias",
    "exit_code": 2
  },
  {
    "case": "refuse-existing-report",
    "exit_code": 2
  },
  {
    "case": "refuse-existing-candidate",
    "exit_code": 2
  },
  {
    "case": "refuse-overlapping-output-destinations",
    "exit_code": 2
  },
  {
    "case": "refuse-existing-generator-directory",
    "exit_code": 2
  },
  {
    "case": "refuse-relative-source",
    "exit_code": 2
  },
  {
    "case": "refuse-source-byte-bound",
    "exit_code": 2
  },
  {
    "case": "injected-report-failure-leaves-verified-candidate",
    "exit_code": 2
  }
]
```

The summary records 25 cases: five exit 0, four review exit 1 and sixteen
incomplete exit 2 outcomes. Eight normal report manifests cover sixteen report
payloads. Sixteen source/plan hash observations, three candidate readbacks,
seventeen preserved fictional fixtures and 44 exact input/report/candidate files
are checked. Four requested candidates remain withheld. The injected late failure
leaves one independently verified candidate without a normal report.

All eight scope flags remain false: real user binaries, candidate execution,
game/firmware patching, physical device access, format semantics, runtime behavior
and transactional rollback. Application readback is byte-consistency evidence,
not proof of safe behavior or durable storage. Unsigned hashes/receipts do not
prove origin or redistribution rights.

Use trusted stable inputs and owned parents. The tool is not an OS sandbox,
atomic snapshot, hard I/O deadline or transaction across candidate/report. A real
write/readback/report failure can leave partial or complete new artifacts. Keep
them private, review the cause and select new destinations for a retry. There is
no automatic overwrite, cleanup or rollback. Read [FORMAT.md](docs/FORMAT.md),
[QUALIFICATION.md](docs/QUALIFICATION.md) and the unchanged historical
[validation](docs/VALIDATION.md) for the exact boundaries.
