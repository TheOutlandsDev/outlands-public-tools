# Fictional Make declaration and explicit-root walkthrough

This guide reads invented saved Make/roots JSON only. It never evaluates Make,
reads or copies payload paths, follows includes or checks source availability.
Declared candidate conflicts are not effective build results. Unresolved
entries are excluded from collision pairing. Root substitution is limited to
explicit whole leading variables; there are no implicit defaults, environment
roots, nested expansion or owner/licensing decisions.

Use Python 3.12–3.15 without third-party packages. Formal guide evidence uses a
fresh no-pip CPython 3.15.2 environment with external copies of the actual three
runtime/generator files. Assertions must remain enabled. Actual CLI commands use
`-E -s -B` to retain sibling support imports while disabling environment/user
site settings and bytecode writes. The driver itself uses `-I -B`.

From the extracted module folder, save the single Python block below as
`fictional_copy_map_walkthrough.py` in an existing absolute private directory
outside the source tree. Replace the fictional path with an owned directory;
do not select links/reparse routes, network paths or actual configs/payloads.
The script creates one new workspace and never deletes earlier evidence.

PowerShell 5.1 or newer:

```powershell
$module = (Get-Location).Path
$privateParent = 'D:\Private-Review'
python -I -B "$privateParent/fictional_copy_map_walkthrough.py" "$module" "$privateParent"
```

POSIX shell, using an existing owned private directory:

```sh
module="$PWD"
privateParent="$HOME/private-review"
python3 -I -B "$privateParent/fictional_copy_map_walkthrough.py" "$module" "$privateParent"
```

The clean fixture joins three physical lines into one literal append with two
entries. Review has three declared conflict pairs, unresolved paths and an
uninspected include. Leading variables stay unresolved without explicit JSON,
despite deliberately different root values set only in child-process environment
dictionaries. Supplying the fictional roots JSON resolves the supported leading
variables; embedded/nested expressions remain unevaluated.

Other cases distinguish duplicate versus source/owner conflicts, NFC/casefold
portability, slash-boundary file/parent paths, condition/include/reassignment
coverage, continuation errors and empty/comment-only scope. Literal appends in
both conditional branches remain candidates; no branch winner or evaluated
collision is asserted. Finding locations are deduplicated separately from pairs.

Three default/details pairs must preserve observations after removing only
opt-in fields/mode. Defaults omit literal paths/owners; details include declared
and resolved fields, including unresolved text/null paths. Literal unsafe HTML
is escaped in the report. Hashes, counts, positions, opaque IDs and structure can
identify material: omission is not anonymization.

The driver independently recomputes Make-input and roots-file sizes/SHA-256,
both report payload hashes, exact report fields/stdout bytes and empty stderr.
It checks unchanged fixtures/runtime bytes, exact created files and no bytecode.
The roots file is a separate snapshot, outside the Make set's count, aggregate
and duplicate-identity checks. The guide asserts duplicate refusal only within
repeated `--file` inputs, not across Make/roots roles.

Thirteen controlled refusals cover roots schema/byte limits, relative paths,
Make aliases, existing outputs and physical/logical/entry/file bounds. Expected
review/incomplete exits are checked internally; the complete driver exits 0 only
if every assertion passes. Unsigned hashes prove consistency, not authenticity,
source existence, effective build output or payload rights.

## Executable driver

```python
"""Inspect fictional Make declarations and explicit roots; never evaluate or copy."""
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
work = Path(tempfile.mkdtemp(prefix="fictional-copy-map-", dir=parent)).resolve()
assert work.parent == parent
runtime_names = ("copy_map_inspector.py", "text_support.py", "examples/generate.py")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
runtime = {name: digest((module/name).read_bytes()) for name in runtime_names}
outcomes = []

def command(case, script, args, expected_exit, expected_stdout):
    before = {p.relative_to(work).as_posix(): digest(p.read_bytes()) for p in work.rglob("*") if p.is_file()}
    environment = dict(os.environ, LOCAL_PATH="fictional/ENVIRONMENT_ROOT_TRAP", TARGET_COPY_OUT_VENDOR="ENVIRONMENT_ROOT_TRAP")
    result = subprocess.run([sys.executable, "-E", "-s", "-B", str(module/script), *map(str, args)],
                            cwd=work, env=environment, capture_output=True, timeout=30)
    assert result.returncode == expected_exit and result.stderr == b"", case
    assert json.loads(result.stdout) == expected_stdout, case
    assert result.stdout == (json.dumps(expected_stdout, sort_keys=True)+os.linesep).encode(), case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before == {name: digest((work/name).read_bytes()) for name in before}, case
    outcomes.append({"case": case, "exit_code": result.returncode})

command("create-fictional-copy-map-text", "examples/generate.py", ["--output", work/"fixtures"], 0,
        {"status": "FICTIONAL_EXAMPLES_CREATED", "files": 4})
fixtures = work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"clean.mk", "review.mk", "roots.mk", "roots.json"}
assert json.loads((fixtures/"roots.json").read_bytes()) == {"schema_version": 1, "roots": {"LOCAL_PATH": "fictional", "TARGET_COPY_OUT_VENDOR": "vendor"}}
crafted = work/"crafted"; crafted.mkdir()
values = {
    "unresolved.mk": b'PRODUCT_COPY_FILES += $(UNKNOWN_ROOT)/one:vendor/same $(UNKNOWN_ROOT)/two:vendor/same\n',
    "expressions.mk": b'PRODUCT_COPY_FILES += $(nested$(NAME))/a:vendor/ignored\nPRODUCT_COPY_FILES += fictional/$(LOCAL_PATH)/a:vendor/embedded\nPRODUCT_COPY_FILES += $(shell echo fictional:vendor/not-a-literal)\nPRODUCT_COPY_FILES += fictional/a:vendor/<script>fiction</script>\n',
    "duplicates-a.mk": b'PRODUCT_COPY_FILES += fictional/a:vendor/same:owner\nPRODUCT_COPY_FILES += fictional/a:vendor/same:owner\n',
    "duplicates-b.mk": b'PRODUCT_COPY_FILES += fictional/b:vendor/same:owner fictional/a:vendor/same:other\n',
    "portability.mk": ('PRODUCT_COPY_FILES += fictional/a:vendor/caf\u00e9\nPRODUCT_COPY_FILES += fictional/b:vendor/cafe\u0301\n'
                       'PRODUCT_COPY_FILES += fictional/c:Vendor/CASE\nPRODUCT_COPY_FILES += fictional/d:vendor/case\n'
                       'PRODUCT_COPY_FILES += fictional/e:vendor/tree\nPRODUCT_COPY_FILES += fictional/f:VENDOR/tree/leaf\n').encode(),
    "conditional.mk": b'ifeq ($(MODE),yes)\nPRODUCT_COPY_FILES += fictional/a:vendor/candidate\nelse\nPRODUCT_COPY_FILES += fictional/b:vendor/candidate\nendif\ninclude fictional-unopened.mk\nPRODUCT_COPY_FILES := fictional/c:vendor/ignored\n',
    "continuation.mk": b'PRODUCT_COPY_FILES += \\\n# interrupted\nfictional/after:vendor/after\nPRODUCT_COPY_FILES += fictional/a:vendor/a\\#literal\nPRODUCT_COPY_FILES += \\',
    "empty.mk": b'',
    "comments.mk": b'# Fictional only.\nPRODUCT_COPY_FILES += # empty append\n',
    "bom.mk": b'\xef\xbb\xbfPRODUCT_COPY_FILES += fictional/a:vendor/a\r\n',
    "invalid-utf8.mk": b'\xff',
    "line-bound.mk": b'X'*8193,
    "logical-bound.mk": b'PRODUCT_COPY_FILES += '+b'a'*5000+b' \\\n'+b'b'*4000+b'\n',
    "record-bound.mk": ''.join(f'PRODUCT_COPY_FILES += fictional/a{i}:vendor/a{i}\n' for i in range(4001)).encode(),
    "byte-bound.mk": b'#'*(1024*1024+1),
    "duplicate-roots.json": b'{"schema_version":1,"roots":{},"roots":{}}',
    "nested-roots.json": b'{"schema_version":1,"roots":{"LOCAL_PATH":"$(OTHER_ROOT)"}}',
    "roots-byte-bound.json": b' '*(65536+1),
}
for name, data in values.items():
    (crafted/name).write_bytes(data)
inputs = {p.relative_to(work).as_posix(): digest(p.read_bytes()) for folder in (fixtures, crafted) for p in folder.iterdir()}
assert len(inputs) == 22
reports = []; make_hashes_checked = 0; roots_hashes_checked = 0; mode_counts = {"default": 0, "included": 0}

def inspect_case(case, selected, report_name, expected_exit, entries=(), conflicts=(), findings=(), coverage=(), roots=None, details=False):
    global make_hashes_checked, roots_hashes_checked
    output = work/report_name
    args = [value for path in selected for value in ("--file", path)]+["--output", output]
    if roots: args.extend(["--roots", roots])
    if details: args.append("--include-details")
    expected = {"status": "NO_SCOPE_FINDINGS" if expected_exit == 0 else "REVIEW_REQUIRED",
                "entries": len(entries), "conflicts": len(conflicts), "coverage_issues": len(coverage)}
    command(case, "copy_map_inspector.py", args, expected_exit, expected)
    assert {p.name for p in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    raw = (output/"report.json").read_bytes(); report = json.loads(raw)
    keys = {"schema_version", "tool", "scope", "details_included", "root_count", "inputs", "entries", "conflicts", "findings", "coverage_issues", "status"}
    assert set(report) == (keys|{"roots_input"} if roots else keys)
    assert report["schema_version"] == 1 and report["tool"] == "Android Build Copy-Map Inspector"
    assert report["scope"] == "Declared literal append entries only; no Make evaluation, source existence or payload licensing check."
    assert report["status"] == expected["status"] and report["details_included"] is details
    assert report["root_count"] == (2 if roots else 0)
    expected_inputs = []
    for index, path in enumerate(selected, 1):
        data = path.read_bytes(); expected_inputs.append({"id": f"input-{index:04d}", "bytes": len(data), "sha256": digest(data)})
        make_hashes_checked += 1
    assert report["inputs"] == expected_inputs
    if roots:
        data = roots.read_bytes()
        assert report["roots_input"] == {"id": "roots-input", "bytes": len(data), "sha256": digest(data)}
        roots_hashes_checked += 1
    def location(source, line):
        return {"source": f"input-{source:04d}", "line": line}
    expected_entries = []
    for index, (source, line, declared_source, declared_destination, owner, resolved_source, resolved_destination) in enumerate(entries, 1):
        item = {"id": f"entry-{index:04d}", **location(source, line),
                "resolution": "literal_or_explicit_root" if resolved_source is not None and resolved_destination is not None else "unresolved",
                "owner_present": owner is not None}
        if details: item.update(declared_source=declared_source, declared_destination=declared_destination, declared_owner=owner,
                                resolved_source=resolved_source, resolved_destination=resolved_destination)
        expected_entries.append(item)
    assert report["entries"] == expected_entries
    assert report["conflicts"] == [{"code": code, "entries": [f"entry-{i:04d}" for i in ids]} for code, ids in conflicts]
    def issues(values):
        return [{"code": code, **location(source, line)} for code, source, line in values]
    assert report["findings"] == issues(findings) and report["coverage_issues"] == issues(coverage)
    payloads = {name: (output/name).read_bytes() for name in ("report.json", "report.html")}
    assert json.loads((output/"MANIFEST.json").read_bytes()) == {"schema_version": 1, "files": [
        {"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(payloads.items())]}
    html = payloads["report.html"].decode()
    assert "Content-Security-Policy" in html and "<script>" not in html and "&quot;schema_version&quot;" in html
    assert all(marker not in data for data in payloads.values() for marker in
               (b"ENVIRONMENT_ROOT_TRAP", b"fictional-unopened.mk", str(work).encode(), str(module).encode()))
    if not details:
        assert all(marker not in raw for marker in (b"fictional/", b"vendor/", b"Vendor/", b"demo_owner", b"$(LOCAL_PATH)", b"<script>"))
    reports.append(report_name); mode_counts["included" if details else "default"] += 1
    return report, html

def literal(source, line, src, dest, owner=None):
    return (source, line, src, dest, owner, src, dest)
def remove_details(value):
    result = copy.deepcopy(value); result["details_included"] = False
    for row in result["entries"]:
        for field in ("declared_source", "declared_destination", "declared_owner", "resolved_source", "resolved_destination"): row.pop(field)
    return result
clean_entries = [literal(1, 2, "fictional/alpha.conf", "vendor/etc/alpha.conf"), literal(1, 2, "fictional/beta.conf", "vendor/etc/beta.conf", "demo_owner")]
clean_default, _ = inspect_case("literal-append-continuation-private-default", [fixtures/"clean.mk"], "clean-report", 0, entries=clean_entries)
clean_details, _ = inspect_case("literal-append-continuation-opt-in-details", [fixtures/"clean.mk"], "clean-details-report", 0, entries=clean_entries, details=True)
assert remove_details(clean_details) == clean_default
dest_conflict = "DECLARED_DESTINATION_CONFLICT"; portability = "PORTABILITY_DESTINATION_COLLISION"
review_args = dict(entries=[literal(1, 1, "fictional/one", "vendor/etc/demo"), literal(1, 1, "fictional/two", "vendor/etc/demo"),
    literal(1, 2, "fictional/three", "Vendor/etc/Demo"), (1, 3, "fictional/four", "../escape", None, "fictional/four", None),
    (1, 4, "$(UNKNOWN_ROOT)/five", "vendor/etc/five", None, None, "vendor/etc/five")],
    conflicts=[(dest_conflict, [1, 2]), (portability, [1, 3]), (portability, [2, 3])],
    findings=[(dest_conflict, 1, 1), (portability, 1, 2)],
    coverage=[("UNSAFE_OR_UNSUPPORTED_RELATIVE_PATH", 1, 3), ("UNRESOLVED_ROOT_VARIABLE", 1, 4), ("UNINSPECTED_MAKE_STATEMENT", 1, 5)])
review_default, _ = inspect_case("declared-conflicts-and-unresolved-paths-default", [fixtures/"review.mk"], "review-report", 1, **review_args)
review_details, _ = inspect_case("declared-conflicts-and-unresolved-paths-details", [fixtures/"review.mk"], "review-details-report", 1, details=True, **review_args)
assert remove_details(review_details) == review_default
root_entry = (1, 1, "$(LOCAL_PATH)/demo.conf", "$(TARGET_COPY_OUT_VENDOR)/etc/demo.conf", None, "fictional/demo.conf", "vendor/etc/demo.conf")
inspect_case("no-implicit-defaults-or-environment-roots", [fixtures/"roots.mk"], "no-roots-report", 1,
    entries=[(*root_entry[:5], None, None)], coverage=[("UNRESOLVED_ROOT_VARIABLE", 1, 1)], details=True)
root_default, _ = inspect_case("explicit-leading-roots-private-default", [fixtures/"roots.mk"], "roots-report", 0,
                               entries=[root_entry], roots=fixtures/"roots.json")
root_details, _ = inspect_case("explicit-leading-roots-opt-in-details", [fixtures/"roots.mk"], "roots-details-report", 0,
                               entries=[root_entry], roots=fixtures/"roots.json", details=True)
assert remove_details(root_details) == root_default
inspect_case("unresolved-entries-excluded-from-collision-pairs", [crafted/"unresolved.mk"], "unresolved-report", 1,
    entries=[(1, 1, "$(UNKNOWN_ROOT)/one", "vendor/same", None, None, "vendor/same"),
             (1, 1, "$(UNKNOWN_ROOT)/two", "vendor/same", None, None, "vendor/same")],
    coverage=[("UNRESOLVED_ROOT_VARIABLE", 1, 1)], details=True)
_, escaped = inspect_case("nested-functions-and-embedded-roots-unevaluated", [crafted/"expressions.mk"], "expressions-report", 1,
    entries=[(1, 2, "fictional/$(LOCAL_PATH)/a", "vendor/embedded", None, None, "vendor/embedded"),
             (1, 4, "fictional/a", "vendor/<script>fiction</script>", None, "fictional/a", None)],
    coverage=[("MAKE_EXPRESSION_NOT_EVALUATED", 1, 1), ("MAKE_EXPRESSION_NOT_EVALUATED", 1, 2),
              ("MAKE_EXPRESSION_NOT_EVALUATED", 1, 3), ("UNSAFE_OR_UNSUPPORTED_RELATIVE_PATH", 1, 4)], roots=fixtures/"roots.json", details=True)
assert "&lt;script&gt;fiction&lt;/script&gt;" in escaped
inspect_case("duplicate-source-and-owner-conflicts-across-files", [crafted/"duplicates-a.mk", crafted/"duplicates-b.mk"], "duplicate-report", 1,
    entries=[literal(1, 1, "fictional/a", "vendor/same", "owner"), literal(1, 2, "fictional/a", "vendor/same", "owner"),
             literal(2, 1, "fictional/b", "vendor/same", "owner"), literal(2, 1, "fictional/a", "vendor/same", "other")],
    conflicts=[("DUPLICATE_DECLARED_COPY", [1, 2]), (dest_conflict, [1, 3]), (dest_conflict, [2, 3]),
               (dest_conflict, [1, 4]), (dest_conflict, [2, 4]), (dest_conflict, [3, 4])],
    findings=[("DUPLICATE_DECLARED_COPY", 1, 2), (dest_conflict, 2, 1)], details=True)
inspect_case("nfc-casefold-and-file-parent-portability", [crafted/"portability.mk"], "portability-report", 1,
    entries=[literal(1, 1, "fictional/a", "vendor/caf\u00e9"), literal(1, 2, "fictional/b", "vendor/cafe\u0301"),
             literal(1, 3, "fictional/c", "Vendor/CASE"), literal(1, 4, "fictional/d", "vendor/case"),
             literal(1, 5, "fictional/e", "vendor/tree"), literal(1, 6, "fictional/f", "VENDOR/tree/leaf")],
    conflicts=[(portability, [1, 2]), (portability, [3, 4]), ("FILE_PARENT_DESTINATION_CONFLICT", [5, 6])],
    findings=[(portability, 1, 2), (portability, 1, 4), ("FILE_PARENT_DESTINATION_CONFLICT", 1, 6)], details=True)
inspect_case("conditions-includes-and-reassignment-not-evaluated", [crafted/"conditional.mk"], "conditional-report", 1,
    entries=[literal(1, 2, "fictional/a", "vendor/candidate"), literal(1, 4, "fictional/b", "vendor/candidate")],
    conflicts=[(dest_conflict, [1, 2])], findings=[(dest_conflict, 1, 4)],
    coverage=[("UNINSPECTED_MAKE_STATEMENT", 1, line) for line in (1, 3, 5, 6, 7)])
inspect_case("interrupted-escaped-and-dangling-continuations", [crafted/"continuation.mk"], "continuation-report", 1,
    coverage=[("INTERRUPTED_CONTINUATION", 1, 1), ("UNINSPECTED_MAKE_STATEMENT", 1, 3),
              ("QUOTING_OR_ESCAPING_UNSUPPORTED", 1, 4), ("DANGLING_CONTINUATION", 1, 5)])
inspect_case("empty-input-is-limited-scope-success", [crafted/"empty.mk"], "empty-report", 0)
inspect_case("comments-and-empty-append-is-limited-scope-success", [crafted/"comments.mk"], "comments-report", 0)
inspect_case("utf8-bom-and-crlf-supported", [crafted/"bom.mk"], "bom-report", 0, entries=[literal(1, 1, "fictional/a", "vendor/a")])

def refusal(case, selected, code, roots=None, output=None):
    args = [value for path in selected for value in ("--file", path)]+["--output", output or work/(case+"-output")]
    if roots: args.extend(["--roots", roots])
    command(case, "copy_map_inspector.py", args, 2, {"status": "INCOMPLETE", "error": code})
refusal("refuse-duplicate-roots-json-key", [fixtures/"clean.mk"], "DUPLICATE_JSON_KEY", roots=crafted/"duplicate-roots.json")
refusal("refuse-nested-root-value", [fixtures/"clean.mk"], "INVALID_ROOT_VALUE", roots=crafted/"nested-roots.json")
refusal("refuse-roots-byte-bound", [fixtures/"clean.mk"], "INPUT_BYTE_LIMIT", roots=crafted/"roots-byte-bound.json")
refusal("refuse-repeated-make-file-alias", [fixtures/"clean.mk", fixtures/"clean.mk"], "DUPLICATE_INPUT_FILE")
refusal("refuse-existing-report", [fixtures/"clean.mk"], "OUTPUT_EXISTS", output=work/"clean-report")
command("refuse-existing-generator-directory", "examples/generate.py", ["--output", fixtures], 2,
        {"status": "INCOMPLETE", "error": "OUTPUT_EXISTS"})
refusal("refuse-relative-make-input", ["relative.mk"], "LOCAL_ABSOLUTE_PATH_REQUIRED")
refusal("refuse-physical-line-bound", [crafted/"line-bound.mk"], "TEXT_LINE_LIMIT")
refusal("refuse-joined-logical-line-bound", [crafted/"logical-bound.mk"], "LOGICAL_LINE_LIMIT")
refusal("refuse-entry-collection-bound", [crafted/"record-bound.mk"], "RECORD_LIMIT")
refusal("refuse-relative-roots-input", [fixtures/"clean.mk"], "LOCAL_ABSOLUTE_PATH_REQUIRED", roots="relative.json")
refusal("refuse-invalid-utf8", [crafted/"invalid-utf8.mk"], "UTF8_REQUIRED")
refusal("refuse-make-input-byte-bound", [crafted/"byte-bound.mk"], "INPUT_BYTE_LIMIT")
assert inputs == {name: digest((work/name).read_bytes()) for name in inputs}
assert runtime == {name: digest((module/name).read_bytes()) for name in runtime_names}
expected_files = set(inputs) | {name+"/"+file for name in reports for file in ("report.json", "report.html", "MANIFEST.json")}
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()} == expected_files
assert len(reports) == 16 and len(expected_files) == 70 and make_hashes_checked == 17 and roots_hashes_checked == 3
assert mode_counts == {"default": 8, "included": 8}
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
print(json.dumps({"outcomes": outcomes, "reports_verified": 16, "payload_hashes_verified": 32,
                  "make_input_hashes_checked": 17, "roots_hashes_checked": 3, "fixture_files_preserved": 22,
                  "expected_workspace_files": 70, "unexpected_application_files": 0, "details_mode_counts": mode_counts,
                  "details_do_not_change_observations": True, "child_environment_root_trap_ignored": True,
                  "bytecode_files": 0, "runtime_bytes_preserved": True,
                  "make_evaluated": False, "payload_paths_accessed": False, "payloads_copied": False,
                  "environment_roots_read": False, "real_device_configs_used": False,
                  "effective_build_results_verified": False, "source_availability_verified": False,
                  "payload_rights_verified": False}, sort_keys=True))
```

## Exact expected case outcomes

```json
[
  {
    "case": "create-fictional-copy-map-text",
    "exit_code": 0
  },
  {
    "case": "literal-append-continuation-private-default",
    "exit_code": 0
  },
  {
    "case": "literal-append-continuation-opt-in-details",
    "exit_code": 0
  },
  {
    "case": "declared-conflicts-and-unresolved-paths-default",
    "exit_code": 1
  },
  {
    "case": "declared-conflicts-and-unresolved-paths-details",
    "exit_code": 1
  },
  {
    "case": "no-implicit-defaults-or-environment-roots",
    "exit_code": 1
  },
  {
    "case": "explicit-leading-roots-private-default",
    "exit_code": 0
  },
  {
    "case": "explicit-leading-roots-opt-in-details",
    "exit_code": 0
  },
  {
    "case": "unresolved-entries-excluded-from-collision-pairs",
    "exit_code": 1
  },
  {
    "case": "nested-functions-and-embedded-roots-unevaluated",
    "exit_code": 1
  },
  {
    "case": "duplicate-source-and-owner-conflicts-across-files",
    "exit_code": 1
  },
  {
    "case": "nfc-casefold-and-file-parent-portability",
    "exit_code": 1
  },
  {
    "case": "conditions-includes-and-reassignment-not-evaluated",
    "exit_code": 1
  },
  {
    "case": "interrupted-escaped-and-dangling-continuations",
    "exit_code": 1
  },
  {
    "case": "empty-input-is-limited-scope-success",
    "exit_code": 0
  },
  {
    "case": "comments-and-empty-append-is-limited-scope-success",
    "exit_code": 0
  },
  {
    "case": "utf8-bom-and-crlf-supported",
    "exit_code": 0
  },
  {
    "case": "refuse-duplicate-roots-json-key",
    "exit_code": 2
  },
  {
    "case": "refuse-nested-root-value",
    "exit_code": 2
  },
  {
    "case": "refuse-roots-byte-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-repeated-make-file-alias",
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
    "case": "refuse-relative-make-input",
    "exit_code": 2
  },
  {
    "case": "refuse-physical-line-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-joined-logical-line-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-entry-collection-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-relative-roots-input",
    "exit_code": 2
  },
  {
    "case": "refuse-invalid-utf8",
    "exit_code": 2
  },
  {
    "case": "refuse-make-input-byte-bound",
    "exit_code": 2
  }
]
```

The summary records thirty cases: eight exit 0, nine review exit 1 and thirteen
incomplete exit 2 results. Sixteen normal manifests cover 32 report payloads.
Seventeen Make-input hashes plus three roots-file hashes, 22 unchanged fictional
fixtures and seventy exact input/report files are independently checked. Eight
reports use defaults and eight request details; three pairs preserve observations.

All eight scope fields stay false: Make evaluation, payload path access, copying,
environment roots, real configs, effective build results, source availability
and payload rights. Empty/comment/empty-append scope can exit 0 with no entries;
that says nothing about complete builds or payload existence. Read
[FORMAT.md](docs/FORMAT.md) and [QUALIFICATION.md](docs/QUALIFICATION.md).

Use trusted stable inputs and owned output parents. Snapshot/path checks and
cooperative limits are not an OS sandbox, atomic snapshot or hard native I/O
deadline. A write error may leave a partial new report directory; preserve it,
review the cause and choose a new destination after fixing the failure. No real
vendor config, device, evaluated build or distribution right is certified.
