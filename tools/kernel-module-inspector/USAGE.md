# Fictional module dependency and selection walkthrough

This guide reviews invented saved text only. It never opens, decompresses or
loads module binaries, invokes kmod, accesses devices or inspects a real system
inventory. Dependency ordering within selected metadata is not kernel ABI
verification, load authorization, actual binary availability or runtime proof.

Use Python 3.12–3.15 without third-party packages. Formal guide evidence uses a
fresh no-pip CPython 3.15.2 environment and external copies of the actual three
runtime/generator files. Assertions must remain enabled. Actual CLI commands
use `-E -s -B` to preserve sibling imports while disabling environment/user-site
settings and bytecode writes. The driver itself uses `-I -B`.

From the extracted module folder, save the single Python block below as
`fictional_module_walkthrough.py` in an existing absolute private directory
outside the source tree. Replace the fictional path with an owned directory;
avoid links/reparse routes, network paths or actual system inventories. The
driver creates one new workspace and never deletes earlier evidence.

PowerShell 5.1 or newer:

```powershell
$module = (Get-Location).Path
$privateParent = 'D:\Private-Review'
python -I -B "$privateParent/fictional_module_walkthrough.py" "$module" "$privateParent"
```

POSIX shell, using an existing owned private directory:

```sh
module="$PWD"
privateParent="$HOME/private-review"
python3 -I -B "$privateParent/fictional_module_walkthrough.py" "$module" "$privateParent"
```

Generated clean metadata selects one feature with a three-module prerequisite
closure. The prerequisites need not be separately selected. Generated review
metadata has a cycle, unknown dependency, repeated selection and unknown name.
Other fixtures distinguish exact-path priority from basename ambiguity;
duplicate declarations, selections and tokens; unresolved prerequisites and
blocked dependants; self-cycles and closed witnesses; and unrelated findings
that still require review despite a complete supported selected plan.

Compressed suffixes are literal text, not decompressed files. Dash/underscore
equivalence is never guessed. An optional declared inventory can omit a path
or repeat a row without proving real binary absence or presence. Empty/comment
inputs have limited empty scope. Unsupported grammar remains coverage, including
raw HTML-like text, and cannot become silently accepted configuration. A deep
1,500-node example checks iterative dependency-first ordering.

Three default/details pairs preserve observations after stripping only opt-in
fields/mode. Defaults omit names/paths; details add accepted literal declarations
and selected names. Unsupported raw rows remain omitted in both modes. HTML
escapes the serialized JSON. IDs, hashes and structure can identify input:
omission is not anonymization. Inputs must have distinct regular-file identities.

The driver supplies expected graph resolutions, ordering, findings and witnesses
explicitly; it does not import the inspector or reuse its graph algorithm. It
checks whole reports, exact stdout bytes and empty stderr; independently verifies
input hashes/lengths, report manifests and exact created files; and checks
unchanged fictional inputs/runtime bytes and no bytecode. Fourteen controlled
refusals cover node/edge budgets, aliases across input roles, output reuse,
arguments, regular files, paths, encoding/controls and line/file/list bounds.
Review/incomplete exits are checked internally; the driver exits 0 only after
all assertions pass. Unsigned hashes establish consistency rather than origin,
rights or runtime correctness. No load script or binary candidate is produced.

## Executable driver

```python
"""Review authored module metadata only; never open or load module binaries."""
import copy
import hashlib
import html
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
work = Path(tempfile.mkdtemp(prefix="fictional-module-text-", dir=parent)).resolve()
assert work.parent == parent
runtime_names = ("module_inspector.py", "inspection_support.py", "examples/generate.py")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
runtime = {name: digest((module/name).read_bytes()) for name in runtime_names}
outcomes = []

def command(case, script, args, expected_exit, expected_stdout):
    before = {p.relative_to(work).as_posix(): digest(p.read_bytes()) for p in work.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-E", "-s", "-B", str(module/script), *map(str, args)],
                            cwd=work, capture_output=True, timeout=60)
    assert result.returncode == expected_exit and result.stderr == b"", case
    assert json.loads(result.stdout) == expected_stdout, (case, result.stdout)
    assert result.stdout == (json.dumps(expected_stdout, sort_keys=True)+os.linesep).encode(), case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before == {name: digest((work/name).read_bytes()) for name in before}, case
    outcomes.append({"case": case, "exit_code": result.returncode})

command("create-fictional-module-text", "examples/generate.py", ["--output", work/"fixtures"], 0,
        {"status": "FICTIONAL_EXAMPLES_CREATED", "files": 5})
fixtures = work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"clean.dep", "clean.load", "available.txt", "review.dep", "review.load"}
crafted = work/"crafted"; crafted.mkdir()
values = {
    "order.dep": b'fictional/feature.ko: fictional/core.ko\nfictional/core.ko:\n',
    "feature.load": b'feature\n',
    "ambiguous.dep": b'one/demo.ko:\ntwo/demo.ko:\n',
    "basename.load": b'demo\n',
    "exact.load": b'one/demo.ko\n',
    "duplicate.dep": b'one/demo.ko:\none/demo.ko:\ntwo/demo.ko:\n',
    "duplicate.load": b'feature\nfictional/feature.ko\n',
    "missing.dep": b'fictional/a.ko: fictional/absent.ko\nfictional/b.ko: fictional/a.ko\n',
    "b.load": b'b\n',
    "cycle.dep": b'fictional/a.ko: fictional/b.ko\nfictional/b.ko: fictional/a.ko\nfictional/c.ko: fictional/a.ko\n',
    "c.load": b'c\n',
    "self.dep": b'fictional/a.ko: fictional/a.ko\n',
    "a.load": b'a\n',
    "unrelated.dep": b'fictional/a.ko: fictional/a.ko\nfictional/b.ko:\n',
    "compressed.dep": b'fictional/a-b.ko.xz:\nfictional/c.ko.zst: fictional/a-b.ko.xz\nfictional/d.ko.gz:\n',
    "underscore.load": b'a_b\n',
    "duplicate-token.dep": b'fictional/a.ko:\nfictional/b.ko: fictional/a.ko fictional/a.ko\n',
    "missing-inventory.txt": b'fictional/core.ko\nfictional/helper.ko\n',
    "duplicate-inventory.txt": b'fictional/core.ko\nfictional/helper.ko\nfictional/feature.ko\nfictional/feature.ko\n',
    "empty.dep": b'',
    "comments.load": b'# Fictional empty selection.\n',
    "unsupported.dep": b'fictional/a.ko:\nnot dependency syntax\nfictional/b.ko: /absolute.ko\nfictional/c.ko: fictional/a.ko # inline\n',
    "unsupported.load": b'a\n../a\na arg=1\n<script>fiction</script>\n',
    "bom.dep": b'\xef\xbb\xbffictional/a.ko:\r\n',
    "deep.dep": ''.join(f'fictional/m{i:04d}.ko: '+(f'fictional/m{i-1:04d}.ko' if i else '')+'\n' for i in range(1500)).encode(),
    "deep.load": b'm1499\n',
    "nodes.dep": ''.join(f'fictional/m{i}.ko:\n' for i in range(2001)).encode(),
    "edges.dep": ''.join(f'fictional/m{i}.ko: '+' '.join('a.ko' for _ in range(900))+'\n' for i in range(5)).encode(),
    "invalid.dep": b'\xff',
    "control.dep": b'# fictional\x00\n',
    "line.dep": b'X'*8193,
    "bytes.dep": b'#'*(1024*1024+1),
    "list.txt": b'a.ko\n'*4001,
}
for name, raw in values.items():
    (crafted/name).write_bytes(raw)
inputs = {p.relative_to(work).as_posix(): digest(p.read_bytes()) for folder in (fixtures, crafted) for p in folder.iterdir()}
assert len(inputs) == 38
reports = []; source_hashes_checked = 0; mode_counts = {"default": 0, "included": 0}

def mid(index):
    return f"module-{index:04d}"
def finding(code, source, line):
    return dict(code=code, source=source, line=line)
def expected_report(deps, loads, declarations=(), selections=(), edges=(), order=(), blocked=(),
                    witnesses=(), findings=(), coverage=(), inventory=None, complete=True, details=False):
    # All resolution, order, ambiguity, witness and finding expectations are supplied
    # explicitly below. This helper does not parse input or compute a graph.
    src = [("dependencies", deps), ("load-list", loads)]
    if inventory is not None:
        src.append(("declared-inventory", inventory))
    result = dict(schema_version=1, tool="Kernel Module List & Dependency Inspector",
        scope="Literal selected human-readable metadata only; no kmod/ABI/builtin/alias/runtime evaluation.",
        details_included=details,
        inputs=[dict(id=label, bytes=len(path.read_bytes()), sha256=digest(path.read_bytes())) for label,path in src],
        modules=[], dependencies=[], load_entries=[], cycle_witnesses=[[mid(i) for i in row] for row in witnesses],
        findings=list(findings), coverage_issues=list(coverage), declared_inventory_checked=inventory is not None)
    for index, (name, count, line) in enumerate(declarations, 1):
        row = dict(id=mid(index), source="dependencies", line=line, dependency_count=count)
        if details: row["declared_path"] = name
        result["modules"].append(row)
    for consumer, target, name, resolution in edges:
        row = dict(consumer=mid(consumer), resolution=resolution, dependency=mid(target) if target else None)
        if details: row["declared_path"] = name
        result["dependencies"].append(row)
    for name, line, ids, resolved in selections:
        row = dict(source="load-list", line=line, resolution="unique_selected_declaration" if resolved else "ambiguous_or_unresolved",
                   module_ids=[mid(i) for i in ids])
        if details: row["declared_name"] = name
        result["load_entries"].append(row)
    result.update(selected_dependency_order=[mid(i) for i in order], blocked_selected_modules=[mid(i) for i in blocked],
                  selected_plan_complete_within_metadata=complete,
                  plan_scope="Unique declared selected dependency closure only; dependencies need not appear separately in the load list. No runtime load authorization.",
                  status="REVIEW_REQUIRED" if findings or coverage else "NO_SCOPE_FINDINGS")
    return result

def inspect_case(case, deps, loads, *, inventory=None, details=False, **expectations):
    global source_hashes_checked
    output = work/(case+"-report")
    expected = expected_report(deps, loads, inventory=inventory, details=details, **expectations)
    args = ["--deps",deps,"--load-list",loads,"--output",output]
    if inventory is not None: args += ["--available",inventory]
    if details: args += ["--include-details"]
    status = expected["status"]
    command(case, "module_inspector.py", args, int(status != "NO_SCOPE_FINDINGS"),
            dict(status=status, modules=len(expected["modules"]), findings=len(expected["findings"]), coverage_issues=len(expected["coverage_issues"])))
    assert {p.name for p in output.iterdir()} == {"report.json", "report.html", "MANIFEST.json"}
    raw = (output/"report.json").read_bytes()
    assert json.loads(raw) == expected, case
    assert raw == (json.dumps(expected, indent=2, ensure_ascii=True, allow_nan=False)+"\n").encode(), case
    page = (output/"report.html").read_bytes()
    assert b"<script" not in page and b"http://" not in page and b"https://" not in page
    assert b"<pre>"+html.escape(raw.decode(),quote=True).encode()+b"</pre>" in page
    manifest = json.loads((output/"MANIFEST.json").read_bytes())
    assert manifest == dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=digest(data))
        for name,data in sorted({"report.json":raw,"report.html":page}.items())])
    if not details:
        assert not any(key in raw for key in (b'"declared_path"', b'"declared_name"', b'fictional/', b'one/demo', b'two/demo'))
    assert str(work).encode() not in raw and str(module).encode() not in raw
    source_hashes_checked += len(expected["inputs"])
    mode_counts["included" if details else "default"] += 1
    reports.append(output)
    return expected

U = "unique_selected_declaration"; M = "not_declared_in_selected_metadata"
clean = dict(declarations=(("fictional/core.ko",0,2),("fictional/helper.ko",1,3),("fictional/feature.ko",2,4)),
             selections=(("feature",1,(3,),True),),
             edges=((2,1,"fictional/core.ko",U),(3,2,"fictional/helper.ko",U),(3,1,"fictional/core.ko",U)), order=(1,2,3))
clean_default = inspect_case("clean-selected-closure-default", fixtures/"clean.dep", fixtures/"clean.load", inventory=fixtures/"available.txt", **clean)
clean_details = inspect_case("clean-selected-closure-details", fixtures/"clean.dep", fixtures/"clean.load", inventory=fixtures/"available.txt", details=True, **clean)
review = dict(declarations=(("fictional/a.ko",1,1),("fictional/b.ko",1,2),("fictional/other.ko",1,3)),
    selections=(("a",1,(1,),True),("a",2,(1,),True),("not_declared",3,(),False)),
    edges=((1,2,"fictional/b.ko",U),(2,1,"fictional/a.ko",U),(3,None,"fictional/unselected.ko",M)),
    blocked=(1,2), witnesses=((1,2,1),), complete=False,
    findings=(finding("DEPENDENCY_NEEDS_METADATA_REVIEW","dependencies",3),finding("DUPLICATE_LOAD_SELECTION","load-list",2),
              finding("LOAD_SELECTION_NEEDS_METADATA_REVIEW","load-list",3),finding("DECLARED_DEPENDENCY_CYCLE","dependencies",2)))
review_default = inspect_case("generated-cycle-and-unknown-default", fixtures/"review.dep", fixtures/"review.load", **review)
review_details = inspect_case("generated-cycle-and-unknown-details", fixtures/"review.dep", fixtures/"review.load", details=True, **review)
inspect_case("dependency-order-over-input-order", crafted/"order.dep", crafted/"feature.load",
    declarations=(("fictional/feature.ko",1,1),("fictional/core.ko",0,2)),selections=(("feature",1,(1,),True),),
    edges=((1,2,"fictional/core.ko",U),),order=(2,1))
ambiguous = (("one/demo.ko",0,1),("two/demo.ko",0,2))
inspect_case("ambiguous-basename-held",crafted/"ambiguous.dep",crafted/"basename.load",declarations=ambiguous,
    selections=(("demo",1,(1,2),False),),complete=False,findings=(finding("LOAD_SELECTION_NEEDS_METADATA_REVIEW","load-list",1),))
inspect_case("exact-path-wins-over-basename-ambiguity",crafted/"ambiguous.dep",crafted/"exact.load",declarations=ambiguous,
    selections=(("one/demo.ko",1,(1,),True),),order=(1,))
inspect_case("duplicate-declaration-alias-held",crafted/"duplicate.dep",crafted/"basename.load",
    declarations=(("one/demo.ko",0,1),("one/demo.ko",0,2),("two/demo.ko",0,3)),
    selections=(("demo",1,(3,),False),),complete=False,
    findings=(finding("AMBIGUOUS_MODULE_DECLARATION","dependencies",1),finding("AMBIGUOUS_MODULE_DECLARATION","dependencies",2),
              finding("LOAD_SELECTION_NEEDS_METADATA_REVIEW","load-list",1)))
duplicate_selection = dict(clean); duplicate_selection["selections"] = (("feature",1,(3,),True),("fictional/feature.ko",2,(3,),True))
duplicate_selection["findings"] = (finding("DUPLICATE_LOAD_SELECTION","load-list",2),)
inspect_case("duplicate-selection-one-closure",fixtures/"clean.dep",crafted/"duplicate.load",**duplicate_selection)
inspect_case("unresolved-prerequisite-blocks-dependants",crafted/"missing.dep",crafted/"b.load",
    declarations=(("fictional/a.ko",1,1),("fictional/b.ko",1,2)),selections=(("b",1,(2,),True),),
    edges=((1,None,"fictional/absent.ko",M),(2,1,"fictional/a.ko",U)),blocked=(1,2),complete=False,
    findings=(finding("DEPENDENCY_NEEDS_METADATA_REVIEW","dependencies",1),))
cycle = inspect_case("cycle-witness-excludes-blocked-dependant",crafted/"cycle.dep",crafted/"c.load",
    declarations=(("fictional/a.ko",1,1),("fictional/b.ko",1,2),("fictional/c.ko",1,3)),selections=(("c",1,(3,),True),),
    edges=((1,2,"fictional/b.ko",U),(2,1,"fictional/a.ko",U),(3,1,"fictional/a.ko",U)),blocked=(1,2,3),witnesses=((1,2,1),),complete=False,
    findings=(finding("DECLARED_DEPENDENCY_CYCLE","dependencies",2),))
assert mid(3) not in cycle["cycle_witnesses"][0] and len(cycle["blocked_selected_modules"]) == 3
inspect_case("self-cycle-closed-witness",crafted/"self.dep",crafted/"a.load",declarations=(("fictional/a.ko",1,1),),
    selections=(("a",1,(1,),True),),edges=((1,1,"fictional/a.ko",U),),blocked=(1,),witnesses=((1,1),),complete=False,
    findings=(finding("DECLARED_DEPENDENCY_CYCLE","dependencies",1),))
unrelated = inspect_case("unrelated-cycle-still-review-selected-plan-complete",crafted/"unrelated.dep",crafted/"b.load",
    declarations=(("fictional/a.ko",1,1),("fictional/b.ko",0,2)),selections=(("b",1,(2,),True),),
    edges=((1,1,"fictional/a.ko",U),),order=(2,),witnesses=((1,1),),findings=(finding("DECLARED_DEPENDENCY_CYCLE","dependencies",1),))
assert unrelated["selected_plan_complete_within_metadata"] and unrelated["status"] == "REVIEW_REQUIRED"
compressed = dict(declarations=(("fictional/a-b.ko.xz",0,1),("fictional/c.ko.zst",1,2),("fictional/d.ko.gz",0,3)),
    selections=(("c",1,(2,),True),),edges=((2,1,"fictional/a-b.ko.xz",U),),order=(1,2))
inspect_case("compressed-suffixes-are-literal-text",crafted/"compressed.dep",crafted/"c.load",**compressed)
underscore = dict(compressed); underscore.update(selections=(("a_b",1,(),False),),order=(),complete=False,
    findings=(finding("LOAD_SELECTION_NEEDS_METADATA_REVIEW","load-list",1),))
inspect_case("no-hyphen-underscore-guessing",crafted/"compressed.dep",crafted/"underscore.load",**underscore)
inspect_case("duplicate-token-normalized-before-order",crafted/"duplicate-token.dep",crafted/"b.load",
    declarations=(("fictional/a.ko",0,1),("fictional/b.ko",2,2)),selections=(("b",1,(2,),True),),
    edges=((2,1,"fictional/a.ko",U),),order=(1,2),findings=(finding("DUPLICATE_DEPENDENCY_TOKEN","dependencies",2),))
missing_inventory = dict(clean); missing_inventory["findings"] = (finding("NOT_IN_SUPPLIED_INVENTORY","dependencies",4),)
inventory_report = inspect_case("inventory-omission-not-binary-absence",fixtures/"clean.dep",fixtures/"clean.load",
    inventory=crafted/"missing-inventory.txt",**missing_inventory)
assert inventory_report["selected_plan_complete_within_metadata"]
dupe_inventory = dict(clean); dupe_inventory["findings"] = (finding("DUPLICATE_INVENTORY_ENTRY","declared-inventory",4),)
inspect_case("duplicate-inventory-entry-review",fixtures/"clean.dep",fixtures/"clean.load",inventory=crafted/"duplicate-inventory.txt",**dupe_inventory)
inspect_case("empty-scope-is-not-inventory-proof",crafted/"empty.dep",crafted/"comments.load")
unsupported = dict(declarations=(("fictional/a.ko",0,1),),selections=(("a",1,(1,),True),),order=(1,),complete=False,
    coverage=(finding("UNSUPPORTED_DEPENDENCY_LINE","dependencies",2),finding("UNSUPPORTED_MODULE_PATH","dependencies",3),
              finding("UNSUPPORTED_MODULE_PATH","dependencies",4),finding("UNSUPPORTED_LIST_ENTRY","load-list",2),
              finding("UNSUPPORTED_LIST_ENTRY","load-list",3),finding("UNSUPPORTED_LIST_ENTRY","load-list",4)))
unsupported_default = inspect_case("unsupported-grammar-default",crafted/"unsupported.dep",crafted/"unsupported.load",**unsupported)
unsupported_details = inspect_case("unsupported-grammar-details-raw-rows-omitted",crafted/"unsupported.dep",crafted/"unsupported.load",details=True,**unsupported)
assert b"<script>" not in (reports[-1]/"report.html").read_bytes()
inspect_case("utf8-bom-and-crlf-supported",crafted/"bom.dep",crafted/"a.load",declarations=(("fictional/a.ko",0,1),),
    selections=(("a",1,(1,),True),),order=(1,))
inspect_case("deep-iterative-selected-order",crafted/"deep.dep",crafted/"deep.load",
    declarations=tuple((f"fictional/m{i:04d}.ko",int(i>0),i+1) for i in range(1500)),
    selections=(("m1499",1,(1500,),True),),edges=tuple((i+1,i,f"fictional/m{i-1:04d}.ko",U) for i in range(1,1500)),
    order=tuple(range(1,1501)))

def without_details(value):
    value = copy.deepcopy(value); value["details_included"] = False
    for collection in ("modules", "dependencies", "load_entries"):
        for row in value[collection]:
            row.pop("declared_path", None); row.pop("declared_name", None)
    return value
for default, details in ((clean_default,clean_details),(review_default,review_details),(unsupported_default,unsupported_details)):
    assert default == without_details(details)

def refuse(case, deps, loads, code, *, inventory=None, output=None, extra=()):
    output = output or work/(case+"-report")
    existed = output.exists()
    args = ["--deps",deps,"--load-list",loads,"--output",output]
    if inventory is not None: args += ["--available",inventory]
    args += list(extra)
    command(case,"module_inspector.py",args,2,dict(status="INCOMPLETE",error=code))
    assert output.exists() == existed, case

refuse("refuse-node-budget",crafted/"nodes.dep",crafted/"a.load","MODULE_NODE_LIMIT")
refuse("refuse-edge-budget",crafted/"edges.dep",crafted/"a.load","MODULE_EDGE_LIMIT")
refuse("refuse-relative-dependency-input","fixtures/clean.dep",fixtures/"clean.load","LOCAL_ABSOLUTE_PATH_REQUIRED")
refuse("refuse-dependency-load-same-file",fixtures/"clean.dep",fixtures/"clean.dep","DUPLICATE_INPUT_FILE")
refuse("refuse-inventory-same-file",fixtures/"clean.dep",fixtures/"clean.load","DUPLICATE_INPUT_FILE",inventory=fixtures/"clean.dep")
refuse("refuse-existing-report",fixtures/"clean.dep",fixtures/"clean.load","OUTPUT_EXISTS",output=reports[0])
command("refuse-existing-generator-directory","examples/generate.py",["--output",fixtures],2,dict(status="INCOMPLETE",error="OUTPUT_EXISTS"))
refuse("refuse-unknown-option",fixtures/"clean.dep",fixtures/"clean.load","ARGUMENTS_INVALID",extra=("--not-a-mode",))
refuse("refuse-directory-input",fixtures,fixtures/"clean.load","REGULAR_FILE_REQUIRED")
refuse("refuse-invalid-utf8",crafted/"invalid.dep",crafted/"a.load","UTF8_REQUIRED")
refuse("refuse-physical-control",crafted/"control.dep",crafted/"a.load","TEXT_CONTROL_UNSUPPORTED")
refuse("refuse-physical-line-bound",crafted/"line.dep",crafted/"a.load","TEXT_LINE_LIMIT")
refuse("refuse-input-byte-bound",crafted/"bytes.dep",crafted/"a.load","INPUT_BYTE_LIMIT")
refuse("refuse-inventory-record-bound",crafted/"bom.dep",crafted/"a.load","RECORD_LIMIT",inventory=crafted/"list.txt")
assert inputs == {name: digest((work/name).read_bytes()) for name in inputs}
assert runtime == {name: digest((module/name).read_bytes()) for name in runtime_names}
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
expected_files = set(inputs)
for output in reports:
    expected_files.update((output/name).relative_to(work).as_posix() for name in ("report.json","report.html","MANIFEST.json"))
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()} == expected_files
print(json.dumps(dict(outcomes=outcomes,reports_verified=len(reports),payload_hashes_verified=2*len(reports),
    input_hashes_checked=source_hashes_checked,fixture_files_preserved=len(inputs),expected_workspace_files=len(expected_files),
    unexpected_application_files=0,details_mode_counts=mode_counts,details_do_not_change_observations=True,
    bytecode_files=0,runtime_bytes_preserved=True,module_binaries_opened=False,modules_loaded=False,
    modules_decompressed=False,kmod_invoked=False,devices_accessed=False,real_system_inventory_used=False,
    kernel_abi_compatibility_verified=False,runtime_load_verified=False),sort_keys=True))
```

## Exact expected case outcomes

```json
[
  {
    "case": "create-fictional-module-text",
    "exit_code": 0
  },
  {
    "case": "clean-selected-closure-default",
    "exit_code": 0
  },
  {
    "case": "clean-selected-closure-details",
    "exit_code": 0
  },
  {
    "case": "generated-cycle-and-unknown-default",
    "exit_code": 1
  },
  {
    "case": "generated-cycle-and-unknown-details",
    "exit_code": 1
  },
  {
    "case": "dependency-order-over-input-order",
    "exit_code": 0
  },
  {
    "case": "ambiguous-basename-held",
    "exit_code": 1
  },
  {
    "case": "exact-path-wins-over-basename-ambiguity",
    "exit_code": 0
  },
  {
    "case": "duplicate-declaration-alias-held",
    "exit_code": 1
  },
  {
    "case": "duplicate-selection-one-closure",
    "exit_code": 1
  },
  {
    "case": "unresolved-prerequisite-blocks-dependants",
    "exit_code": 1
  },
  {
    "case": "cycle-witness-excludes-blocked-dependant",
    "exit_code": 1
  },
  {
    "case": "self-cycle-closed-witness",
    "exit_code": 1
  },
  {
    "case": "unrelated-cycle-still-review-selected-plan-complete",
    "exit_code": 1
  },
  {
    "case": "compressed-suffixes-are-literal-text",
    "exit_code": 0
  },
  {
    "case": "no-hyphen-underscore-guessing",
    "exit_code": 1
  },
  {
    "case": "duplicate-token-normalized-before-order",
    "exit_code": 1
  },
  {
    "case": "inventory-omission-not-binary-absence",
    "exit_code": 1
  },
  {
    "case": "duplicate-inventory-entry-review",
    "exit_code": 1
  },
  {
    "case": "empty-scope-is-not-inventory-proof",
    "exit_code": 0
  },
  {
    "case": "unsupported-grammar-default",
    "exit_code": 1
  },
  {
    "case": "unsupported-grammar-details-raw-rows-omitted",
    "exit_code": 1
  },
  {
    "case": "utf8-bom-and-crlf-supported",
    "exit_code": 0
  },
  {
    "case": "deep-iterative-selected-order",
    "exit_code": 0
  },
  {
    "case": "refuse-node-budget",
    "exit_code": 2
  },
  {
    "case": "refuse-edge-budget",
    "exit_code": 2
  },
  {
    "case": "refuse-relative-dependency-input",
    "exit_code": 2
  },
  {
    "case": "refuse-dependency-load-same-file",
    "exit_code": 2
  },
  {
    "case": "refuse-inventory-same-file",
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
    "case": "refuse-unknown-option",
    "exit_code": 2
  },
  {
    "case": "refuse-directory-input",
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
    "case": "refuse-input-byte-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-inventory-record-bound",
    "exit_code": 2
  }
]
```

The summary records 38 cases: nine exit 0, fifteen review exit 1 and fourteen
incomplete exit 2 results. Twenty-three report manifests cover 46 payloads;
50 input hash observations, 38 preserved fictional inputs and 107 exact
input/report files are checked. Twenty reports use defaults and three request
details; three pairs preserve observations.

All eight scope fields stay false: module binary access/loading/decompression,
kmod invocation, device access, real system inventory, kernel ABI verification
and runtime load verification. A complete selected metadata plan can coexist
with unrelated findings, inventory omissions or duplicate selections. Read
[FORMAT.md](docs/FORMAT.md) and [QUALIFICATION.md](docs/QUALIFICATION.md) before
interpreting evidence. This source-only walkthrough is not native kmod parity,
full system inventory, kernel compatibility or deployment acceptance.
