# Fictional saved APK-metadata walkthrough

Extract the [APK Metadata Report Diff 0.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/apk-report-diff-v0.1.0), verify SHA256SUMS and supply ordinary CPython 3.12, 3.13, 3.14 or 3.15. Qualification selects 3.15.2 for that minor. The inspector uses only Python's standard library for a saved-text workload; this guide selects no APKs. The ZIP contains no interpreter, AAPT2, SDK, APK, capture or generated report. No installation or administrative privileges are required.

## Choose a private workspace

Keep unpacked source and an existing private work parent separate. Copy the Python block below into a new file named `fictional_apk_text_walkthrough.py` outside the source directory. Substitute your actual absolute paths in these explicitly fictional PowerShell examples:

```powershell
$module = 'D:\Source\apk-report-diff-0.1.0'
$privateWork = 'D:\Private\apk-text-work'
python --version
python -E -s -B .\fictional_apk_text_walkthrough.py "$module" "$privateWork"
```

On Ubuntu, use your actual absolute paths:

```sh
python3 --version
python3 -E -s -B ./fictional_apk_text_walkthrough.py "/absolute/source/apk-report-diff-0.1.0" "/absolute/private/apk-text-work"
```

The private parent must exist. Every run creates a new canonical `fictional-apk-text-*` subdirectory and retains generated inputs/reports for review. Twelve small text fixtures are authored, including an overlong-line refusal fixture. They are invented saved declarations, not captures from an APK or device. The script requires assertions; `-O` is refused. `-E -s -B` ignores Python environment overrides, disables user-site packages and prevents bytecode writes while allowing sibling imports from the selected source folder.

## Execute the complete walkthrough

The block invokes the actual fictional generator and comparison CLI. It checks equal declarations, six selected changes, private defaults, optional details, unknown-row holds, duplicate library identities, common-library relative order, different/unresolved package identities and escaped HTML. It then verifies six controlled refusals. Report modes are checked separately: six default reports and four reports with details enabled. Removing only opt-in literal details from the detailed six-change report must yield exactly the default report.

The checks independently hash twenty selected-text source observations and ten report manifests. These are text-byte and report consistency checks, not APK hashes, capture authenticity or complete manifest validation. The script never opens an APK, invokes AAPT2, performs capture, installs an SDK/app or connects to a device. Every fixture comes from the authored text shown by the generator and script.

```python
"""Compare only the fictional saved badging text authored below."""
from collections import Counter
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
work = Path(tempfile.mkdtemp(prefix="fictional-apk-text-", dir=parent)).resolve()
assert work.parent == parent
runtime_names = ("apk_report_diff.py", "inspection_support.py", "examples/generate.py")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
runtime = {name: digest((module/name).read_bytes()) for name in runtime_names}
outcomes = []

def command(case, script, args, expected_exit, expected_stdout, wire=None):
    before = {p.relative_to(work).as_posix(): digest(p.read_bytes()) for p in work.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-E", "-s", "-B", str(module/script), *map(str, args)],
                            cwd=work, capture_output=True, timeout=30)
    assert result.returncode == expected_exit and result.stderr == b"", case
    assert json.loads(result.stdout) == expected_stdout, case
    expected_wire = json.dumps(expected_stdout, sort_keys=True) if wire is None else wire
    assert result.stdout == (expected_wire+os.linesep).encode(), case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before == {name: digest((work/name).read_bytes()) for name in before}, case
    outcomes.append({"case": case, "exit_code": result.returncode})

command("create-fictional-saved-text", "examples/generate.py", ["--output", work/"fixtures"], 0,
        {"status": "FICTIONAL_EXAMPLES_CREATED", "files": 5},
        json.dumps({"status": "FICTIONAL_EXAMPLES_CREATED", "files": 5}))
fixtures = work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"before.txt", "same.txt", "after.txt", "unsupported.txt", "duplicate.txt"}
before_text = (fixtures/"before.txt").read_text(encoding="utf-8")
after_text = (fixtures/"after.txt").read_text(encoding="utf-8")
crafted = work/"crafted"; crafted.mkdir()
package = "package: name='example.ledger' versionCode='7' versionName='fixed'\n"
(crafted/"order-before.txt").write_bytes((package+"uses-library:'example.alpha'\nuses-library-not-required:'example.beta'\n").encode())
(crafted/"order-after.txt").write_bytes((package+"uses-library-not-required:'example.beta'\nuses-library:'example.alpha'\n").encode())
(crafted/"different-package.txt").write_bytes(after_text.replace("example.orchard", "example.other").encode())
(crafted/"ambiguous-package.txt").write_bytes((after_text+after_text.splitlines()[0]+"\n").encode())
(crafted/"escaped-version.txt").write_bytes(after_text.replace("versionName='2.0'", "versionName='</pre><script>fiction</script>'").encode())
(crafted/"ignored-label.txt").write_bytes(before_text.replace("Fictional Orchard", "ignored-private-label").encode())
(crafted/"over-line-limit.txt").write_bytes(b"X"*8193)
inputs = {p.relative_to(work).as_posix(): digest(p.read_bytes())
          for folder in (fixtures, crafted) for p in folder.iterdir()}
assert len(inputs) == 12
reports = []
source_hashes_checked = 0
mode_counts = {"default": 0, "included": 0}


def compare_case(case, before, after, report_name, expected_exit, fields, holds, coverage, identity, details=False):
    global source_hashes_checked
    output = work/report_name
    expected = {"status": "NO_SCOPE_FINDINGS" if expected_exit == 0 else "REVIEW_REQUIRED",
                "changes": len(fields), "held_comparisons": len(holds), "coverage_issues": len(coverage)}
    args = ["--before", before, "--after", after, "--output", output]
    if details: args.append("--include-details")
    command(case, "apk_report_diff.py", args, expected_exit, expected)
    assert {p.name for p in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    raw = (output/"report.json").read_bytes(); report = json.loads(raw)
    assert report["status"] == expected["status"] and report["details_included"] is details
    assert report["package_identity"] == identity
    assert Counter(row["field"] for row in report["changes"]) == Counter(fields)
    assert Counter(row["reason"] for row in report["held_comparisons"]) == Counter(holds)
    assert Counter(row["code"] for row in report["coverage_issues"]) == Counter(coverage)
    expected_sources = []
    for label, path in (("before", before), ("after", after)):
        source = path.read_bytes()
        expected_sources.append({"id": label, "bytes": len(source), "sha256": digest(source)})
        source_hashes_checked += 1
    assert report["sources"] == expected_sources
    if identity == "different_declared_names":
        assert report["findings"] == [{"code": "PACKAGE_IDENTITY_CHANGED"}]
    else:
        assert report["findings"] == ([{"code": "DECLARED_METADATA_CHANGED"}] if fields else [])
    if details:
        assert "declared_packages" in report and all("before" in row and "after" in row for row in report["changes"])
    else:
        assert "declared_packages" not in report
        assert all(not {"before", "after", "declared_identity"} & row.keys() for row in report["changes"])
        assert all(marker not in raw for marker in (b"example.orchard", b"example.alpha", b"example.beta", b"example.gamma", b"example.other", b"example.ledger"))
    assert all(marker not in raw for marker in (b"Fictional Orchard", b"ignored-private-label", b"fictional-only"))
    payloads = {name: (output/name).read_bytes() for name in ("report.json", "report.html")}
    assert json.loads((output/"MANIFEST.json").read_bytes()) == {"schema_version": 1, "files": [
        {"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(payloads.items())]}
    html = payloads["report.html"].decode()
    assert "Content-Security-Policy" in html and "<script>" not in html
    assert str(work).encode() not in raw
    mode_counts["included" if details else "default"] += 1
    reports.append(report_name)
    return report, html

same = "same_declared_name"
six = ["version_code", "version_name", "target_sdk"]+["declared_requirement"]*3
compare_case("equal-saved-declarations", fixtures/"before.txt", fixtures/"same.txt", "equal-report", 0, [], [], [], same)
default, _ = compare_case("six-changes-private-default", fixtures/"before.txt", fixtures/"after.txt", "changed-report", 1,
                          six, [], [], same)
detailed, _ = compare_case("six-changes-opt-in-details", fixtures/"before.txt", fixtures/"after.txt", "details-report", 1,
                           six, [], [], same, True)
assert detailed["declared_packages"] == {"before": "example.orchard", "after": "example.orchard"}
assert {row["field"]: (row["before"], row["after"]) for row in detailed["changes"] if row["entity_id"] == "package-0001"} == {
    "version_code": ("1", "2"), "version_name": ("1.0", "2.0"), "target_sdk": ("34", "35")}
assert {row["declared_identity"]: (row["before"], row["after"]) for row in detailed["changes"] if row["field"] == "declared_requirement"} == {
    "example.alpha": ("required", None), "example.beta": ("optional", "required"), "example.gamma": (None, "optional")}
normalized = copy.deepcopy(detailed); normalized["details_included"] = False; normalized.pop("declared_packages")
for row in normalized["changes"]:
    for key in ("before", "after", "declared_identity"): row.pop(key, None)
assert normalized == default
unknown, _ = compare_case("unknown-row-holds-unmatched-claims", fixtures/"before.txt", fixtures/"unsupported.txt", "unknown-report", 1,
                         ["version_code", "version_name", "target_sdk"]+["declared_requirement"]*2,
                         ["UNIDENTIFIED_OPPOSITE_ROWS"]*2+["INCOMPLETE_OR_AMBIGUOUS_LIBRARY_ORDER"],
                         ["UNSUPPORTED_ROW"], same, True)
assert {row.get("field") for row in unknown["held_comparisons"] if row["entity_id"] == "package-0001"} == {"max_sdk"}
compare_case("duplicate-library-is-held", fixtures/"before.txt", fixtures/"duplicate.txt", "duplicate-report", 1,
             ["version_code", "version_name", "target_sdk"]+["declared_requirement"]*2,
             ["AMBIGUOUS_LIBRARY_IDENTITY", "INCOMPLETE_OR_AMBIGUOUS_LIBRARY_ORDER"], ["AMBIGUOUS_LIBRARY_ROWS"], same)
order, _ = compare_case("relative-common-library-order", crafted/"order-before.txt", crafted/"order-after.txt", "order-report", 1,
                        ["relative_common_order"], [], [], same, True)
assert order["changes"][0]["before"] == ["example.alpha", "example.beta"]
assert order["changes"][0]["after"] == ["example.beta", "example.alpha"]
compare_case("different-package-holds-other-fields", fixtures/"before.txt", crafted/"different-package.txt", "identity-report", 1,
             [], ["DIFFERENT_PACKAGES_NOT_COMPARED"], [], "different_declared_names")
compare_case("ambiguous-package-is-unresolved", fixtures/"before.txt", crafted/"ambiguous-package.txt", "ambiguous-report", 1,
             [], ["PACKAGE_IDENTITY_UNRESOLVED"], ["AMBIGUOUS_PACKAGE_ROWS"], "unresolved")
escaped, html = compare_case("opt-in-version-text-is-html-escaped", fixtures/"before.txt", crafted/"escaped-version.txt", "escaped-report", 1,
                            six, [], [], same, True)
assert next(row["after"] for row in escaped["changes"] if row["field"] == "version_name") == "</pre><script>fiction</script>"
assert "&lt;script&gt;" in html
compare_case("ignored-label-change-is-not-compared", fixtures/"before.txt", crafted/"ignored-label.txt", "ignored-report", 0,
             [], [], [], same)

def refusal(case, script, args, code):
    command(case, script, args, 2, {"status": "INCOMPLETE", "error": code})
refusal("refuse-same-input-alias", "apk_report_diff.py", ["--before", fixtures/"before.txt", "--after", fixtures/"before.txt",
        "--output", work/"alias-report"], "DUPLICATE_INPUT_FILE")
refusal("refuse-existing-report", "apk_report_diff.py", ["--before", fixtures/"before.txt", "--after", fixtures/"after.txt",
        "--output", work/"changed-report"], "OUTPUT_EXISTS")
refusal("refuse-existing-generator-directory", "examples/generate.py", ["--output", fixtures], "OUTPUT_EXISTS")
refusal("refuse-relative-input", "apk_report_diff.py", ["--before", "relative.txt", "--after", fixtures/"after.txt",
        "--output", work/"relative-report"], "LOCAL_ABSOLUTE_PATH_REQUIRED")
refusal("refuse-missing-arguments", "apk_report_diff.py", [], "ARGUMENTS_INVALID")
refusal("refuse-overlong-text-line", "apk_report_diff.py", ["--before", fixtures/"before.txt", "--after", crafted/"over-line-limit.txt",
        "--output", work/"limit-report"], "TEXT_LINE_LIMIT")
assert inputs == {name: digest((work/name).read_bytes()) for name in inputs}
assert runtime == {name: digest((module/name).read_bytes()) for name in runtime_names}
expected_files = set(inputs) | {name+"/"+file for name in reports for file in ("report.json", "report.html", "MANIFEST.json")}
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()} == expected_files
assert len(reports) == 10 and len(expected_files) == 42 and source_hashes_checked == 20
assert mode_counts == {"default": 6, "included": 4}
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
print(json.dumps({"outcomes": outcomes, "reports_verified": 10, "payload_hashes_verified": 20,
                  "saved_text_source_hashes_checked": 20, "fixture_files_preserved": 12,
                  "expected_workspace_files": 42, "unexpected_application_files": 0,
                  "details_mode_counts": mode_counts, "details_do_not_change_comparison": True,
                  "bytecode_files": 0, "runtime_bytes_preserved": True,
                  "apk_files_opened": False, "aapt2_invoked": False, "capture_performed": False,
                  "sdk_installed": False, "real_packages_or_devices_used": False}, sort_keys=True))
```

Expected outcomes, in execution order:

```json
[
  {
    "case": "create-fictional-saved-text",
    "exit_code": 0
  },
  {
    "case": "equal-saved-declarations",
    "exit_code": 0
  },
  {
    "case": "six-changes-private-default",
    "exit_code": 1
  },
  {
    "case": "six-changes-opt-in-details",
    "exit_code": 1
  },
  {
    "case": "unknown-row-holds-unmatched-claims",
    "exit_code": 1
  },
  {
    "case": "duplicate-library-is-held",
    "exit_code": 1
  },
  {
    "case": "relative-common-library-order",
    "exit_code": 1
  },
  {
    "case": "different-package-holds-other-fields",
    "exit_code": 1
  },
  {
    "case": "ambiguous-package-is-unresolved",
    "exit_code": 1
  },
  {
    "case": "opt-in-version-text-is-html-escaped",
    "exit_code": 1
  },
  {
    "case": "ignored-label-change-is-not-compared",
    "exit_code": 0
  },
  {
    "case": "refuse-same-input-alias",
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
    "case": "refuse-overlong-text-line",
    "exit_code": 2
  }
]
```

The final JSON also reports ten report directories, twenty report-file hashes, twenty saved-text source-hash checks and twelve unchanged fixture files. Exactly 42 files exist below the generated work directory: twelve inputs and ten three-file reports. Three cases return 0, eight return expected review status 1, and six return expected incomplete/refusal status 2. The walkthrough itself exits 0 only when every expected outcome and invariant matches.

A failed assertion means the walkthrough was not accepted; retain the private files for diagnosis instead of changing an expected result to force a pass. The full status line, host-normal line ending and empty stderr are checked for each invocation. Source filenames and private paths do not appear in status output. Every input and previously created report remains byte-identical after later comparisons/refusals.

## Understand changes and holds

The generated before/after pair has six changes: version code, version name, target SDK, a removed library declaration, an added library declaration and a required/optional requirement change. The values remain strings. No upgrade ordering, effective SDK inheritance or class-loader compatibility is inferred. The `platformBuildVersionCode` example is recognized but discarded rather than compared.

An unknown row leaves supported matched declarations comparable while holding unmatched claims and common-library order. A duplicate library identity is held even when repeated values agree; no first/last declaration wins. Different package names hold all remaining comparison; an ambiguous package declaration leaves identity unresolved. A held comparison does not mean unchanged. The relative-order case observes common unique library declaration order, not runtime resolution.

An application-label-only change produces no supported change, because that row family is counted and discarded. This is an explicit scope boundary, not label validation or a completeness check. Raw unsupported rows and application labels remain absent even with details enabled. The escaped-version example is a supported literal string that becomes visible only through opt-in details; its JSON value is preserved and static HTML escapes the script-like text.

## Read and protect reports

A complete report has `report.json`, escaped static `report.html` and `MANIFEST.json`. Open HTML locally or consume JSON. The unsigned manifest hashes the two report files; it checks byte consistency, not authenticity. Each source record hashes the selected saved text bytes, not an APK or the quality of a capture. A matching source hash cannot establish that a producer ran successfully, that a capture is complete or that it represents an authorized app.

Default reports omit literal package/version/SDK/library values. `--include-details` includes supported values and package/library identities. `details_included` is true only for requested detailed reports; it is not globally false. Raw unknown rows and ignored application labels are never included. Omission is not anonymization: source hashes, counts, order and field-presence patterns can identify material. Keep all captures and reports private until fully reviewed. Static HTML uses escaped text, a restrictive CSP and no scripts or remote assets.

`NO_SCOPE_FINDINGS` means no selected change or coverage issue was observed in the documented saved-text subset. `REVIEW_REQUIRED` includes changes, ambiguity or unsupported coverage. `INCOMPLETE` is a controlled argument/path/bounds/I/O result, with no successful report promised. These statuses do not establish permission risk, malware absence, signing, installability, compatibility, full manifest validity or device behavior.

## Compare authorized saved text

After reading [the exact grammar and limits](docs/FORMAT.md), select two distinct stable saved-text files you are permitted to inspect:

```text
python -E -s -B apk_report_diff.py --before ABSOLUTE_BEFORE_TEXT --after ABSOLUTE_AFTER_TEXT --output ABSOLUTE_NEW_REPORT_DIRECTORY
```

Add `--include-details` only when the private report needs the supported values and you will review them before sharing. Keep `apk_report_diff.py`, `inspection_support.py` and the example subfolder together. Use `python3` where appropriate. Each report directory must be new and its parent must exist. Inputs must be distinct regular files; same-file/hardlink aliases, linked/reparse routes, unsupported device/UNC routes, alternate streams, traversal and detected changes are refused.

The text grammar is a limited case-sensitive single-line subset. UTF-8 may include a BOM and LF/CRLF; bare CR, unsupported controls, long lines and declared bounds are refused. No shell expansion, quote repair, XML-entity parsing or complete AAPT2 grammar is inferred. Missing SDK rows mean unspecified in the selected text, not an inherited Android default. Output errors can leave partial new directories; resolve the cause and choose a fresh name. No existing input/report is overwritten.

Trusted stable local paths and output parents remain required. Sampled file identity checks and cooperative bounds are not hostile-filesystem isolation, atomic snapshots or hard native I/O deadlines. The optional [capture guidance](docs/CAPTURE.md) describes a separate manual action using an existing trusted external tool; it is retained unchanged and is not executed by this walkthrough, inspector or qualification. No live producer/SDK/APK acceptance is claimed.

## Qualification, source and rights

The [standalone qualification contract](docs/QUALIFICATION.md) covers all 61 preserved original methods, copied-runtime CLI/safeguard checks and finite native skip rules. [Release records](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/apk-report-diff-v0.1.0) provide actual matrix outcomes and checksums. [Historical validation](docs/VALIDATION.md) remains historical evidence, not a substitute for fresh source-archive acceptance.

[MIT](LICENSE) covers original source, authored documentation/tests and fictional generators. Python/bundled-library terms, external producer terms and inspected-input rights remain separate. [Provenance](docs/PROVENANCE.md) links primary background; no AAPT2/AOSP implementation or captured APK content is bundled. Deliberately review source changes before regenerating an unsigned source manifest. Matching inventory hashes alone do not establish trusted authorship, rights or universal secret absence.
