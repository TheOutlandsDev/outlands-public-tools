# Fictional selected init-text walkthrough

This guide indexes invented saved rc text only. It never starts a service,
mounts a target, follows an import, evaluates triggers/properties or opens a
device. Names and references describe selected declarations, not effective
device state. Duplicate services remain ambiguous even with `override`.
Reboot/critical markers are observations, not runtime behavior or bootability proof.

Use Python 3.12–3.15 without third-party packages. Formal guide evidence uses a
fresh no-pip CPython 3.15.2 environment with external copies of the actual three
runtime/generator files. Assertions must remain enabled. Actual CLI commands use
`-E -s -B` to retain sibling support imports while disabling environment/user
site settings and bytecode writes. The driver itself uses `-I -B`.

From the extracted module folder, save the single Python block below as
`fictional_init_walkthrough.py` in an existing absolute private directory outside
the source tree. Replace the fictional path with an owned directory; do not
select links/reparse routes, network paths or real configs. The script creates
one new private workspace and never deletes earlier evidence.

PowerShell 5.1 or newer:

```powershell
$module = (Get-Location).Path
$privateParent = 'D:\Private-Review'
python -I -B "$privateParent/fictional_init_walkthrough.py" "$module" "$privateParent"
```

POSIX shell, using an existing owned private directory:

```sh
module="$PWD"
privateParent="$HOME/private-review"
python3 -I -B "$privateParent/fictional_init_walkthrough.py" "$module" "$privateParent"
```

The clean fixture has one service and a unique selected-file reference. The
review fixture retains duplicate declarations, an ambiguous reference, an
unselected reference, critical/reboot markers and an unfollowed import. The
guide checks both privacy modes and requires the same observations after
removing only opt-in literal fields and the mode flag. Details may include
declared names, executable/import/mount paths and trigger text; raw service argv
is always omitted. Unknown command/option payloads are omitted too. Hashes,
counts, line positions and structure remain identifying, so omission is not
anonymization. Literal HTML in requested details must be escaped in HTML output.

Other cases check cross-file reference indexing without opening targets,
nonliteral section-context reset, malformed headers, reboot/restart declarations,
empty/comment-only scope and BOM/CRLF. Empty/comment-only files intentionally
exit 0 with no indexed declarations; this is not configuration completeness.
Ten controlled refusals cover UTF-8, controls, line/collection/file-byte limits,
same-file aliases, existing destinations, relative input and missing arguments.

The driver checks exact report fields, fixed stdout bytes and empty stderr,
independently recomputes input lengths/SHA-256 and both report payload hashes,
and verifies unchanged fixtures/runtime bytes, exact created files and no
bytecode. Unsigned manifests prove consistency, not origin or device validity.
Expected review/incomplete exits are checked internally; the complete driver
exits 0 only when every assertion passes.

## Executable driver

```python
"""Index only fictional saved rc text; never execute its declarations."""
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
work = Path(tempfile.mkdtemp(prefix="fictional-init-text-", dir=parent)).resolve()
assert work.parent == parent
runtime_names = ("init_inspector.py", "text_support.py", "examples/generate.py")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
runtime = {name: digest((module/name).read_bytes()) for name in runtime_names}
outcomes = []

def command(case, script, args, expected_exit, expected_stdout):
    before = {p.relative_to(work).as_posix(): digest(p.read_bytes()) for p in work.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-E", "-s", "-B", str(module/script), *map(str, args)],
                            cwd=work, capture_output=True, timeout=30)
    assert result.returncode == expected_exit and result.stderr == b"", case
    assert json.loads(result.stdout) == expected_stdout, case
    assert result.stdout == (json.dumps(expected_stdout, sort_keys=True)+os.linesep).encode(), case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before == {name: digest((work/name).read_bytes()) for name in before}, case
    outcomes.append({"case": case, "exit_code": result.returncode})

command("create-fictional-init-text", "examples/generate.py", ["--output", work/"fixtures"], 0,
        {"status": "FICTIONAL_EXAMPLES_CREATED", "files": 2})
fixtures = work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"clean.rc", "review.rc"}
crafted = work/"crafted"; crafted.mkdir()
values = {
    "reset.rc": b'service example_alpha /fictional/bin/alpha PRIVATE_ARGV_MARKER\n disabled\non property:fictional.ready=1\n start example_alpha\n setprop fictional.value $dynamic\n stop example_alpha\nservice example_beta "/fictional/bin/quoted"\n oneshot\non late-init\n exec_start example_alpha\n',
    "declarations.rc": b'service example_alpha /fictional/bin/alpha PRIVATE_ARGV_MARKER\n',
    "references.rc": b'import /fictional/unopened.rc\non boot\n start example_alpha\n stop not_selected\n mount_all /fictional/fstab --late\n',
    "malformed.rc": b'service invalid/name /fictional/bin/invalid\n disabled\non\n start invalid\nimport\n oneshot\n',
    "reboot.rc": b'service example_reboot /fictional/bin/reboot-demo PRIVATE_ARGV_MARKER\n critical 1 2\n reboot_on_failure reboot-demo\n onrestart restart not_selected\n onrestart reboot\n onrestart setprop fictional.value PRIVATE_OPTION_MARKER\n',
    "html.rc": b'service example_html /fictional/bin/<script>fiction</script> PRIVATE_ARGV_MARKER\non <script>fiction</script>\n start example_html\n',
    "empty.rc": b'',
    "comments.rc": b'# Fictional comment only.\n \t# PRIVATE_ARGV_MARKER\n\n',
    "bom.rc": b'\xef\xbb\xbfservice example_bom /fictional/bin/bom\r\non boot\r\n start example_bom\r\n',
    "invalid-utf8.rc": b'\xff',
    "control.rc": b'# fictional\x00\n',
    "line-bound.rc": b'X'*8193,
    "record-bound.rc": ''.join(f'service example_{i} /fictional/bin/a\n' for i in range(4001)).encode(),
    "byte-bound.rc": b'#'*(1024*1024+1),
}
for name, data in values.items():
    (crafted/name).write_bytes(data)
inputs = {p.relative_to(work).as_posix(): digest(p.read_bytes())
          for folder in (fixtures, crafted) for p in folder.iterdir()}
assert len(inputs) == 16
reports = []; source_hashes_checked = 0; mode_counts = {"default": 0, "included": 0}

def inspect_case(case, selected, report_name, expected_exit, services=(), actions=(), imports=(), references=(), mounts=(), findings=(), coverage=(), details=False):
    global source_hashes_checked
    output = work/report_name
    args = [value for path in selected for value in ("--file", path)]+["--output", output]
    if details: args.append("--include-details")
    expected = {"status": "NO_SCOPE_FINDINGS" if expected_exit == 0 else "REVIEW_REQUIRED",
                "services": len(services), "findings": len(findings), "coverage_issues": len(coverage)}
    command(case, "init_inspector.py", args, expected_exit, expected)
    assert {p.name for p in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    raw = (output/"report.json").read_bytes(); report = json.loads(raw)
    assert set(report) == {"schema_version", "tool", "scope", "details_included", "inputs", "services", "actions",
                           "imports", "references", "mount_all", "findings", "coverage_issues", "status"}
    assert report["schema_version"] == 1 and report["tool"] == "Android Init Service Inspector"
    assert report["scope"] == "Literal selected-file declarations; no import, property, trigger or runtime evaluation."
    assert report["status"] == expected["status"] and report["details_included"] is details
    expected_inputs = []
    for index, path in enumerate(selected, 1):
        data = path.read_bytes(); expected_inputs.append({"id": f"input-{index:04d}", "bytes": len(data), "sha256": digest(data)})
        source_hashes_checked += 1
    assert report["inputs"] == expected_inputs
    def location(source, line):
        return {"source": f"input-{source:04d}", "line": line}
    rows = []
    for index, (source, line, argc, options, restarts, name, executable) in enumerate(services, 1):
        item = {"id": f"service-{index:04d}", **location(source, line), "argument_count": argc,
                "options": options, "restart_commands": restarts}
        if details: item.update(name=name, executable=executable)
        rows.append(item)
    assert report["services"] == rows
    rows = []
    for index, (source, line, trigger) in enumerate(actions, 1):
        item = {"id": f"action-{index:04d}", **location(source, line)}
        if details: item["trigger_text"] = trigger
        rows.append(item)
    assert report["actions"] == rows
    rows = []
    for source, line, operands, path in imports:
        item = {**location(source, line), "operand_count": operands}
        if details and operands == 1: item["declared_path"] = path
        rows.append(item)
    assert report["imports"] == rows
    rows = []
    for source, line, command_name, context, resolution, ids, name in references:
        item = {**location(source, line), "command": command_name, "context": context,
                "resolution": resolution, "service_ids": [f"service-{i:04d}" for i in ids]}
        if details: item["declared_name"] = name
        rows.append(item)
    assert report["references"] == rows
    rows = []
    for source, line, mode, path in mounts:
        item = {**location(source, line), "mode": mode}
        if details: item["declared_path"] = path
        rows.append(item)
    assert report["mount_all"] == rows
    def issues(values):
        return [{"code": code, **location(source, line)} for code, source, line in values]
    assert report["findings"] == issues(findings) and report["coverage_issues"] == issues(coverage)
    payloads = {name: (output/name).read_bytes() for name in ("report.json", "report.html")}
    assert json.loads((output/"MANIFEST.json").read_bytes()) == {"schema_version": 1, "files": [
        {"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(payloads.items())]}
    html = payloads["report.html"].decode()
    assert "Content-Security-Policy" in html and "<script>" not in html and "&quot;schema_version&quot;" in html
    assert all(marker not in data for data in payloads.values() for marker in
               (b"PRIVATE_ARGV_MARKER", b"PRIVATE_OPTION_MARKER", b"--demo", str(work).encode(), str(module).encode()))
    if not details:
        assert all(marker not in raw for marker in (b"/fictional", b"demo_worker", b"example_", b"not_selected", b"<script>"))
    reports.append(report_name); mode_counts["included" if details else "default"] += 1
    return report, html

unique = "unique_selected_declaration"; missing = "not_declared_in_selected_files"; ambiguous = "ambiguous_selected_declarations"
clean_services = [(1, 2, 1, ["class", "disabled", "oneshot"], 0, "demo_worker", "/fictional/bin/worker")]
clean_actions = [(1, 6, "boot")]
clean_refs = [(1, 7, "start", "action-0001", unique, [1], "demo_worker")]
default, _ = inspect_case("clean-literal-index-private-default", [fixtures/"clean.rc"], "clean-report", 0,
                          services=clean_services, actions=clean_actions, references=clean_refs)
detailed, _ = inspect_case("clean-literal-index-opt-in-details", [fixtures/"clean.rc"], "clean-details-report", 0,
                           services=clean_services, actions=clean_actions, references=clean_refs, details=True)
def remove_details(value):
    result = copy.deepcopy(value); result["details_included"] = False
    for key in ("services", "actions", "imports", "references", "mount_all"):
        for row in result[key]:
            for field in ("name", "executable", "trigger_text", "declared_path", "declared_name"): row.pop(field, None)
    return result
assert remove_details(detailed) == default
review_args = dict(services=[(1, 2, 0, ["critical", "onrestart"], 1, "demo_worker", "/fictional/bin/worker"),
                            (1, 5, 0, ["override"], 0, "demo_worker", "/fictional/bin/other")],
                   actions=[(1, 7, "boot")], imports=[(1, 11, 1, "/fictional/not-followed.rc")],
                   references=[(1, 8, "start", "action-0001", ambiguous, [1, 2], "demo_worker"),
                               (1, 9, "start", "action-0001", missing, [], "unselected_service")],
                   mounts=[(1, 10, "--early", "/fictional/fstab")], findings=[
                       ("CRITICAL_SERVICE_DECLARED", 1, 3), ("RESTART_REBOOT_DECLARED", 1, 4),
                       ("DUPLICATE_SERVICE_DECLARATION", 1, 2), ("DUPLICATE_SERVICE_DECLARATION", 1, 5),
                       ("REFERENCE_NEEDS_SELECTED_FILE_REVIEW", 1, 8), ("REFERENCE_NEEDS_SELECTED_FILE_REVIEW", 1, 9)],
                   coverage=[("IMPORTS_NOT_FOLLOWED", 1, 11)])
review_default, _ = inspect_case("duplicate-override-and-unfollowed-import-default", [fixtures/"review.rc"], "review-report", 1, **review_args)
review_details, _ = inspect_case("duplicate-override-and-unfollowed-import-details", [fixtures/"review.rc"], "review-details-report", 1, details=True, **review_args)
assert remove_details(review_details) == review_default
inspect_case("nonliteral-lines-reset-supported-context", [crafted/"reset.rc"], "reset-report", 1,
    services=[(1, 1, 1, ["disabled"], 0, "example_alpha", "/fictional/bin/alpha")],
    actions=[(1, 3, "property:fictional.ready=1"), (1, 9, "late-init")],
    references=[(1, 4, "start", "action-0001", unique, [1], "example_alpha"), (1, 10, "exec_start", "action-0002", unique, [1], "example_alpha")],
    coverage=[("NONLITERAL_STATEMENT", 1, 5), ("STATEMENT_WITHOUT_SUPPORTED_SECTION", 1, 6),
              ("NONLITERAL_STATEMENT", 1, 7), ("STATEMENT_WITHOUT_SUPPORTED_SECTION", 1, 8)], details=True)
inspect_case("cross-file-reference-index-never-opens-targets", [crafted/"declarations.rc", crafted/"references.rc"], "cross-file-report", 1,
    services=[(1, 1, 1, [], 0, "example_alpha", "/fictional/bin/alpha")], actions=[(2, 2, "boot")],
    imports=[(2, 1, 1, "/fictional/unopened.rc")],
    references=[(2, 3, "start", "action-0001", unique, [1], "example_alpha"), (2, 4, "stop", "action-0001", missing, [], "not_selected")],
    mounts=[(2, 5, "--late", "/fictional/fstab")], findings=[("REFERENCE_NEEDS_SELECTED_FILE_REVIEW", 2, 4)],
    coverage=[("IMPORTS_NOT_FOLLOWED", 2, 1)], details=True)
inspect_case("malformed-headers-do-not-capture-later-statements", [crafted/"malformed.rc"], "malformed-report", 1,
    imports=[(1, 5, 0, None)], coverage=[("INVALID_SERVICE_DECLARATION", 1, 1), ("STATEMENT_WITHOUT_SUPPORTED_SECTION", 1, 2),
        ("INVALID_ACTION_DECLARATION", 1, 3), ("STATEMENT_WITHOUT_SUPPORTED_SECTION", 1, 4),
        ("IMPORTS_NOT_FOLLOWED", 1, 5), ("STATEMENT_WITHOUT_SUPPORTED_SECTION", 1, 6)], details=True)
inspect_case("reboot-and-restart-markers-are-declarations-only", [crafted/"reboot.rc"], "reboot-report", 1,
    services=[(1, 1, 1, ["critical", "reboot_on_failure", "onrestart"], 3, "example_reboot", "/fictional/bin/reboot-demo")],
    references=[(1, 4, "restart", "service-0001", missing, [], "not_selected")], findings=[
        ("CRITICAL_SERVICE_DECLARED", 1, 2), ("REBOOT_ON_FAILURE_DECLARED", 1, 3), ("RESTART_REBOOT_DECLARED", 1, 5),
        ("REFERENCE_NEEDS_SELECTED_FILE_REVIEW", 1, 4)], coverage=[("UNINSPECTED_RESTART_COMMAND", 1, 6)], details=True)
html_args = dict(services=[(1, 1, 1, [], 0, "example_html", "/fictional/bin/<script>fiction</script>")],
                 actions=[(1, 2, "<script>fiction</script>")],
                 references=[(1, 3, "start", "action-0001", unique, [1], "example_html")])
html_default, _ = inspect_case("literal-html-text-private-default", [crafted/"html.rc"], "html-default-report", 0, **html_args)
html_details, html = inspect_case("literal-details-html-escaped-argv-still-omitted", [crafted/"html.rc"], "html-details-report", 0, details=True, **html_args)
assert "&lt;script&gt;fiction&lt;/script&gt;" in html and remove_details(html_details) == html_default
inspect_case("empty-input-is-limited-scope-success", [crafted/"empty.rc"], "empty-report", 0)
inspect_case("comment-only-input-is-limited-scope-success", [crafted/"comments.rc"], "comment-report", 0)
inspect_case("utf8-bom-and-crlf-supported", [crafted/"bom.rc"], "bom-report", 0,
    services=[(1, 1, 0, [], 0, "example_bom", "/fictional/bin/bom")], actions=[(1, 2, "boot")],
    references=[(1, 3, "start", "action-0001", unique, [1], "example_bom")])

def refusal(case, selected, code, output=None):
    args = [value for path in selected for value in ("--file", path)]+["--output", output or work/(case+"-output")]
    command(case, "init_inspector.py", args, 2, {"status": "INCOMPLETE", "error": code})
refusal("refuse-invalid-utf8", [crafted/"invalid-utf8.rc"], "UTF8_REQUIRED")
refusal("refuse-physical-control", [crafted/"control.rc"], "TEXT_CONTROL_UNSUPPORTED")
refusal("refuse-line-bound", [crafted/"line-bound.rc"], "TEXT_LINE_LIMIT")
refusal("refuse-service-collection-bound", [crafted/"record-bound.rc"], "RECORD_LIMIT")
refusal("refuse-same-file-alias", [fixtures/"clean.rc", fixtures/"clean.rc"], "DUPLICATE_INPUT_FILE")
refusal("refuse-existing-report", [fixtures/"clean.rc"], "OUTPUT_EXISTS", output=work/"clean-report")
command("refuse-existing-generator-directory", "examples/generate.py", ["--output", fixtures], 2,
        {"status": "INCOMPLETE", "error": "OUTPUT_EXISTS"})
refusal("refuse-relative-input", ["relative.rc"], "LOCAL_ABSOLUTE_PATH_REQUIRED")
command("refuse-missing-required-arguments", "init_inspector.py", [], 2, {"status": "INCOMPLETE", "error": "ARGUMENTS_INVALID"})
refusal("refuse-input-byte-bound", [crafted/"byte-bound.rc"], "INPUT_BYTE_LIMIT")
assert inputs == {name: digest((work/name).read_bytes()) for name in inputs}
assert runtime == {name: digest((module/name).read_bytes()) for name in runtime_names}
expected_files = set(inputs) | {name+"/"+file for name in reports for file in ("report.json", "report.html", "MANIFEST.json")}
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()} == expected_files
assert len(reports) == 13 and len(expected_files) == 55 and source_hashes_checked == 14
assert mode_counts == {"default": 6, "included": 7}
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
print(json.dumps({"outcomes": outcomes, "reports_verified": 13, "payload_hashes_verified": 26,
                  "saved_input_hashes_checked": 14, "fixture_files_preserved": 16, "expected_workspace_files": 55,
                  "unexpected_application_files": 0, "details_mode_counts": mode_counts,
                  "details_do_not_change_observations": True, "raw_argv_always_omitted": True,
                  "bytecode_files": 0, "runtime_bytes_preserved": True,
                  "imports_followed": False, "services_started": False, "mounts_performed": False,
                  "triggers_evaluated": False, "properties_evaluated": False, "real_device_configs_used": False,
                  "bootability_verified": False, "effective_device_state_verified": False}, sort_keys=True))
```

## Exact expected case outcomes

```json
[
  {
    "case": "create-fictional-init-text",
    "exit_code": 0
  },
  {
    "case": "clean-literal-index-private-default",
    "exit_code": 0
  },
  {
    "case": "clean-literal-index-opt-in-details",
    "exit_code": 0
  },
  {
    "case": "duplicate-override-and-unfollowed-import-default",
    "exit_code": 1
  },
  {
    "case": "duplicate-override-and-unfollowed-import-details",
    "exit_code": 1
  },
  {
    "case": "nonliteral-lines-reset-supported-context",
    "exit_code": 1
  },
  {
    "case": "cross-file-reference-index-never-opens-targets",
    "exit_code": 1
  },
  {
    "case": "malformed-headers-do-not-capture-later-statements",
    "exit_code": 1
  },
  {
    "case": "reboot-and-restart-markers-are-declarations-only",
    "exit_code": 1
  },
  {
    "case": "literal-html-text-private-default",
    "exit_code": 0
  },
  {
    "case": "literal-details-html-escaped-argv-still-omitted",
    "exit_code": 0
  },
  {
    "case": "empty-input-is-limited-scope-success",
    "exit_code": 0
  },
  {
    "case": "comment-only-input-is-limited-scope-success",
    "exit_code": 0
  },
  {
    "case": "utf8-bom-and-crlf-supported",
    "exit_code": 0
  },
  {
    "case": "refuse-invalid-utf8",
    "exit_code": 2
  },
  {
    "case": "refuse-physical-control",
    "exit_code": 2
  },
  {
    "case": "refuse-line-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-service-collection-bound",
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
    "case": "refuse-missing-required-arguments",
    "exit_code": 2
  },
  {
    "case": "refuse-input-byte-bound",
    "exit_code": 2
  }
]
```

The summary records 24 cases: eight exit 0, six review exit 1 and ten incomplete
exit 2 results. Thirteen normal manifests cover 26 report payloads. Fourteen
selected-input hash observations, sixteen unchanged fictional fixtures and
55 exact input/report files are independently checked. Six reports use default
privacy and seven enable details; all omit raw service argv.

All eight scope fields stay false: imports followed, services started, mounts,
trigger/property evaluation, real device configs, bootability and effective
device-state verification. A unique selected declaration does not establish
effective availability; an unselected reference does not prove device absence.
Read [FORMAT.md](docs/FORMAT.md) and [QUALIFICATION.md](docs/QUALIFICATION.md).

Use trusted stable inputs and owned output parents. Snapshot/path checks and
cooperative limits are not an OS sandbox, atomic snapshot or hard native I/O
deadline. A write failure can leave a partial new report directory; preserve it,
review the cause and select another new destination after fixing the failure.
No device configuration, boot success, firmware safety or runtime acceptance
is established by this guide.
