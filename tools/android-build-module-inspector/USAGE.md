# Fictional saved build-declaration walkthrough

This guide runs the actual copied Python CLI against invented BP/Make text and
wanted-name lists. It never evaluates a build file, runs Make/Soong, follows an
include, compiles a module or opens a device. A literal declaration is an
observation; an unseen request does not prove absence from an effective build.

Use Python 3.12–3.15, without third-party packages. Formal guide evidence uses a
fresh no-pip CPython 3.15.2 environment and copies the three real runtime/generator
files to an external owned location. Assertions must remain enabled. The CLI
uses `-E -s -B` so its sibling support module is available while environment/user
site settings and bytecode writes are disabled. The guide driver uses `-I -B`.

From the extracted module folder, save the single Python block below as
`fictional_build_walkthrough.py` in an existing absolute private directory
outside the source tree. Set the placeholders to directories you control; do
not use a build tree, link/reparse route, network path or shared output parent.
The script creates one new private workspace and never deletes prior evidence.

PowerShell 5.1 or newer (the private path is fictional and must be replaced):

```powershell
$module = (Get-Location).Path
$privateParent = 'D:\Private-Review'
python -I -B "$privateParent/fictional_build_walkthrough.py" "$module" "$privateParent"
```

POSIX shell, using an existing owned private directory:

```sh
module="$PWD"
privateParent="$HOME/private-review"
python3 -I -B "$privateParent/fictional_build_walkthrough.py" "$module" "$privateParent"
```

The first case creates five fictional inputs. Ten completed inspections verify
exact JSON fields, declaration identities/holds, requested states, coverage and
fixed stdout bytes with empty stderr. The detailed/default clean pair must differ
only by opt-in names/kinds and its mode flag. Both modes omit discarded values
and filenames; default omission is not anonymization because hashes, positions,
counts and structure remain. HTML escaping and its script-free policy are checked.

Each report's source lengths/SHA-256 are independently recomputed from selected
text bytes, and each manifest is independently compared to both report payloads.
These hashes are not build-output hashes or authenticity proof. The script
checks unchanged inputs/runtime bytes, exact created files and no bytecode.
Seven controlled refusals test token bounds, aliases, existing outputs, relative
inputs, missing build inputs and invalid requested names. Expected exit 1 and 2
results are checked internally; the complete driver exits 0 only if all checks pass.

## Executable driver

```python
"""Inspect only fictional saved declarations; never evaluate their build text."""
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
work = Path(tempfile.mkdtemp(prefix="fictional-build-text-", dir=parent)).resolve()
assert work.parent == parent
runtime_names = ("build_module_inspector.py", "inspection_support.py", "examples/generate.py")
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

command("create-fictional-build-text", "examples/generate.py", ["--output", work/"fixtures"], 0,
        {"status": "FICTIONAL_EXAMPLES_CREATED", "files": 5},
        json.dumps({"status": "FICTIONAL_EXAMPLES_CREATED", "files": 5}))
fixtures = work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"clean.bp", "clean.mk", "review.bp", "wanted.txt", "wanted-unseen.txt"}
crafted = work/"crafted"; crafted.mkdir()
texts = {
    "unsupported.bp": 'cc_library { name: "example.visible", }\nnames = ["not-evaluated"]\ncc_library { name: "example.hidden", }\n',
    "wanted-visible.txt": "example.visible\nexample.hidden\n",
    "nested.bp": 'cc_library { name: "example.outer", target: { android: { name: "example.nested", }, }, srcs: ["PRIVATE_DISCARDED_SENTINEL</pre><script>fiction</script>"], }\n',
    "wanted-nested.txt": "example.outer\nexample.nested\n",
    "duplicate-property.bp": 'cc_library { name: "example.held", enabled: true, enabled: false, }\n',
    "wanted-held.txt": "example.held\nexample.unseen\n",
    "unknown.mk": "include $(CLEAR_VARS)\nLOCAL_MODULE := example.local\ninclude private-unfollowed.mk\ninclude $(BUILD_SHARED_LIBRARY)\n",
    "wanted-local.txt": "example.local\nexample.unseen\n",
    "directive.mk": "include $(CLEAR_VARS)\nLOCAL_MODULE := example.preceding\nifeq (yes,yes)\ninclude $(BUILD_SHARED_LIBRARY)\ninclude $(CLEAR_VARS)\nLOCAL_MODULE := example.later\ninclude $(BUILD_SHARED_LIBRARY)\nendif\n",
    "wanted-preceding.txt": "example.preceding\nexample.later\n",
    "duplicate-wanted.txt": "example.alpha\nexample.alpha\nexample.unseen\n",
    "token-bound.bp": "a a a a a a a a a a\n"*4001,
    "invalid-wanted.txt": "name with spaces\n",
}
for name, text in texts.items():
    (crafted/name).write_bytes(text.encode("utf-8"))
inputs = {p.relative_to(work).as_posix(): digest(p.read_bytes())
          for folder in (fixtures, crafted) for p in folder.iterdir()}
assert len(inputs) == 18
reports = []
source_hashes_checked = 0
mode_counts = {"default": 0, "included": 0}

def inspect_case(case, selected, wanted, report_name, expected_exit, declarations, requested,
                 findings=(), coverage=(), uncertain=False, ignored=0, repeated=(), details=False):
    global source_hashes_checked
    output = work/report_name
    expected = {"status": "NO_SCOPE_FINDINGS" if expected_exit == 0 else "REVIEW_REQUIRED",
                "declarations": len(declarations), "repeated_names": len(repeated),
                "findings": len(findings), "coverage_issues": len(coverage)}
    args = []
    for syntax, path in selected:
        args.extend(["--"+syntax, path])
    args.extend(["--wanted", wanted, "--output", output])
    if details: args.append("--include-details")
    command(case, "build_module_inspector.py", args, expected_exit, expected)
    assert {p.name for p in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    raw = (output/"report.json").read_bytes(); report = json.loads(raw)
    assert set(report) == {"schema_version", "tool", "scope", "details_included", "sources", "declarations",
                           "repeated_names", "wanted", "findings", "coverage_issues",
                           "unresolved_identity_or_scope", "ignored_make_rows", "status"}
    assert report["schema_version"] == 1 and report["tool"] == "Android Build Module Declaration Inspector"
    assert report["scope"] == "Literal declarations in explicitly selected build text; no build, namespace or expression evaluation."
    assert report["status"] == expected["status"] and report["details_included"] is details
    assert report["unresolved_identity_or_scope"] is uncertain and report["ignored_make_rows"] == ignored
    expected_sources = []
    for index, (syntax, path) in enumerate([*selected, ("wanted", wanted)], 1):
        source = path.read_bytes()
        expected_sources.append({"id": f"input-{index:04d}", "bytes": len(source), "sha256": digest(source), "syntax": syntax})
        source_hashes_checked += 1
    assert report["sources"] == expected_sources
    expected_declarations = []
    for index, (source, line, syntax, known, held, name, kind) in enumerate(declarations, 1):
        row = {"id": f"declaration-{index:04d}", "source": f"input-{source:04d}", "line": line,
               "syntax": syntax, "identity_known": known, "held": held}
        if details: row.update(declared_name=name, module_kind=kind)
        expected_declarations.append(row)
    assert report["declarations"] == expected_declarations
    expected_requested = []
    for index, (name, state, entries) in enumerate(requested, 1):
        row = {"id": f"wanted-{index:04d}", "state": state,
               "declarations": [f"declaration-{i:04d}" for i in entries]}
        if details: row["declared_name"] = name
        expected_requested.append(row)
    assert report["wanted"] == expected_requested
    expected_repeated = []
    for index, (name, entries) in enumerate(repeated, 1):
        row = {"id": f"repeated-{index:04d}", "declarations": [f"declaration-{i:04d}" for i in entries], "count": len(entries)}
        if details: row["declared_name"] = name
        expected_repeated.append(row)
    assert report["repeated_names"] == expected_repeated
    assert report["findings"] == [{"code": code} for code in findings]
    assert report["coverage_issues"] == [{"code": code, "source": f"input-{source:04d}", "line": line}
                                           for code, source, line in coverage]
    if not details:
        assert b"example." not in raw and b"cc_library" not in raw and b"BUILD_SHARED_LIBRARY" not in raw
    assert all(marker not in raw for marker in (b"PRIVATE_DISCARDED_SENTINEL", b"private-unfollowed.mk", b"invented.cpp", b"Invented.java", b"not-evaluated"))
    assert str(work).encode() not in raw and str(module).encode() not in raw
    payloads = {name: (output/name).read_bytes() for name in ("report.json", "report.html")}
    assert json.loads((output/"MANIFEST.json").read_bytes()) == {"schema_version": 1, "files": [
        {"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(payloads.items())]}
    html = payloads["report.html"].decode()
    assert "Content-Security-Policy" in html and "<script>" not in html and "&quot;schema_version&quot;" in html
    mode_counts["included" if details else "default"] += 1
    reports.append(report_name)
    return report

once = "observed_once"; held = "observed_held"; incomplete = "held_incomplete_scope"
not_seen = "not_observed_selected_supported_scope"
clean_declarations = [(1, 2, "bp", True, False, "example.alpha", "cc_library"),
                      (1, 7, "bp", True, False, "example.beta", "java_library"),
                      (2, 3, "mk", True, False, "example.gamma", "BUILD_SHARED_LIBRARY")]
clean_requests = [("example.alpha", once, [1]), ("example.beta", once, [2]), ("example.gamma", once, [3])]
clean_selected = [("bp", fixtures/"clean.bp"), ("mk", fixtures/"clean.mk")]
default = inspect_case("literal-bp-mk-private-default", clean_selected, fixtures/"wanted.txt", "clean-report", 0,
                       clean_declarations, clean_requests, ignored=2)
detailed = inspect_case("literal-bp-mk-opt-in-details", clean_selected, fixtures/"wanted.txt", "details-report", 0,
                        clean_declarations, clean_requests, ignored=2, details=True)
normalized = copy.deepcopy(detailed); normalized["details_included"] = False
for group in ("declarations", "repeated_names", "wanted"):
    for row in normalized[group]:
        for key in ("declared_name", "module_kind"): row.pop(key, None)
assert normalized == default
inspect_case("repeated-names-and-dynamic-identity-hold", [("bp", fixtures/"review.bp")], fixtures/"wanted-unseen.txt", "repeated-report", 1,
             [(1, 1, "bp", True, False, "example.alpha", "cc_library"), (1, 2, "bp", True, False, "example.alpha", "cc_library"),
              (1, 3, "bp", False, True, None, "cc_library")],
             [("example.alpha", "observed_multiple", [1, 2]), ("example.unseen", incomplete, [])],
             findings=["REPEATED_DECLARED_NAME_OBSERVED"], coverage=[("BP_NAME_UNRESOLVED", 1, 3)],
             uncertain=True, repeated=[("example.alpha", [1, 2])], details=True)
inspect_case("unseen-in-selected-supported-scope", [("bp", fixtures/"clean.bp")], fixtures/"wanted-unseen.txt", "unseen-report", 1,
             clean_declarations[:2], [("example.alpha", once, [1]), ("example.unseen", not_seen, [])],
             findings=["WANTED_NAME_NOT_OBSERVED"])
inspect_case("unsupported-top-level-stops-file", [("bp", crafted/"unsupported.bp")], crafted/"wanted-visible.txt", "stopped-bp-report", 1,
             [(1, 1, "bp", True, False, "example.visible", "cc_library")],
             [("example.visible", once, [1]), ("example.hidden", incomplete, [])],
             coverage=[("BP_TOPLEVEL_REMAINDER_UNINSPECTED", 1, 2)], uncertain=True, details=True)
inspect_case("nested-name-is-not-direct-module-name", [("bp", crafted/"nested.bp")], crafted/"wanted-nested.txt", "nested-report", 1,
             [(1, 1, "bp", True, False, "example.outer", "cc_library")],
             [("example.outer", once, [1]), ("example.nested", not_seen, [])],
             findings=["WANTED_NAME_NOT_OBSERVED"], details=True)
inspect_case("duplicate-direct-property-holds-declaration", [("bp", crafted/"duplicate-property.bp")], crafted/"wanted-held.txt", "duplicate-property-report", 1,
             [(1, 1, "bp", True, True, "example.held", "cc_library")],
             [("example.held", held, [1]), ("example.unseen", incomplete, [])],
             coverage=[("BP_DUPLICATE_DIRECT_PROPERTY", 1, 1)], uncertain=True)
inspect_case("unknown-make-include-stays-unfollowed", [("mk", crafted/"unknown.mk")], crafted/"wanted-local.txt", "unknown-include-report", 1,
             [(1, 1, "mk", True, True, "example.local", "BUILD_SHARED_LIBRARY")],
             [("example.local", held, [1]), ("example.unseen", incomplete, [])],
             coverage=[("MK_INCLUDE_UNFOLLOWED", 1, 3)], uncertain=True, details=True)
inspect_case("make-directive-stops-remainder", [("mk", crafted/"directive.mk")], crafted/"wanted-preceding.txt", "stopped-mk-report", 1,
             [(1, 1, "mk", True, True, "example.preceding", "unresolved")],
             [("example.preceding", held, [1]), ("example.later", incomplete, [])],
             coverage=[("MK_DIRECTIVE_REMAINDER_UNINSPECTED", 1, 3)], uncertain=True)
inspect_case("duplicate-wanted-name-is-recorded-once", [("bp", fixtures/"clean.bp")], crafted/"duplicate-wanted.txt", "duplicate-wanted-report", 1,
             clean_declarations[:2], [("example.alpha", once, [1]), ("example.unseen", not_seen, [])],
             findings=["WANTED_NAME_NOT_OBSERVED"], coverage=[("DUPLICATE_WANTED_NAME", 2, 2)])

def refusal(case, script, args, code):
    command(case, script, args, 2, {"status": "INCOMPLETE", "error": code})
refusal("refuse-bp-token-bound", "build_module_inspector.py", ["--bp", crafted/"token-bound.bp", "--output", work/"token-report"], "BP_TOKEN_LIMIT")
refusal("refuse-same-file-alias", "build_module_inspector.py", ["--bp", fixtures/"clean.bp", "--bp", fixtures/"clean.bp", "--output", work/"alias-report"], "DUPLICATE_INPUT_FILE")
refusal("refuse-existing-report", "build_module_inspector.py", ["--bp", fixtures/"clean.bp", "--output", work/"clean-report"], "OUTPUT_EXISTS")
refusal("refuse-existing-generator-directory", "examples/generate.py", ["--output", fixtures], "OUTPUT_EXISTS")
refusal("refuse-relative-input", "build_module_inspector.py", ["--bp", "relative.bp", "--output", work/"relative-report"], "LOCAL_ABSOLUTE_PATH_REQUIRED")
refusal("refuse-missing-build-input", "build_module_inspector.py", ["--output", work/"empty-report"], "BUILD_INPUT_REQUIRED")
refusal("refuse-unsupported-wanted-name", "build_module_inspector.py", ["--bp", fixtures/"clean.bp", "--wanted", crafted/"invalid-wanted.txt", "--output", work/"invalid-wanted-report"], "WANTED_NAME_UNSUPPORTED")
assert inputs == {name: digest((work/name).read_bytes()) for name in inputs}
assert runtime == {name: digest((module/name).read_bytes()) for name in runtime_names}
expected_files = set(inputs) | {name+"/"+file for name in reports for file in ("report.json", "report.html", "MANIFEST.json")}
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()} == expected_files
assert len(reports) == 10 and len(expected_files) == 48 and source_hashes_checked == 22
assert mode_counts == {"default": 5, "included": 5}
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
print(json.dumps({"outcomes": outcomes, "reports_verified": 10, "payload_hashes_verified": 20,
                  "saved_text_source_hashes_checked": 22, "fixture_files_preserved": 18,
                  "expected_workspace_files": 48, "unexpected_application_files": 0,
                  "details_mode_counts": mode_counts, "details_do_not_change_observations": True,
                  "bytecode_files": 0, "runtime_bytes_preserved": True,
                  "make_invoked": False, "soong_invoked": False, "includes_followed": False,
                  "builds_executed": False, "real_user_build_files_used": False, "fixture_inputs_executed": False,
                  "physical_devices_opened": False, "effective_build_availability_verified": False}, sort_keys=True))
```

## Exact expected case outcomes

```json
[
  {
    "case": "create-fictional-build-text",
    "exit_code": 0
  },
  {
    "case": "literal-bp-mk-private-default",
    "exit_code": 0
  },
  {
    "case": "literal-bp-mk-opt-in-details",
    "exit_code": 0
  },
  {
    "case": "repeated-names-and-dynamic-identity-hold",
    "exit_code": 1
  },
  {
    "case": "unseen-in-selected-supported-scope",
    "exit_code": 1
  },
  {
    "case": "unsupported-top-level-stops-file",
    "exit_code": 1
  },
  {
    "case": "nested-name-is-not-direct-module-name",
    "exit_code": 1
  },
  {
    "case": "duplicate-direct-property-holds-declaration",
    "exit_code": 1
  },
  {
    "case": "unknown-make-include-stays-unfollowed",
    "exit_code": 1
  },
  {
    "case": "make-directive-stops-remainder",
    "exit_code": 1
  },
  {
    "case": "duplicate-wanted-name-is-recorded-once",
    "exit_code": 1
  },
  {
    "case": "refuse-bp-token-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-same-file-alias",
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
    "case": "refuse-missing-build-input",
    "exit_code": 2
  },
  {
    "case": "refuse-unsupported-wanted-name",
    "exit_code": 2
  }
]
```

The final summary also reports ten manifests, twenty report-file hashes, 22
source-hash observations, eighteen unchanged fictional inputs and 48 exact
input/report files. Five reports use defaults and five request details. All eight
scope flags remain false: Make, Soong, include following, builds, real user files,
fixture execution, physical device access and effective build availability.

For the clean case, three requested names are observed once. The repeated case
has two matching observations and an unresolved third identity, so the unseen
request is held. Unsupported BP top-level statements and Make directives stop
the remaining file; an unknown include remains unfollowed. Duplicate direct
properties hold a known declaration. Nested names never become module identities.
An unmatched request in complete selected supported scope receives
`not_observed_selected_supported_scope`, which remains narrower than real build
absence. Duplicate wanted rows are recorded once with separate coverage.

Read [FORMAT.md](docs/FORMAT.md) for the deliberate subset and
[QUALIFICATION.md](docs/QUALIFICATION.md) for release gates. No evidence here
establishes full Soong/Make validity, namespace resolution, dependency closure,
build inclusion, build success, binary quality or device compatibility. Use
trusted stable inputs/output parents. Path/snapshot checks and cooperative
bounds are not an OS sandbox or a hard native I/O deadline. Failed writes can
leave partial new reports; use another new output after resolving the cause.
