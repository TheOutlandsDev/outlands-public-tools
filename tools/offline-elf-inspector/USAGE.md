# Fictional offline ELF walkthrough

Extract the [Offline ELF Dependency Inspector 1.1.0 source ZIP](https://github.com/TheOutlandsDev/outlands-public-tools/releases/tag/offline-elf-inspector-v1.1.0), verify SHA256SUMS and supply ordinary CPython 3.12, 3.13, 3.14 or 3.15. Qualification selects 3.15.2 for that minor. Runtime version 1.1.0 is preserved. No Python packages, compiler, readelf, WSL, device, firmware or native parser dependency is needed for this exercise. The source ZIP includes no interpreter or ELF binary.

Choose an existing trusted private parent outside the source checkout and public/synchronized folders. Every demo/report destination is new. Replace the fictional absolute source/private paths below with your actual selected paths and Python. The optional no-pip environment installs no dependencies and requires no activation, administrator privilege, account login or execution-policy change. Actual permissions and workplace policies still apply.

PowerShell:

```powershell
$source = 'D:\Source\offline-elf-inspector-1.1.0'
$privateWork = 'D:\Private\elf-review'
python -I -B -m venv --without-pip (Join-Path $privateWork 'new-environment')
$py = Join-Path $privateWork 'new-environment\Scripts\python.exe'
& $py -I -B (Join-Path $source 'elf_inspector.py') --version
& $py -I -B (Join-Path $source 'elf_inspector.py') --help
```

Ubuntu:

```sh
source=/path/to/offline-elf-inspector-1.1.0
private_work=/path/to/private-elf-review
python3 -I -B -m venv --without-pip "$private_work/new-environment"
py="$private_work/new-environment/bin/python"
"$py" -I -B "$source/elf_inspector.py" --version
"$py" -I -B "$source/elf_inspector.py" --help
```

## Run all thirteen cases unchanged

Save the single Python block below as `fictional_walkthrough.py` in your private parent and run with assertions enabled. It authors metadata and padding using struct, invokes the preserved demo generator three times and retains seventeen invented input files. These are not loader-valid test programs and contain no authored executable machine code. No generated or inspected ELF is loaded or executed, and no real application, phone file, firmware or third-party binary is used.

The three demos exercise clean candidate cycles, mixed ambiguity/missing/architecture findings and clean bytes with optional hint text. Default and hint-enabled inspections are separate; their declared graphs must remain identical. One ELF32 big-endian fixture exercises complete JSON stdout. A truncated fixture produces a complete review report, rather than a successful compatibility claim.

Five report directories each contain report.json, index.html, README.txt and MANIFEST.json. The exercise compares whole structured report bytes against its explicit fictional metadata expectations, checks complete stdout/stderr bytes and statuses, parses only generated static HTML markup, and independently verifies all fifteen payload byte lengths/hashes. No browser, native loader or hinted path is opened. Existing inputs/reports and runtime bytes must stay unchanged; exact final workspace contents and absence of bytecode/unexpected files are checked.

The thirteen outcomes are seven exit 0, two expected review exit 2 and four controlled error exit 1. The four errors write complete JSON to stderr with empty stdout. Python argparse usage errors also use exit 2, but are a different contract and are not these review outcomes. Do not treat exit 2 alone as evidence of a complete report without checking its output/status.

PowerShell:

```powershell
& $py -I -B (Join-Path $privateWork 'fictional_walkthrough.py') $source $privateWork
```

Ubuntu:

```sh
"$py" -I -B "$private_work/fictional_walkthrough.py" "$source" "$private_work"
```

```python
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

if not __debug__:
    raise RuntimeError("ASSERTIONS_REQUIRED")

NOTE = "Candidates in explicit local inputs only. No loader, linker namespaces, symbol/ABI compatibility, dlopen or runtime success is verified."
HINT_NOTE = "ASCII token observations only. They may be unused, incomplete or coincidental; they do not prove dependencies, missing files, runtime loading or configuration use. No hinted path is opened."
README = b"Private local metadata report. No inspected binaries are included. This is not a backup, runtime compatibility check or software license clearance. Review filenames, embedded paths and any optional hint tokens before sharing.\n"
TAIL = b"\x00liboptional_effects.so.2\x00/vendor/etc/fictional-demo.xml\x00/vendor/firmware/fictional-demo.bin\x00"
COUNT_KEYS = ("unique_metadata_candidate", "ambiguous_candidates", "architecture_mismatch",
              "object_type_mismatch", "unresolved_in_supplied_inputs", "path_dependency_not_resolved")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")

def authored_elf(needed=(), soname="", bits=64, endian="little", runpath="", interpreter=""):
    # Author known metadata and padding with struct. These are not test programs.
    order = "<" if endian == "little" else ">"
    strings = bytearray(b"\x00")
    tags = []
    for tag, value in [(1, name) for name in needed] + ([(14, soname)] if soname else []) + ([(29, runpath)] if runpath else []):
        position = len(strings)
        strings.extend(value.encode("utf-8") + b"\x00")
        tags.append((tag, position))
    unit = 8 if bits == 32 else 16
    dynamic_size = (len(tags) + 3) * unit
    string_offset = ((512 + dynamic_size + 63) // 64) * 64
    interpreter_bytes = interpreter.encode("utf-8") + b"\x00" if interpreter else b""
    interpreter_offset = ((string_offset + len(strings) + 63) // 64) * 64
    total = max(string_offset + len(strings), interpreter_offset + len(interpreter_bytes))
    header_size, ph_size = (52, 32) if bits == 32 else (64, 56)
    ph_count = 2 + int(bool(interpreter))
    data = bytearray(total)
    data[:16] = b"\x7fELF" + bytes([1 if bits == 32 else 2, 1 if endian == "little" else 2, 1, 0, 0]) + bytes(7)
    header = (3, 40 if bits == 32 else 183, 1, 0, header_size, 0, 0, header_size, ph_size, ph_count, 0, 0, 0)
    struct.pack_into(order + ("HHIIIIIHHHHHH" if bits == 32 else "HHIQQQIHHHHHH"), data, 16, *header)
    segments = [(1, 0, 65536, total), (2, 512, 66048, dynamic_size)]
    if interpreter:
        segments.append((3, interpreter_offset, 65536 + interpreter_offset, len(interpreter_bytes)))
    for index, (kind, offset, address, size) in enumerate(segments):
        values = (kind, offset, address, 0, size, size, 4, 1) if bits == 32 else (kind, 4, offset, address, 0, size, size, 1)
        struct.pack_into(order + ("IIIIIIII" if bits == 32 else "IIQQQQQQ"), data, header_size + index * ph_size, *values)
    for index, pair in enumerate(tags + [(5, 65536 + string_offset), (10, len(strings)), (0, 0)]):
        struct.pack_into(order + ("iI" if bits == 32 else "qQ"), data, 512 + index * unit, *pair)
    data[string_offset:string_offset + len(strings)] = strings
    if interpreter:
        data[interpreter_offset:interpreter_offset + len(interpreter_bytes)] = interpreter_bytes
    reads = 4 + header_size + ph_size * ph_count + dynamic_size + len(strings) + len(interpreter_bytes)
    return bytes(data), reads

def example_plan(mixed=False, hinted=False):
    needed = ("libdemo.so", "libchoice.so", "libabsent.so", "libwrong.so") if mixed else ("libdemo.so",)
    specs = {"app/demo.elf": dict(needed=needed, runpath="$ORIGIN/../lib", interpreter="/fictional/linker64"),
             "lib/libdemo-real.so": dict(needed=("libleaf.so",), soname="libdemo.so"),
             "lib/libleaf.so": dict(needed=("libdemo.so",), soname="libleaf.so")}
    if mixed:
        specs.update({"lib/choice-a.so": dict(soname="libchoice.so"),
                      "lib/choice-b.so": dict(soname="libchoice.so"),
                      "lib/libwrong.so": dict(soname="libwrong.so", bits=32)})
    files, reads = {}, {}
    for name, spec in specs.items():
        files[name], reads[name] = authored_elf(**spec)
    if hinted:
        files["app/demo.elf"] += TAIL
    files["lib/not-elf.txt"] = b"Fictional non-ELF file; ignored by metadata discovery.\n"
    return files, specs, reads

def node(label, name, raw, spec, hints=False):
    bits = spec.get("bits", 64)
    value = dict(id=label, name=name, **{"class": bits}, endian=spec.get("endian", "little"),
        machine=40 if bits == 32 else 183, machine_name="ARM" if bits == 32 else "AArch64",
        osabi=0, abi_version=0, flags=0, type="DYN", interpreter=spec.get("interpreter", ""),
        soname=spec.get("soname", ""), needed=list(spec.get("needed", ())), rpath="",
        runpath=spec.get("runpath", ""), metadata="dynamic_segment", bytes=len(raw), sha256=sha(raw))
    if hints:
        tokens = [("library_text", text) for text in set(value["needed"] + ([value["soname"]] if value["soname"] else []))]
        if name == "demo.elf":
            tokens += [("library_text", "liboptional_effects.so.2"),
                       ("config_or_firmware_path_text", "/vendor/etc/fictional-demo.xml"),
                       ("config_or_firmware_path_text", "/vendor/firmware/fictional-demo.bin")]
        observations = [dict(kind=kind, text=text, first_offset=raw.index(text.encode()), occurrences=raw.count(text.encode()))
                        for kind, text in sorted(tokens)]
        value["runtime_hint_scan"] = dict(coverage="complete_ascii_scan", bytes_scanned=len(raw),
            file_bytes=len(raw), reasons=[], overlong_ascii_runs_omitted=0, observations=observations)
    return value

def summary(files, entries, elfs, ignored, visited, edges, issues, metadata, hashed, **counts):
    return dict(files_examined=files, directory_entries=entries, elf_files=elfs, non_elf_ignored=ignored,
        visited_in_graph=visited, dependency_edges=edges, issue_count=issues, issues_omitted=0,
        metadata_bytes_read=metadata, hash_bytes_read=hashed,
        **{name: counts.get(name, 0) for name in COUNT_KEYS})

def report_base(status, counts, roots, entries, nodes, edges=(), issues=()):
    return dict(schema="outlands-offline-elf-dependencies/1", tool_version="1.1.0", status=status,
        interpretation=NOTE, limits=dict(files=2000, entries=20000, depth=32, seconds=60), summary=counts,
        roots=roots, entry_files=entries, files=nodes, dependencies=list(edges), issues=list(issues))

def demo_report(mixed=False, hinted_bytes=False, hints=False):
    files, specs, reads = example_plan(mixed, hinted_bytes)
    labels = {name: "selected-1/demo.elf" if name == "app/demo.elf" else "root-1/" + name.split("/")[-1] for name in specs}
    nodes = sorted([node(labels[name], name.split("/")[-1], files[name], spec, hints)
                    for name, spec in specs.items()], key=lambda value: value["id"])
    edges = []
    for consumer, needed, candidates, state in [
        ("selected-1/demo.elf", "libdemo.so", ["root-1/libdemo-real.so"], "unique_metadata_candidate"),
        ("root-1/libdemo-real.so", "libleaf.so", ["root-1/libleaf.so"], "unique_metadata_candidate"),
        ("root-1/libleaf.so", "libdemo.so", ["root-1/libdemo-real.so"], "unique_metadata_candidate")
    ] + ([
        ("selected-1/demo.elf", "libchoice.so", ["root-1/choice-a.so", "root-1/choice-b.so"], "ambiguous_candidates"),
        ("selected-1/demo.elf", "libabsent.so", [], "unresolved_in_supplied_inputs"),
        ("selected-1/demo.elf", "libwrong.so", ["root-1/libwrong.so"], "architecture_mismatch")
    ] if mixed else []):
        edges.append(dict(consumer=consumer, needed=needed, status=state,
            candidate=candidates[0] if state == "unique_metadata_candidate" else None,
            candidate_count=len(candidates), candidates=candidates, candidates_omitted=0))
    counts = summary(len(files), len(files) - 1, len(specs), 1, 3, len(edges), 0,
        sum(reads.values()) + 4, sum(len(files[name]) for name in specs),
        unique_metadata_candidate=3, ambiguous_candidates=int(mixed),
        architecture_mismatch=int(mixed), unresolved_in_supplied_inputs=int(mixed))
    report = report_base("REVIEW_REQUIRED" if mixed else "NO_SCOPE_FINDINGS", counts, ["root-1"],
        ["selected-1/demo.elf"], nodes, sorted(edges, key=lambda value: (value["consumer"], value["needed"])))
    if hints:
        report["runtime_hints"] = dict(interpretation=HINT_NOTE,
            limits=dict(file_bytes=8388608, total_bytes=67108864, ascii_run_bytes=1024,
                        observations_per_file=128, total_observations=2000),
            files_scanned=3, bytes_scanned=sum(len(files[name]) for name in specs), observation_slots_used=8,
            observations=8, files_with_partial_hint_coverage=0)
    return report

def stdout_report():
    raw, reads = authored_elf(bits=32, endian="big")
    counts = summary(1, 0, 1, 0, 1, 0, 0, reads, len(raw))
    return report_base("NO_SCOPE_FINDINGS", counts, [], ["selected-1/declared-32-big.elf"],
        [node("selected-1/declared-32-big.elf", "declared-32-big.elf", raw, dict(bits=32, endian="big"))])

def malformed_report():
    return report_base("REVIEW_REQUIRED", summary(1, 0, 0, 0, 0, 0, 2, 4, 0), [], [], [],
        issues=[dict(location="scan", code="NO_SUPPORTED_ELF_FILES"),
                dict(location="selected-1/malformed.elf", code="ELF_RANGE_OUTSIDE_FILE")])

def outcomes():
    rows = []
    for label, mixed in (("create-clean-demo", False), ("create-mixed-demo", True), ("create-hinted-demo", False)):
        rows.append(dict(case=label, exit_code=0,
            stdout=dict(files=7 if mixed else 4, fixture="mixed" if mixed else "clean", machine_code=False), stderr=None))
    for label, report in (("clean-output", demo_report()), ("mixed-output", demo_report(True)),
        ("hinted-default", demo_report(hinted_bytes=True)), ("hints-enabled", demo_report(hinted_bytes=True, hints=True))):
        rows.append(dict(case=label, exit_code=2 if report["status"] == "REVIEW_REQUIRED" else 0,
            stdout=dict(status=report["status"], report_files=4, summary=report["summary"]), stderr=None))
    rows.append(dict(case="elf32-big-json-stdout", exit_code=0, stdout=stdout_report(), stderr=None))
    bad = malformed_report()
    rows.append(dict(case="malformed-review", exit_code=2,
        stdout=dict(status=bad["status"], report_files=4, summary=bad["summary"]), stderr=None))
    for label, code in (("refuse-existing-output", "OUTPUT_MUST_BE_NEW_DIRECTORY"),
        ("refuse-scan-root-output", "OUTPUT_MUST_BE_OUTSIDE_SCAN_ROOTS"),
        ("refuse-duplicate-roots", "ROOTS_MUST_BE_DISJOINT"),
        ("refuse-no-selection", "SELECT_AT_LEAST_ONE_ROOT_OR_FILE")):
        rows.append(dict(case=label, exit_code=1, stdout=None, stderr=dict(status="ERROR", code=code)))
    return rows

class StaticHTML(HTMLParser):
    def handle_starttag(self, tag, attrs):
        assert tag in {"html", "head", "meta", "title", "style", "body", "main", "h1", "h2", "p",
            "nav", "a", "div", "strong", "details", "summary", "table", "thead", "tr", "th", "tbody", "td"}, tag
        assert not any(name.lower().startswith("on") or name in {"src", "srcdoc"} for name, value in attrs)
        for name, value in attrs:
            if name == "href":
                assert tag == "a" and value in {"#dependencies", "#metadata", "#coverage"}

def main():
    assert len(sys.argv) == 3
    source, parent = map(lambda value: Path(value).resolve(), sys.argv[1:])
    assert source.is_dir() and parent.is_dir()
    assert not parent.is_symlink() and not getattr(parent, "is_junction", lambda: False)()
    pins = {name: sha((source / name).read_bytes()) for name in ("elf_inspector.py", "examples/make_demo.py")}
    work = Path(tempfile.mkdtemp(prefix="fictional-elf-", dir=parent))
    assert not work.is_relative_to(source)
    protected, observed = {}, []
    def metadata(path):
        value = path.stat()
        return (value.st_size, value.st_mtime_ns, value.st_ino, value.st_nlink,
                value.st_birthtime_ns if os.name == "nt" else value.st_ctime_ns)
    def protect(root):
        for path in root.rglob("*") if root.is_dir() else [root]:
            if path.is_file():
                protected[path] = (path.read_bytes(), metadata(path))
    expected_rows = {value["case"]: value for value in outcomes()}
    def invoke(label, program, args, pretty=False):
        expected = expected_rows[label]
        done = subprocess.run([sys.executable, "-I", "-B", str(source / program), *map(str, args)],
            cwd=work, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        assert done.returncode == expected["exit_code"], label
        for stream in ("stdout", "stderr"):
            wanted = expected[stream]
            text = "" if wanted is None else ((encoded(wanted).decode() if pretty else json.dumps(wanted) + "\n").replace("\n", os.linesep))
            assert getattr(done, stream) == text.encode("utf-8"), (label, stream)
        assert all(path.read_bytes() == value[0] and metadata(path) == value[1] for path, value in protected.items()), label
        assert pins == {name: sha((source / name).read_bytes()) for name in pins}
        observed.append(expected)
    clean, mixed, hinted = [work / name for name in ("clean-demo", "mixed-demo", "hinted-demo")]
    for label, destination, options, mixed_flag, hints_flag in (
        ("create-clean-demo", clean, ["--clean"], False, False),
        ("create-mixed-demo", mixed, [], True, False),
        ("create-hinted-demo", hinted, ["--clean", "--runtime-hints"], False, True)):
        invoke(label, "examples/make_demo.py", ["--destination", destination, *options])
        expected_files = example_plan(mixed_flag, hints_flag)[0]
        assert {path.relative_to(destination).as_posix(): path.read_bytes() for path in destination.rglob("*") if path.is_file()} == expected_files
        protect(destination)
    wide = work / "declared-32-big.elf"
    wide.write_bytes(authored_elf(bits=32, endian="big")[0])
    malformed = work / "malformed.elf"
    malformed.write_bytes(b"\x7fELF")
    protect(wide)
    protect(malformed)
    reports = []
    def check_report(output, expected):
        assert {path.name for path in output.iterdir()} == {"report.json", "index.html", "README.txt", "MANIFEST.json"}
        payloads = {name: (output / name).read_bytes() for name in ("report.json", "index.html", "README.txt")}
        assert payloads["report.json"] == encoded(expected)
        assert payloads["README.txt"] == README
        manifest = dict(schema="outlands-elf-report-files/1", files=[dict(path=name, bytes=len(data), sha256=sha(data)) for name, data in sorted(payloads.items())])
        assert (output / "MANIFEST.json").read_bytes() == encoded(manifest)
        markup = payloads["index.html"].decode("utf-8")
        parser = StaticHTML(convert_charrefs=True)
        parser.feed(markup)
        parser.close()
        assert "<script" not in markup.lower() and "<iframe" not in markup.lower()
        assert "default-src 'none'" in markup and "url(" not in markup.lower()
        assert str(work) not in markup and str(work) not in payloads["report.json"].decode()
        reports.append(output)
        protect(output)
    for label, root, expected, options in (
        ("clean-output", clean, demo_report(), []),
        ("mixed-output", mixed, demo_report(True), []),
        ("hinted-default", hinted, demo_report(hinted_bytes=True), []),
        ("hints-enabled", hinted, demo_report(hinted_bytes=True, hints=True), ["--runtime-hints"])):
        output = work / (label + "-report")
        invoke(label, "elf_inspector.py", ["--file", root / "app/demo.elf", "--root", root / "lib", "--sha256", "--output", output, *options])
        check_report(output, expected)
    default = demo_report(hinted_bytes=True)
    enabled = demo_report(hinted_bytes=True, hints=True)
    assert default["dependencies"] == enabled["dependencies"] and default["summary"] == enabled["summary"]
    assert "runtime_hints" not in default and all("runtime_hint_scan" not in value for value in default["files"])
    invoke("elf32-big-json-stdout", "elf_inspector.py", ["--file", wide, "--sha256"], pretty=True)
    bad_output = work / "malformed-review-report"
    invoke("malformed-review", "elf_inspector.py", ["--file", malformed, "--sha256", "--output", bad_output])
    check_report(bad_output, malformed_report())
    invoke("refuse-existing-output", "elf_inspector.py", ["--file", clean / "app/demo.elf", "--root", clean / "lib", "--output", work / "clean-output-report"])
    invoke("refuse-scan-root-output", "elf_inspector.py", ["--root", clean / "lib", "--output", clean / "lib/new-report"])
    invoke("refuse-duplicate-roots", "elf_inspector.py", ["--root", clean / "lib", "--root", clean / "lib", "--output", work / "not-created-roots-report"])
    invoke("refuse-no-selection", "elf_inspector.py", ["--output", work / "not-created-selection-report"])
    assert {path.name for path in work.iterdir()} == {"clean-demo", "mixed-demo", "hinted-demo", "declared-32-big.elf", "malformed.elf",
        "clean-output-report", "mixed-output-report", "hinted-default-report", "hints-enabled-report", "malformed-review-report"}
    assert len([path for path in work.rglob("*") if path.is_file()]) == 37
    assert not list(work.rglob("*.pyc")) and not list(work.rglob("__pycache__"))
    assert observed == outcomes() and len(reports) == 5
    print(json.dumps(dict(outcomes=observed, reports_verified=5, payload_hashes_verified=15,
        fixture_files_preserved=17, expected_workspace_files=37, unexpected_application_files=0,
        bytecode_files=0, runtime_bytes_preserved=True, elf_loaded_or_executed=False,
        real_phone_or_application_data_used=False), sort_keys=True, indent=2))

if __name__ == "__main__":
    main()
```

## Complete CLI outcomes

Each stdout/stderr object below is the entire decoded JSON output for that invocation; null means an empty stream. The ELF32 big-endian stdout case includes the complete report. The wrapper also checks exact formatting and native line endings. These hashes and labels describe only the exact invented bytes in this guide.

```json
[
  {
    "case": "create-clean-demo",
    "exit_code": 0,
    "stdout": {
      "files": 4,
      "fixture": "clean",
      "machine_code": false
    },
    "stderr": null
  },
  {
    "case": "create-mixed-demo",
    "exit_code": 0,
    "stdout": {
      "files": 7,
      "fixture": "mixed",
      "machine_code": false
    },
    "stderr": null
  },
  {
    "case": "create-hinted-demo",
    "exit_code": 0,
    "stdout": {
      "files": 4,
      "fixture": "clean",
      "machine_code": false
    },
    "stderr": null
  },
  {
    "case": "clean-output",
    "exit_code": 0,
    "stdout": {
      "status": "NO_SCOPE_FINDINGS",
      "report_files": 4,
      "summary": {
        "files_examined": 4,
        "directory_entries": 3,
        "elf_files": 3,
        "non_elf_ignored": 1,
        "visited_in_graph": 3,
        "dependency_edges": 3,
        "issue_count": 0,
        "issues_omitted": 0,
        "metadata_bytes_read": 933,
        "hash_bytes_read": 2132,
        "unique_metadata_candidate": 3,
        "ambiguous_candidates": 0,
        "architecture_mismatch": 0,
        "object_type_mismatch": 0,
        "unresolved_in_supplied_inputs": 0,
        "path_dependency_not_resolved": 0
      }
    },
    "stderr": null
  },
  {
    "case": "mixed-output",
    "exit_code": 2,
    "stdout": {
      "status": "REVIEW_REQUIRED",
      "report_files": 4,
      "summary": {
        "files_examined": 7,
        "directory_entries": 6,
        "elf_files": 6,
        "non_elf_ignored": 1,
        "visited_in_graph": 3,
        "dependency_edges": 6,
        "issue_count": 0,
        "issues_omitted": 0,
        "metadata_bytes_read": 1700,
        "hash_bytes_read": 4116,
        "unique_metadata_candidate": 3,
        "ambiguous_candidates": 1,
        "architecture_mismatch": 1,
        "object_type_mismatch": 0,
        "unresolved_in_supplied_inputs": 1,
        "path_dependency_not_resolved": 0
      }
    },
    "stderr": null
  },
  {
    "case": "hinted-default",
    "exit_code": 0,
    "stdout": {
      "status": "NO_SCOPE_FINDINGS",
      "report_files": 4,
      "summary": {
        "files_examined": 4,
        "directory_entries": 3,
        "elf_files": 3,
        "non_elf_ignored": 1,
        "visited_in_graph": 3,
        "dependency_edges": 3,
        "issue_count": 0,
        "issues_omitted": 0,
        "metadata_bytes_read": 933,
        "hash_bytes_read": 2225,
        "unique_metadata_candidate": 3,
        "ambiguous_candidates": 0,
        "architecture_mismatch": 0,
        "object_type_mismatch": 0,
        "unresolved_in_supplied_inputs": 0,
        "path_dependency_not_resolved": 0
      }
    },
    "stderr": null
  },
  {
    "case": "hints-enabled",
    "exit_code": 0,
    "stdout": {
      "status": "NO_SCOPE_FINDINGS",
      "report_files": 4,
      "summary": {
        "files_examined": 4,
        "directory_entries": 3,
        "elf_files": 3,
        "non_elf_ignored": 1,
        "visited_in_graph": 3,
        "dependency_edges": 3,
        "issue_count": 0,
        "issues_omitted": 0,
        "metadata_bytes_read": 933,
        "hash_bytes_read": 2225,
        "unique_metadata_candidate": 3,
        "ambiguous_candidates": 0,
        "architecture_mismatch": 0,
        "object_type_mismatch": 0,
        "unresolved_in_supplied_inputs": 0,
        "path_dependency_not_resolved": 0
      }
    },
    "stderr": null
  },
  {
    "case": "elf32-big-json-stdout",
    "exit_code": 0,
    "stdout": {
      "schema": "outlands-offline-elf-dependencies/1",
      "tool_version": "1.1.0",
      "status": "NO_SCOPE_FINDINGS",
      "interpretation": "Candidates in explicit local inputs only. No loader, linker namespaces, symbol/ABI compatibility, dlopen or runtime success is verified.",
      "limits": {
        "files": 2000,
        "entries": 20000,
        "depth": 32,
        "seconds": 60
      },
      "summary": {
        "files_examined": 1,
        "directory_entries": 0,
        "elf_files": 1,
        "non_elf_ignored": 0,
        "visited_in_graph": 1,
        "dependency_edges": 0,
        "issue_count": 0,
        "issues_omitted": 0,
        "metadata_bytes_read": 145,
        "hash_bytes_read": 640,
        "unique_metadata_candidate": 0,
        "ambiguous_candidates": 0,
        "architecture_mismatch": 0,
        "object_type_mismatch": 0,
        "unresolved_in_supplied_inputs": 0,
        "path_dependency_not_resolved": 0
      },
      "roots": [],
      "entry_files": [
        "selected-1/declared-32-big.elf"
      ],
      "files": [
        {
          "id": "selected-1/declared-32-big.elf",
          "name": "declared-32-big.elf",
          "class": 32,
          "endian": "big",
          "machine": 40,
          "machine_name": "ARM",
          "osabi": 0,
          "abi_version": 0,
          "flags": 0,
          "type": "DYN",
          "interpreter": "",
          "soname": "",
          "needed": [],
          "rpath": "",
          "runpath": "",
          "metadata": "dynamic_segment",
          "bytes": 640,
          "sha256": "f3d12e3de14b1875ce26522b05b534009324b9b378c52aaf2d1bd65a2747fd57"
        }
      ],
      "dependencies": [],
      "issues": []
    },
    "stderr": null
  },
  {
    "case": "malformed-review",
    "exit_code": 2,
    "stdout": {
      "status": "REVIEW_REQUIRED",
      "report_files": 4,
      "summary": {
        "files_examined": 1,
        "directory_entries": 0,
        "elf_files": 0,
        "non_elf_ignored": 0,
        "visited_in_graph": 0,
        "dependency_edges": 0,
        "issue_count": 2,
        "issues_omitted": 0,
        "metadata_bytes_read": 4,
        "hash_bytes_read": 0,
        "unique_metadata_candidate": 0,
        "ambiguous_candidates": 0,
        "architecture_mismatch": 0,
        "object_type_mismatch": 0,
        "unresolved_in_supplied_inputs": 0,
        "path_dependency_not_resolved": 0
      }
    },
    "stderr": null
  },
  {
    "case": "refuse-existing-output",
    "exit_code": 1,
    "stdout": null,
    "stderr": {
      "status": "ERROR",
      "code": "OUTPUT_MUST_BE_NEW_DIRECTORY"
    }
  },
  {
    "case": "refuse-scan-root-output",
    "exit_code": 1,
    "stdout": null,
    "stderr": {
      "status": "ERROR",
      "code": "OUTPUT_MUST_BE_OUTSIDE_SCAN_ROOTS"
    }
  },
  {
    "case": "refuse-duplicate-roots",
    "exit_code": 1,
    "stdout": null,
    "stderr": {
      "status": "ERROR",
      "code": "ROOTS_MUST_BE_DISJOINT"
    }
  },
  {
    "case": "refuse-no-selection",
    "exit_code": 1,
    "stdout": null,
    "stderr": {
      "status": "ERROR",
      "code": "SELECT_AT_LEAST_ONE_ROOT_OR_FILE"
    }
  }
]
```

The retained workspace has exactly 37 files: seventeen fictional inputs and five four-file reports. The default run contains no runtime-hint fields; the enabled run adds eight text observations across three ELF files without changing its declared graph. Embedded /vendor/etc/fictional-demo.xml and /vendor/firmware/fictional-demo.bin are tokens in the fixture, not accesses or discovered files on your computer.

This exercise does not inject a late output failure or cancellation. Such a failure can retain an incomplete new private folder; it is not a verified report or backup. Preserve it for review and use a different new destination for a retry. The inspector does not overwrite, clean up or roll back files. Native failure/partial-output controls are separate qualification cases.

Keep real reports private: relative names, dependency names, hashes, embedded search/interpreter paths and opt-in hint tokens can identify data. The manifest is not a signature. A unique metadata candidate does not establish loader behavior, full ABI compatibility, phone/hardware compatibility, runtime success or licensing rights. Sampled filesystem checks and cooperative budgets are not a sandbox, atomic snapshot or hard native I/O deadline. See [current qualification](docs/QUALIFICATION.md), the preserved [format contract](docs/FORMAT.md) and [private workspace guidance](docs/PRIVATE-WORKSPACE.md).
