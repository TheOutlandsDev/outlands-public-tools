# Fictional Linux and Android fstab comparison walkthrough

This guide compares invented saved before/after text only. It never mounts or
probes filesystems, changes configurations, connects devices or evaluates
effective flags. Reports describe selected parsed records, not complete device
state, source availability, runtime-equivalent behavior or bootability.

Use Python 3.12–3.15 without third-party packages. Formal guide evidence uses a
fresh no-pip CPython 3.15.2 environment with external copies of the actual three
runtime/generator files. Assertions must remain enabled. Actual CLI commands use
`-E -s -B` to retain sibling support imports while disabling environment/user
site settings and bytecode writes. The driver itself uses `-I -B`.

From the extracted module folder, save the single Python block below as
`fictional_fstab_walkthrough.py` in an existing absolute private directory
outside the source tree. Replace the fictional path with an owned directory;
do not choose links/reparse routes, network paths or actual configs. The driver
creates one new workspace and never deletes earlier evidence.

PowerShell 5.1 or newer:

```powershell
$module = (Get-Location).Path
$privateParent = 'D:\Private-Review'
python -I -B "$privateParent/fictional_fstab_walkthrough.py" "$module" "$privateParent"
```

POSIX shell, using an existing owned private directory:

```sh
module="$PWD"
privateParent="$HOME/private-review"
python3 -I -B "$privateParent/fictional_fstab_walkthrough.py" "$module" "$privateParent"
```

The generated Linux pair differs only in comments and compares cleanly. The
changed pair has an option change, added target and unique-common-target order
change. Android explicitly uses five fields and its changed pair alters only
`fs_mgr_flags`. Linux omitted dump/pass fields equal explicit leading-zero
numerals. Supported whitespace/backslash escapes decode once after splitting;
embedded `#` and nonbreaking spaces remain field data.

Other cases distinguish addition from reorder, target rename from value change,
duplicate targets on either side, ordered option text, empty/duplicate tokens,
identical unsupported rows, empty scope, BOM/CRLF and Android field-count coverage.
Duplicates never receive arbitrary pairings and are excluded from relative
order. Unsupported rows keep coverage incomplete even when input bytes match.
The order scope excludes additions, removals, ambiguity and unsupported rows.

Three default/details pairs must preserve observations after removing only
opt-in fields/mode. Defaults omit decoded values; details include selected fields,
before/after values and ambiguous targets. Literal HTML in details is escaped.
Hashes, line positions, IDs/counts and structure can identify inputs: omission
is not anonymization. Before/after must be distinct regular-file identities,
even when their bytes are identical.

The driver checks exact report fields, stdout bytes and empty stderr;
independently recomputes both input hashes/lengths and report manifest hashes;
and checks unchanged fixtures/runtime bytes, exact created files and no bytecode.
Eleven controlled refusals cover aliases, existing outputs, relative paths,
required/unknown modes and encoding/control/line/collection/file-byte bounds.
Review/incomplete exits are checked internally; the complete driver exits 0 only
when every assertion passes. Unsigned hashes establish consistency, not origin,
device correctness or redistribution permission.

## Executable driver

```python
"""Compare fictional saved fstab text only; never mount or probe its targets."""
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
work = Path(tempfile.mkdtemp(prefix="fictional-fstab-text-", dir=parent)).resolve()
assert work.parent == parent
runtime_names = ("fstab_diff.py", "text_support.py", "examples/generate.py")
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

command("create-fictional-fstab-text", "examples/generate.py", ["--output", work/"fixtures"], 0,
        {"status": "FICTIONAL_EXAMPLES_CREATED", "files": 7})
fixtures = work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"linux-before.fstab", "linux-same.fstab", "linux-changed.fstab",
    "android-before.fstab", "android-same.fstab", "android-changed.fstab", "ambiguous.fstab"}
crafted = work/"crafted"; crafted.mkdir()
escaped_rows = 'sshfs#fiction /mnt/my\\040disk fuse defaults 0 0 # fictional comment\nfictional\\134source /mnt/tab\\011name ext4 rw 0 0\nfictional-nbsp /my\u00a0disk ext4 rw\n'
values = {
    "numeric-before.fstab": b'UUID=fiction /numeric ext4 defaults\n',
    "numeric-after.fstab": b'UUID=fiction /numeric ext4 defaults 00 000\n',
    "escapes-before.fstab": escaped_rows.encode(),
    "escapes-after.fstab": ('# Fictional comment-only change.\n'+escaped_rows).encode(),
    "addition-before.fstab": b'fictional-a /a ext4 rw\nfictional-b /b ext4 rw\n',
    "addition-after.fstab": b'fictional-x /x ext4 rw\nfictional-a /a ext4 rw\nfictional-b /b ext4 rw\n',
    "rename-before.fstab": b'fictional-a /old ext4 rw\n',
    "rename-after.fstab": b'fictional-a /new ext4 rw\n',
    "duplicate-before.fstab": b'fictional-a /same ext4 rw\nfictional-b /same ext4 rw\n',
    "duplicate-after.fstab": b'fictional-a /same ext4 ro\nfictional-c /else ext4 rw\n',
    "unique-before.fstab": b'fictional-a /same ext4 rw\n',
    "options-before.fstab": b'fictional-a /options ext4 rw,noatime\n',
    "options-after.fstab": b'fictional-a /options ext4 noatime,rw\n',
    "tokens-before.fstab": b'fictional-a /tokens ext4 rw,rw,\n',
    "tokens-after.fstab": b'fictional-a /tokens ext4 rw,rw,\n',
    "unsupported-before.fstab": b'not enough fields\na /bad\\041name ext4 rw\na /numbers ext4 rw -1 0\na /ok ext4 rw\n',
    "unsupported-after.fstab": b'not enough fields\na /bad\\041name ext4 rw\na /numbers ext4 rw -1 0\na /ok ext4 rw\n',
    "html-before.fstab": b'fictional-source /html ext4 rw\n',
    "html-after.fstab": b'</pre><script>fiction</script> /html ext4 rw\n',
    "empty.fstab": b'',
    "comments.fstab": b'# Fictional comment-only file.\n',
    "bom-before.fstab": b'\xef\xbb\xbffictional-bom /bom ext4 rw\r\n',
    "bom-after.fstab": b'fictional-bom /bom ext4 rw\n',
    "android-wrong-before.fstab": b'fictional-a /android ext4 rw\n',
    "android-wrong-after.fstab": b'fictional-a /android ext4 rw wait extra\n',
    "invalid-utf8.fstab": b'\xff',
    "control.fstab": b'# fictional\x00\n',
    "line-bound.fstab": b'X'*8193,
    "record-bound.fstab": ''.join(f'fictional-{i} /bound-{i} ext4 rw\n' for i in range(4001)).encode(),
    "byte-bound.fstab": b'#'*(1024*1024+1),
}
for name, data in values.items():
    (crafted/name).write_bytes(data)
inputs = {p.relative_to(work).as_posix(): digest(p.read_bytes()) for folder in (fixtures, crafted) for p in folder.iterdir()}
assert len(inputs) == 37
reports = []; source_hashes_checked = 0; mode_counts = {"default": 0, "included": 0}

def linux(src, target, fstype="ext4", options="rw", dump=0, pass_number=0):
    return dict(source=src, target=target, fstype=fstype, options=options, dump=dump, pass_number=pass_number)
def android(src, target, fstype, options, flags):
    return dict(source=src, target=target, fstype=fstype, options=options, fs_mgr_flags=flags)
linux_fields = ["source", "target", "fstype", "options", "dump", "pass_number"]

def inspect_case(case, before, after, mode, report_name, expected_exit, groups=(), changes=(), ambiguous=(),
                 findings=(), coverage=(), reordered=False, details=False):
    global source_hashes_checked
    output = work/report_name
    expected = {"status": "NO_SCOPE_FINDINGS" if expected_exit == 0 else "REVIEW_REQUIRED",
                "changes": len(changes), "ambiguous_targets": len(ambiguous),
                "relative_order_changed": reordered, "coverage_issues": len(coverage)}
    args = ["--before", before, "--after", after, "--format", mode, "--output", output]
    if details: args.append("--include-details")
    command(case, "fstab_diff.py", args, expected_exit, expected)
    assert {p.name for p in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    raw = (output/"report.json").read_bytes(); report = json.loads(raw)
    assert set(report) == {"schema_version", "tool", "format", "scope", "details_included", "inputs", "records", "changes",
                           "ambiguous_targets", "findings", "coverage_issues", "relative_order_changed", "order_scope", "parsed_counts", "status"}
    assert report["schema_version"] == 1 and report["tool"] == "Fstab Configuration Diff" and report["format"] == mode
    assert report["scope"] == "Selected text records only; no mount, boot, filesystem or effective flag evaluation."
    assert report["status"] == expected["status"] and report["details_included"] is details
    assert report["relative_order_changed"] is reordered
    assert report["order_scope"] == "Unique common parsed targets only; additions, removals, ambiguous and unsupported rows excluded."
    expected_inputs = []
    for side, path in (("before", before), ("after", after)):
        data = path.read_bytes(); expected_inputs.append({"id": side, "bytes": len(data), "sha256": digest(data)})
        source_hashes_checked += 1
    assert report["inputs"] == expected_inputs
    expected_records = []; counts = {"before": 0, "after": 0}
    for index, rows in enumerate(groups, 1):
        for side, line, fields in rows:
            item = {"target_id": f"target-{index:04d}", "side": side, "line": line}
            if details: item["fields"] = fields
            expected_records.append(item); counts[side] += 1
    assert report["records"] == expected_records and report["parsed_counts"] == counts
    expected_changes = []
    for index, kind, fields, before_line, after_line, old, new in changes:
        item = {"target_id": f"target-{index:04d}", "kind": kind, "fields_changed": fields,
                "before_line": before_line, "after_line": after_line}
        if details: item.update(before=old, after=new)
        expected_changes.append(item)
    assert report["changes"] == expected_changes
    expected_ambiguous = []
    for index, target, before_lines, after_lines in ambiguous:
        item = {"target_id": f"target-{index:04d}", "before_lines": before_lines, "after_lines": after_lines}
        if details: item["target"] = target
        expected_ambiguous.append(item)
    assert report["ambiguous_targets"] == expected_ambiguous
    def issues(values):
        return [{"code": code, "source": side, "line": line} for code, side, line in values]
    assert report["findings"] == issues(findings) and report["coverage_issues"] == issues(coverage)
    payloads = {name: (output/name).read_bytes() for name in ("report.json", "report.html")}
    assert json.loads((output/"MANIFEST.json").read_bytes()) == {"schema_version": 1, "files": [
        {"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in sorted(payloads.items())]}
    html = payloads["report.html"].decode()
    assert "Content-Security-Policy" in html and "<script>" not in html and "&quot;schema_version&quot;" in html
    assert all(marker not in data for data in payloads.values() for marker in (str(work).encode(), str(module).encode()))
    if not details:
        assert all(marker not in raw for marker in (b"UUID=", b"fictional-", b"/dev/fictional", b"/srv/", b"<script>"))
    reports.append(report_name); mode_counts["included" if details else "default"] += 1
    return report, html

def remove_details(value):
    result = copy.deepcopy(value); result["details_included"] = False
    for row in result["records"]: row.pop("fields", None)
    for row in result["changes"]:
        row.pop("before", None); row.pop("after", None)
    for row in result["ambiguous_targets"]: row.pop("target", None)
    return result
root = linux("UUID=demo-root", "/", options="defaults", pass_number=1)
data = linux("UUID=demo-data", "/srv/demo", options="rw,noatime", pass_number=2)
data_ro = linux("UUID=demo-data", "/srv/demo", options="ro,noatime", pass_number=2)
extra = linux("UUID=demo-extra", "/srv/extra", options="defaults", pass_number=2)
inspect_case("linux-comment-only-equivalence", fixtures/"linux-before.fstab", fixtures/"linux-same.fstab", "linux", "linux-same-report", 0,
             groups=[[("before", 2, root), ("after", 2, root)], [("before", 3, data), ("after", 3, data)]])
linux_changed = dict(groups=[[("before", 2, root), ("after", 2, root)], [("before", 3, data), ("after", 1, data_ro)], [("after", 3, extra)]],
    changes=[(2, "changed", ["options"], 3, 1, data, data_ro), (3, "added", linux_fields, None, 3, None, extra)],
    findings=[("RELATIVE_RECORD_ORDER_CHANGED", "comparison", 0), ("CONFIGURATION_VALUES_CHANGED", "comparison", 0)], reordered=True)
linux_default, _ = inspect_case("linux-change-and-unique-common-order-default", fixtures/"linux-before.fstab", fixtures/"linux-changed.fstab", "linux", "linux-change-report", 1, **linux_changed)
linux_details, _ = inspect_case("linux-change-and-unique-common-order-details", fixtures/"linux-before.fstab", fixtures/"linux-changed.fstab", "linux", "linux-details-report", 1, details=True, **linux_changed)
assert remove_details(linux_details) == linux_default
old_android = android("/dev/fictional/data", "/data", "ext4", "noatime,nosuid", "wait,check")
new_android = android("/dev/fictional/data", "/data", "ext4", "noatime,nosuid", "wait,check,quota")
inspect_case("android-comment-only-equivalence", fixtures/"android-before.fstab", fixtures/"android-same.fstab", "android", "android-same-report", 0,
             groups=[[("before", 2, old_android), ("after", 1, old_android)]])
android_changed = dict(groups=[[("before", 2, old_android), ("after", 1, new_android)]],
    changes=[(1, "changed", ["fs_mgr_flags"], 2, 1, old_android, new_android)], findings=[("CONFIGURATION_VALUES_CHANGED", "comparison", 0)])
android_default, _ = inspect_case("android-fifth-field-change-default", fixtures/"android-before.fstab", fixtures/"android-changed.fstab", "android", "android-change-report", 1, **android_changed)
android_details, _ = inspect_case("android-fifth-field-change-details", fixtures/"android-before.fstab", fixtures/"android-changed.fstab", "android", "android-details-report", 1, details=True, **android_changed)
assert remove_details(android_details) == android_default
numeric = linux("UUID=fiction", "/numeric", options="defaults")
inspect_case("linux-missing-numerics-equal-explicit-leading-zeroes", crafted/"numeric-before.fstab", crafted/"numeric-after.fstab", "linux", "numeric-report", 0,
             groups=[[("before", 1, numeric), ("after", 1, numeric)]], details=True)
escaped = [linux("sshfs#fiction", "/mnt/my disk", "fuse", "defaults"), linux("fictional\\source", "/mnt/tab\tname"), linux("fictional-nbsp", "/my\u00a0disk")]
inspect_case("octal-decoding-embedded-hash-and-nonbreaking-space", crafted/"escapes-before.fstab", crafted/"escapes-after.fstab", "linux", "escapes-report", 0,
             groups=[[("before", i, fields), ("after", i+1, fields)] for i, fields in enumerate(escaped, 1)], details=True)
a = linux("fictional-a", "/a"); b = linux("fictional-b", "/b"); x = linux("fictional-x", "/x")
inspect_case("addition-alone-is-not-common-target-reorder", crafted/"addition-before.fstab", crafted/"addition-after.fstab", "linux", "addition-report", 1,
    groups=[[("before", 1, a), ("after", 2, a)], [("before", 2, b), ("after", 3, b)], [("after", 1, x)]],
    changes=[(3, "added", linux_fields, None, 1, None, x)], findings=[("CONFIGURATION_VALUES_CHANGED", "comparison", 0)])
old = linux("fictional-a", "/old"); new = linux("fictional-a", "/new")
inspect_case("target-rename-is-removal-and-addition", crafted/"rename-before.fstab", crafted/"rename-after.fstab", "linux", "rename-report", 1,
    groups=[[("before", 1, old)], [("after", 1, new)]], changes=[(1, "removed", linux_fields, 1, None, old, None), (2, "added", linux_fields, None, 1, None, new)],
    findings=[("CONFIGURATION_VALUES_CHANGED", "comparison", 0)])
dup_a = linux("fictional-a", "/same"); dup_b = linux("fictional-b", "/same"); dup_ro = linux("fictional-a", "/same", options="ro"); other = linux("fictional-c", "/else")
inspect_case("before-duplicates-held-without-arbitrary-pairing", crafted/"duplicate-before.fstab", crafted/"duplicate-after.fstab", "linux", "duplicate-before-report", 1,
    groups=[[("before", 1, dup_a), ("before", 2, dup_b), ("after", 1, dup_ro)], [("after", 2, other)]],
    ambiguous=[(1, "/same", [1, 2], [1])], changes=[(2, "added", linux_fields, None, 2, None, other)], findings=[
        ("AMBIGUOUS_TARGET_NO_PAIRING", "before", 1), ("AMBIGUOUS_TARGET_NO_PAIRING", "before", 2),
        ("AMBIGUOUS_TARGET_NO_PAIRING", "after", 1), ("CONFIGURATION_VALUES_CHANGED", "comparison", 0)], details=True)
inspect_case("after-only-duplicates-excluded-from-pairing-and-order", crafted/"unique-before.fstab", crafted/"duplicate-before.fstab", "linux", "duplicate-after-report", 1,
    groups=[[("before", 1, dup_a), ("after", 1, dup_a), ("after", 2, dup_b)]], ambiguous=[(1, "/same", [1], [1, 2])], findings=[
        ("AMBIGUOUS_TARGET_NO_PAIRING", "before", 1), ("AMBIGUOUS_TARGET_NO_PAIRING", "after", 1), ("AMBIGUOUS_TARGET_NO_PAIRING", "after", 2)])
opt_old = linux("fictional-a", "/options", options="rw,noatime"); opt_new = linux("fictional-a", "/options", options="noatime,rw")
inspect_case("option-order-is-text-not-effective-semantics", crafted/"options-before.fstab", crafted/"options-after.fstab", "linux", "option-order-report", 1,
    groups=[[("before", 1, opt_old), ("after", 1, opt_new)]], changes=[(1, "changed", ["options"], 1, 1, opt_old, opt_new)],
    findings=[("CONFIGURATION_VALUES_CHANGED", "comparison", 0)], details=True)
tokens = linux("fictional-a", "/tokens", options="rw,rw,")
inspect_case("identical-empty-duplicate-option-tokens-still-findings", crafted/"tokens-before.fstab", crafted/"tokens-after.fstab", "linux", "tokens-report", 1,
    groups=[[("before", 1, tokens), ("after", 1, tokens)]], findings=[(code, side, 1) for side in ("before", "after") for code in ("EMPTY_OPTION_TOKEN", "DUPLICATE_OPTION_TOKEN")], details=True)
ok = linux("a", "/ok")
inspect_case("identical-unsupported-rows-remain-coverage", crafted/"unsupported-before.fstab", crafted/"unsupported-after.fstab", "linux", "unsupported-report", 1,
    groups=[[("before", 4, ok), ("after", 4, ok)]], coverage=[(code, side, line) for side in ("before", "after")
        for code, line in (("UNSUPPORTED_FIELD_COUNT", 1), ("UNSUPPORTED_FIELD_ESCAPE", 2), ("UNSUPPORTED_NUMERIC_FIELD", 3))])
html_old = linux("fictional-source", "/html"); html_new = linux("</pre><script>fiction</script>", "/html")
html_args = dict(groups=[[("before", 1, html_old), ("after", 1, html_new)]], changes=[(1, "changed", ["source"], 1, 1, html_old, html_new)],
                 findings=[("CONFIGURATION_VALUES_CHANGED", "comparison", 0)])
html_default, _ = inspect_case("literal-html-source-private-default", crafted/"html-before.fstab", crafted/"html-after.fstab", "linux", "html-default-report", 1, **html_args)
html_details, html = inspect_case("literal-details-html-escaped", crafted/"html-before.fstab", crafted/"html-after.fstab", "linux", "html-details-report", 1, details=True, **html_args)
assert remove_details(html_details) == html_default and "&lt;script&gt;fiction&lt;/script&gt;" in html
inspect_case("empty-versus-comment-only-is-limited-scope-success", crafted/"empty.fstab", crafted/"comments.fstab", "linux", "empty-report", 0)
bom = linux("fictional-bom", "/bom")
inspect_case("utf8-bom-and-crlf-supported", crafted/"bom-before.fstab", crafted/"bom-after.fstab", "linux", "bom-report", 0,
             groups=[[("before", 1, bom), ("after", 1, bom)]])
inspect_case("android-requires-exactly-five-fields", crafted/"android-wrong-before.fstab", crafted/"android-wrong-after.fstab", "android", "android-fields-report", 1,
             coverage=[("UNSUPPORTED_FIELD_COUNT", "before", 1), ("UNSUPPORTED_FIELD_COUNT", "after", 1)])

def refusal(case, before, after, code, output=None, mode="linux"):
    args = ["--before", before, "--after", after, "--output", output or work/(case+"-output")]
    if mode is not None: args.extend(["--format", mode])
    command(case, "fstab_diff.py", args, 2, {"status": "INCOMPLETE", "error": code})
refusal("refuse-before-after-same-file-alias", fixtures/"linux-before.fstab", fixtures/"linux-before.fstab", "DUPLICATE_INPUT_FILE")
refusal("refuse-existing-report", fixtures/"linux-before.fstab", fixtures/"linux-same.fstab", "OUTPUT_EXISTS", output=work/"linux-same-report")
command("refuse-existing-generator-directory", "examples/generate.py", ["--output", fixtures], 2, {"status": "INCOMPLETE", "error": "OUTPUT_EXISTS"})
refusal("refuse-relative-before-input", "relative.fstab", fixtures/"linux-same.fstab", "LOCAL_ABSOLUTE_PATH_REQUIRED")
refusal("refuse-missing-explicit-format", fixtures/"linux-before.fstab", fixtures/"linux-same.fstab", "ARGUMENTS_INVALID", mode=None)
refusal("refuse-unknown-format", fixtures/"linux-before.fstab", fixtures/"linux-same.fstab", "ARGUMENTS_INVALID", mode="guess")
refusal("refuse-invalid-utf8", crafted/"invalid-utf8.fstab", crafted/"empty.fstab", "UTF8_REQUIRED")
refusal("refuse-physical-control", crafted/"control.fstab", crafted/"empty.fstab", "TEXT_CONTROL_UNSUPPORTED")
refusal("refuse-physical-line-bound", crafted/"line-bound.fstab", crafted/"empty.fstab", "TEXT_LINE_LIMIT")
refusal("refuse-record-collection-bound", crafted/"record-bound.fstab", crafted/"empty.fstab", "RECORD_LIMIT")
refusal("refuse-input-byte-bound", crafted/"byte-bound.fstab", crafted/"empty.fstab", "INPUT_BYTE_LIMIT")
assert inputs == {name: digest((work/name).read_bytes()) for name in inputs}
assert runtime == {name: digest((module/name).read_bytes()) for name in runtime_names}
expected_files = set(inputs) | {name+"/"+file for name in reports for file in ("report.json", "report.html", "MANIFEST.json")}
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()} == expected_files
assert len(reports) == 20 and len(expected_files) == 97 and source_hashes_checked == 40
assert mode_counts == {"default": 12, "included": 8}
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
print(json.dumps({"outcomes": outcomes, "reports_verified": 20, "payload_hashes_verified": 40,
                  "before_after_hashes_checked": 40, "fixture_files_preserved": 37, "expected_workspace_files": 97,
                  "unexpected_application_files": 0, "details_mode_counts": mode_counts,
                  "details_do_not_change_observations": True, "bytecode_files": 0, "runtime_bytes_preserved": True,
                  "filesystems_mounted": False, "filesystems_probed": False, "configurations_modified": False,
                  "devices_connected": False, "real_device_configs_used": False, "bootability_verified": False,
                  "effective_flags_evaluated": False, "effective_device_state_verified": False}, sort_keys=True))
```

## Exact expected case outcomes

```json
[
  {
    "case": "create-fictional-fstab-text",
    "exit_code": 0
  },
  {
    "case": "linux-comment-only-equivalence",
    "exit_code": 0
  },
  {
    "case": "linux-change-and-unique-common-order-default",
    "exit_code": 1
  },
  {
    "case": "linux-change-and-unique-common-order-details",
    "exit_code": 1
  },
  {
    "case": "android-comment-only-equivalence",
    "exit_code": 0
  },
  {
    "case": "android-fifth-field-change-default",
    "exit_code": 1
  },
  {
    "case": "android-fifth-field-change-details",
    "exit_code": 1
  },
  {
    "case": "linux-missing-numerics-equal-explicit-leading-zeroes",
    "exit_code": 0
  },
  {
    "case": "octal-decoding-embedded-hash-and-nonbreaking-space",
    "exit_code": 0
  },
  {
    "case": "addition-alone-is-not-common-target-reorder",
    "exit_code": 1
  },
  {
    "case": "target-rename-is-removal-and-addition",
    "exit_code": 1
  },
  {
    "case": "before-duplicates-held-without-arbitrary-pairing",
    "exit_code": 1
  },
  {
    "case": "after-only-duplicates-excluded-from-pairing-and-order",
    "exit_code": 1
  },
  {
    "case": "option-order-is-text-not-effective-semantics",
    "exit_code": 1
  },
  {
    "case": "identical-empty-duplicate-option-tokens-still-findings",
    "exit_code": 1
  },
  {
    "case": "identical-unsupported-rows-remain-coverage",
    "exit_code": 1
  },
  {
    "case": "literal-html-source-private-default",
    "exit_code": 1
  },
  {
    "case": "literal-details-html-escaped",
    "exit_code": 1
  },
  {
    "case": "empty-versus-comment-only-is-limited-scope-success",
    "exit_code": 0
  },
  {
    "case": "utf8-bom-and-crlf-supported",
    "exit_code": 0
  },
  {
    "case": "android-requires-exactly-five-fields",
    "exit_code": 1
  },
  {
    "case": "refuse-before-after-same-file-alias",
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
    "case": "refuse-relative-before-input",
    "exit_code": 2
  },
  {
    "case": "refuse-missing-explicit-format",
    "exit_code": 2
  },
  {
    "case": "refuse-unknown-format",
    "exit_code": 2
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
    "case": "refuse-physical-line-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-record-collection-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-input-byte-bound",
    "exit_code": 2
  }
]
```

The summary records 32 cases: seven exit 0, fourteen review exit 1 and eleven
incomplete exit 2 results. Twenty normal manifests cover forty report payloads.
Forty independent before/after hash observations, 37 unchanged fictional fixtures
and 97 exact input/report files are checked. Twelve reports use defaults and
eight request details; three pairs preserve observations.

All eight scope fields remain false: filesystem mounting/probing, configuration
modification, devices connected, real device configs, bootability, effective
flags and effective device-state verification. Empty/comment-only inputs can
exit 0 without proving completeness. Read [FORMAT.md](docs/FORMAT.md) and
[QUALIFICATION.md](docs/QUALIFICATION.md).

Use trusted stable inputs and owned parents. Snapshot/path checks and
cooperative limits are not an OS sandbox, atomic snapshot or hard native I/O
deadline. A write failure can leave a partial new report; preserve it, review
the cause and choose a new destination after fixing the failure. No actual
filesystem, device, boot or runtime acceptance is certified here.
