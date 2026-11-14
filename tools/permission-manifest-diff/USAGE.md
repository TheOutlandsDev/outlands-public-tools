# Fictional permission-manifest comparison walkthrough

This guide compares authored saved metadata only. Declared paths are not opened,
permissions/ownership are not changed, SELinux policy is not evaluated and
capabilities are not applied. No effective access, device action, real manifest
or security verdict is involved. Selected differences do not authorize deployment.

Use Python 3.12–3.15 without third-party packages. Formal evidence uses a fresh
no-pip CPython 3.15.2 environment and external copies of the four actual
runtime/generator files. Assertions must remain enabled. CLI/generator uses
`-E -s -B` for sibling imports without environment/user-site settings or bytecode.
The independent driver uses `-I -B` and imports no inspector/comparison helper.

From the extracted module folder, save the single Python block below as
`fictional_permission_walkthrough.py` in an existing absolute private directory
outside source. Replace the fictional path with an owned directory; avoid
links/reparse routes, network paths and actual manifests. The driver creates one
new workspace and never deletes earlier evidence.

PowerShell 5.1 or newer:

```powershell
$module = (Get-Location).Path
$privateParent = 'D:\Private-Review'
python -I -B "$privateParent/fictional_permission_walkthrough.py" "$module" "$privateParent"
```

POSIX shell, using an existing owned private directory:

```sh
module="$PWD"
privateParent="$HOME/private-review"
python3 -I -B "$privateParent/fictional_permission_walkthrough.py" "$module" "$privateParent"
```

Generated same/changed/review pairs check numeric/option-order equivalence,
declared owner/mode/mask changes, known-invalid metadata and duplicate holds.
Other cases cover multi-file sets, all five supported field changes, uint32
UID/GID boundaries, full uint64 canonical hex, omitted-versus-zero capabilities
and literal SELinux category ordering. Modes remain octal metadata, not risk scores.

Known paths with unknown/repeated/invalid fields stay held without invented
removal. Unknown paths instead mark unidentified scope, holding unmatched
opposite identities while supported unique matched changes remain visible.
Duplicates on either side/across files never get arbitrary pairings, including
identical declarations. Paths are case-sensitive literal keys; no actual target,
user database, SELinux policy, filesystem or target-files archive is consulted.

Four default/details pairs preserve observations after stripping only opt-in
identities/fields and mode. Supported details are normalized; unsupported rows
have no invented fields. Raw unknown metadata, input filenames and original
lines stay omitted. Hashes/positions/IDs/structure can identify input: omission
is not anonymization. Empty scope and nonexistent declared targets prove little.

Whole-report expectations explicitly supply record positions, normalized fields,
changes, holds/counts and coverage; no parser/matcher is reused. The driver checks
exact stdout/empty stderr, independently recomputes input/report hashes and
checks unchanged fixtures/runtime, exact created files and no bytecode. Twelve
controlled refusals cover aliases, output reuse, arguments, UTF-8/controls and
line/file/record/count bounds. Review/refusal exits are checked internally;
the driver exits 0 only when every assertion passes. Unsigned hashes establish
byte consistency rather than origin, rights or effective access/security.

## Executable driver

```python
"""Compare authored permission metadata only; never open declared paths."""
import copy
import hashlib
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

if not __debug__:raise RuntimeError("ASSERTIONS_REQUIRED")
module=Path(sys.argv[1]).resolve(strict=True);parent=Path(sys.argv[2]).resolve(strict=True)
assert module.is_absolute() and parent.is_absolute() and parent.is_dir()
assert not parent.is_relative_to(module) and not module.is_relative_to(parent)
assert not module.is_symlink() and not parent.is_symlink() and not getattr(parent,"is_junction",lambda:False)()
work=Path(tempfile.mkdtemp(prefix="fictional-permission-text-",dir=parent)).resolve();assert work.parent==parent
runtime_names=("permission_diff.py","declaration_diff.py","inspection_support.py","examples/generate.py")
def digest(raw):return hashlib.sha256(raw).hexdigest()
runtime={name:digest((module/name).read_bytes()) for name in runtime_names};outcomes=[]
def command(case,script,args,expected_exit,expected_stdout):
    before={p.relative_to(work).as_posix():digest(p.read_bytes()) for p in work.rglob("*") if p.is_file()}
    result=subprocess.run([sys.executable,"-E","-s","-B",str(module/script),*map(str,args)],cwd=work,capture_output=True,timeout=60)
    assert result.returncode==expected_exit and result.stderr==b"",(case,result.stdout,result.stderr)
    assert json.loads(result.stdout)==expected_stdout,(case,result.stdout)
    assert result.stdout==(json.dumps(expected_stdout,sort_keys=True)+os.linesep).encode(),case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before=={name:digest((work/name).read_bytes()) for name in before},case
    outcomes.append(dict(case=case,exit_code=result.returncode))
command("create-fictional-permission-manifests","examples/generate.py",["--output",work/"fixtures"],0,dict(status="FICTIONAL_EXAMPLES_CREATED",files=4))
fixtures=work/"fixtures";assert {p.name for p in fixtures.iterdir()}=={"before.txt","same.txt","changed.txt","review.txt"}
crafted=work/"crafted";crafted.mkdir()

values={
    "dup-before.txt":b'system/a 0 0 644\nsystem/a 0 0 600\n',"dup-after.txt":b'system/a 0 0 600\n',
    "dup-after-equal.txt":b'system/a 0 0 644\nsystem/a 0 0 644\n',
    "one-before.txt":b'system/a 0 0 644\n',"one-after.txt":b'system/a 0 0 644\n',"empty.txt":b'',
    "unknown-path.txt":b'system/./a 0 0 644\n',"mixed-before.txt":b'system/a 0 0 644\nsystem/b 0 0 644\n',
    "mixed-after.txt":b'system/a 0 0 600\nsystem/./b 0 0 644\n',
    "full-before.txt":b'system/a 0 2000 755 selabel=u:object_r:demo:s0 capabilities=0x0\n',
    "full-after.txt":b'system/a 1000 1001 4755 selabel=u:object_r:other:s0 capabilities=0x1\n',
    "null-before.txt":b'system/a 0 0 644\n',"null-after.txt":b'system/a 0 0 644 capabilities=0x0\n',
    "max-before.txt":b'system/max 4294967295 4294967295 7777 capabilities=0xFFFFFFFFFFFFFFFF\n',
    "max-after.txt":b'system/max 4294967295 4294967295 7777 capabilities=0xffffffffffffffff\n',
    "label-before.txt":b'system/a 0 0 644 selabel=u:object_r:demo:s0:c1,c2\n',
    "label-after.txt":b'system/a 0 0 644 selabel=u:object_r:demo:s0:c2,c1\n',
    "invalid-known.txt":b'system/a 0 0 644 unknown=fictional_unknown_marker\n',
    "duplicate-optional.txt":b'system/a 0 0 644 capabilities=0x0 capabilities=0x1\n',
    "numeric-before.txt":''.join(f'system/n{i} 0 0 644\n' for i in range(1,6)).encode(),
    "numeric-after.txt":b'system/n1 4294967296 0 644\nsystem/n2 root 0 644\nsystem/n3 0 0 rwx\nsystem/n4 0 0 100644\nsystem/n5 0 -1 644\n',
    "case-before.txt":b'system/File 0 0 644\n',"case-after.txt":b'system/file 0 0 644\n',
    "unsupported.txt":b'../a 0 0 644\n/a 0 0 644\na//b 0 0 644\na/./b 0 0 644\na\\b 0 0 644\na:stream 0 0 644\n',
    "inline.txt":b'system/a 0 0 644 # comment\n',"bom.txt":b'\xef\xbb\xbfsystem/a 0 0 644\r\n',
    "comments.txt":b'# Fictional empty scope.\n',
    "nonexistent-before.txt":b'fictional/not-existing 0 0 7777\n',"nonexistent-after.txt":b'fictional/not-existing 0 0 7777\n',
    "invalid.txt":b'\xff',"control.txt":b'\x00',"line.txt":b'X'*8193,"bytes.txt":b'#'*(1024*1024+1),
    "record.txt":''.join(f'system/k{i} 0 0 644\n' for i in range(4001)).encode(),
    "multi-before-a.txt":b'system/a 0 0 644\n',"multi-before-b.txt":b'system/b 0 0 755\n',
    "multi-after-a.txt":b'system/b 0 0 0755\n',"multi-after-b.txt":b'system/a 0 0 0644\n',
}
for name,raw in values.items():(crafted/name).write_bytes(raw)
inputs={p.relative_to(work).as_posix():digest(p.read_bytes()) for folder in (fixtures,crafted) for p in folder.iterdir()}
assert len(inputs)==42
reports=[];input_hashes_checked=0;mode_counts={"default":0,"included":0}

def rid(index):return f"record-{index:04d}"
def issue(code,source,line):return dict(code=code,source=source,line=line)
def declaration(side,source,line,key,value):return (side,source,line,key,value)
def expected_report(before,after,*,records=(),changes=(),holds=(),unidentified=(),findings=(),coverage=(),compared=0,unchanged=0,details=False):
    # Record identities, pairing/holds, changes and finding order are supplied
    # explicitly. This helper does not parse source or compute key matches.
    src=[(f"before-{i:04d}",p) for i,p in enumerate(before,1)]+[(f"after-{i:04d}",p) for i,p in enumerate(after,1)]
    result=dict(schema_version=1,tool="Filesystem Permission Manifest Diff",
        scope="Selected literal path/UID/GID/mode/optional-label/capability declarations only; no filesystem or policy evaluation.",details_included=details,
        inputs=[dict(id=label,bytes=len(p.read_bytes()),sha256=digest(p.read_bytes())) for label,p in src],records=[],changes=[],held_identities=[],
        unidentified_rows=[dict(side=side,source=source,line=line) for side,source,line in unidentified],findings=list(findings),coverage_issues=list(coverage))
    for index,(side,source,line,key,value) in enumerate(records,1):
        row=dict(id=rid(index),side=side,source=source,line=line,supported=value is not None)
        if details:
            row["declared_identity"]=key
            if value is not None:row["fields"]=value
        result["records"].append(row)
    for kind,previous,now,fields in changes:
        result["changes"].append(dict(kind=kind,before_id=rid(previous) if previous else None,after_id=rid(now) if now else None,fields_changed=list(fields)))
    for reason,previous,now in holds:
        result["held_identities"].append(dict(reason=reason,before_ids=[rid(i) for i in previous],after_ids=[rid(i) for i in now]))
    result.update(comparison_counts=dict(unique_compared=compared,unchanged=unchanged,held=len(holds)),
        comparison_scope="Unique parsed selected declarations only; unmatched identities are held when the opposite side has unidentified rows. No effective runtime state is inferred.",
        status="REVIEW_REQUIRED" if findings or coverage else "NO_SCOPE_FINDINGS")
    return result
def inspect_case(case,before,after,*,details=False,**expectations):
    global input_hashes_checked
    before=tuple(before);after=tuple(after);expected=expected_report(before,after,details=details,**expectations);output=work/(case+"-report");args=[]
    for path in before:args += ["--before",path]
    for path in after:args += ["--after",path]
    args += ["--output",output]
    if details:args += ["--include-details"]
    status=expected["status"]
    command(case,"permission_diff.py",args,int(status!="NO_SCOPE_FINDINGS"),dict(status=status,changes=len(expected["changes"]),held_identities=len(expected["held_identities"]),coverage_issues=len(expected["coverage_issues"])))
    assert {p.name for p in output.iterdir()}=={"report.json","report.html","MANIFEST.json"}
    raw=(output/"report.json").read_bytes();page=(output/"report.html").read_bytes()
    assert json.loads(raw)==expected,case
    assert raw==(json.dumps(expected,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode(),case
    assert b'<script' not in page and b'http://' not in page and b'https://' not in page
    assert b'<pre>'+html.escape(raw.decode(),quote=True).encode()+b'</pre>' in page
    assert json.loads((output/"MANIFEST.json").read_bytes())==dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=digest(data)) for name,data in sorted({"report.json":raw,"report.html":page}.items())])
    if not details:assert b'"declared_identity"' not in raw and b'"fields"' not in raw and b'system/' not in raw and b'fictional/' not in raw
    assert str(work).encode() not in raw and str(module).encode() not in raw and b'fictional_unknown_marker' not in raw
    input_hashes_checked+=len(before)+len(after);mode_counts["included" if details else "default"]+=1;reports.append(output);return expected
def b(line,key,value,source="before-0001"):return declaration("before",source,line,key,value)
def a(line,key,value,source="after-0001"):return declaration("after",source,line,key,value)

def fields(uid=0,gid=0,mode="0644",label=None,cap=None):return dict(uid=uid,gid=gid,mode_octal=mode,selabel=label,capabilities=cap)
all_fields=("uid","gid","mode_octal","selabel","capabilities")
change_finding=(issue("SELECTED_DECLARATIONS_CHANGED","comparison",0),)
demo=fields(0,2000,"0755","u:object_r:demo_exec:s0","0x0");conf=fields()
same=dict(records=(b(2,"system/bin/demo",demo),b(3,"system/etc/demo.conf",conf),a(1,"system/etc/demo.conf",conf),a(2,"system/bin/demo",demo)),compared=2,unchanged=2)
same_default=inspect_case("numeric-spelling-option-order-same-default",[fixtures/"before.txt"],[fixtures/"same.txt"],**same)
same_details=inspect_case("numeric-spelling-option-order-same-details",[fixtures/"before.txt"],[fixtures/"same.txt"],details=True,**same)
changed=dict(records=(b(2,"system/bin/demo",demo),b(3,"system/etc/demo.conf",conf),a(1,"system/bin/demo",fields(1000,2000,"4755","u:object_r:demo_exec:s0","0x1")),a(2,"system/etc/demo.conf",conf)),
    changes=(("changed",1,3,("uid","mode_octal","capabilities")),),compared=2,unchanged=1,findings=change_finding)
changed_default=inspect_case("declared-owner-mode-mask-change-default",[fixtures/"before.txt"],[fixtures/"changed.txt"],**changed)
changed_details=inspect_case("declared-owner-mode-mask-change-details",[fixtures/"before.txt"],[fixtures/"changed.txt"],details=True,**changed)
review=dict(records=(b(2,"system/bin/demo",demo),b(3,"system/etc/demo.conf",conf),a(1,"system/bin/demo",None),a(2,"system/etc/demo.conf",conf),a(3,"system/etc/demo.conf",fields(mode="0600"))),
    holds=(("unsupported_declaration",(1,),(3,)),("duplicate_declarations",(2,),(4,5))),
    findings=(issue("AMBIGUOUS_DUPLICATE_DECLARATION","before-0001",3),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0001",2),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0001",3)),
    coverage=(issue("UNSUPPORTED_PERMISSION_DECLARATION","after-0001",1),))
review_default=inspect_case("invalid-known-path-and-duplicates-held-default",[fixtures/"before.txt"],[fixtures/"review.txt"],**review)
review_details=inspect_case("invalid-known-path-and-duplicates-held-details",[fixtures/"before.txt"],[fixtures/"review.txt"],details=True,**review)
inspect_case("multi-before-after-sets-compare-no-precedence",[crafted/"multi-before-a.txt",crafted/"multi-before-b.txt"],[crafted/"multi-after-a.txt",crafted/"multi-after-b.txt"],
    records=(b(1,"system/a",conf),b(1,"system/b",fields(mode="0755"),"before-0002"),a(1,"system/b",fields(mode="0755")),a(1,"system/a",conf,"after-0002")),compared=2,unchanged=2)
inspect_case("all-five-supported-fields-change",[crafted/"full-before.txt"],[crafted/"full-after.txt"],details=True,
    records=(b(1,"system/a",fields(0,2000,"0755","u:object_r:demo:s0","0x0")),a(1,"system/a",fields(1000,1001,"4755","u:object_r:other:s0","0x1"))),
    changes=(("changed",1,2,all_fields),),compared=1,findings=change_finding)
inspect_case("omitted-capability-is-not-explicit-zero",[crafted/"null-before.txt"],[crafted/"null-after.txt"],
    records=(b(1,"system/a",conf),a(1,"system/a",fields(cap="0x0"))),changes=(("changed",1,2,("capabilities",)),),compared=1,findings=change_finding)
maximum=fields(4294967295,4294967295,"7777",cap="0xffffffffffffffff")
inspect_case("uint32-and-uint64-hex-boundaries-normalize",[crafted/"max-before.txt"],[crafted/"max-after.txt"],details=True,
    records=(b(1,"system/max",maximum),a(1,"system/max",maximum)),compared=1,unchanged=1)
inspect_case("selinux-category-order-is-literal-text",[crafted/"label-before.txt"],[crafted/"label-after.txt"],
    records=(b(1,"system/a",fields(label="u:object_r:demo:s0:c1,c2")),a(1,"system/a",fields(label="u:object_r:demo:s0:c2,c1"))),
    changes=(("changed",1,2,("selabel",)),),compared=1,findings=change_finding)
invalid_known=dict(records=(b(1,"system/a",conf),a(1,"system/a",None)),holds=(("unsupported_declaration",(1,),(2,)),),coverage=(issue("UNSUPPORTED_PERMISSION_DECLARATION","after-0001",1),))
invalid_default=inspect_case("known-path-unknown-fields-held-default",[crafted/"one-before.txt"],[crafted/"invalid-known.txt"],**invalid_known)
invalid_details=inspect_case("known-path-unknown-fields-held-details",[crafted/"one-before.txt"],[crafted/"invalid-known.txt"],details=True,**invalid_known)
assert "fields" not in invalid_details["records"][1]
inspect_case("duplicate-optional-fields-hold-entire-path",[crafted/"one-before.txt"],[crafted/"duplicate-optional.txt"],**invalid_known)
inspect_case("invalid-numeric-and-mode-fields-keep-known-identities",[crafted/"numeric-before.txt"],[crafted/"numeric-after.txt"],
    records=tuple(b(i,f"system/n{i}",conf) for i in range(1,6))+tuple(a(i,f"system/n{i}",None) for i in range(1,6)),
    holds=tuple(("unsupported_declaration",(i,),(i+5,)) for i in range(1,6)),coverage=tuple(issue("UNSUPPORTED_PERMISSION_DECLARATION","after-0001",i) for i in range(1,6)))
inspect_case("before-duplicates-never-paired",[crafted/"dup-before.txt"],[crafted/"one-after.txt"],
    records=(b(1,"system/a",conf),b(2,"system/a",fields(mode="0600")),a(1,"system/a",conf)),holds=(("duplicate_declarations",(1,2),(3,)),),
    findings=(issue("AMBIGUOUS_DUPLICATE_DECLARATION","before-0001",1),issue("AMBIGUOUS_DUPLICATE_DECLARATION","before-0001",2),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0001",1)))
inspect_case("equal-after-duplicates-still-held",[crafted/"one-before.txt"],[crafted/"dup-after-equal.txt"],
    records=(b(1,"system/a",conf),a(1,"system/a",conf),a(2,"system/a",conf)),holds=(("duplicate_declarations",(1,),(2,3)),),
    findings=(issue("AMBIGUOUS_DUPLICATE_DECLARATION","before-0001",1),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0001",1),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0001",2)))
inspect_case("duplicate-across-selected-files-held",[crafted/"one-before.txt"],[crafted/"one-after.txt",crafted/"dup-after.txt"],
    records=(b(1,"system/a",conf),a(1,"system/a",conf),a(1,"system/a",fields(mode="0600"),"after-0002")),holds=(("duplicate_declarations",(1,),(2,3)),),
    findings=(issue("AMBIGUOUS_DUPLICATE_DECLARATION","before-0001",1),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0001",1),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0002",1)))
inspect_case("unknown-before-path-holds-apparent-addition",[crafted/"unknown-path.txt"],[crafted/"one-after.txt"],records=(a(1,"system/a",conf),),
    holds=(("uninspected_identity_on_opposite_side",(),(1,)),),unidentified=(("before","before-0001",1),),coverage=(issue("UNSUPPORTED_MANIFEST_PATH","before-0001",1),))
inspect_case("unknown-after-path-holds-apparent-removal",[crafted/"one-before.txt"],[crafted/"unknown-path.txt"],records=(b(1,"system/a",conf),),
    holds=(("uninspected_identity_on_opposite_side",(1,),()),),unidentified=(("after","after-0001",1),),coverage=(issue("UNSUPPORTED_MANIFEST_PATH","after-0001",1),))
inspect_case("unique-change-visible-beside-unknown-path-hold",[crafted/"mixed-before.txt"],[crafted/"mixed-after.txt"],
    records=(b(1,"system/a",conf),b(2,"system/b",conf),a(1,"system/a",fields(mode="0600"))),changes=(("changed",1,3,("mode_octal",)),),compared=1,
    holds=(("uninspected_identity_on_opposite_side",(2,),()),),unidentified=(("after","after-0001",2),),findings=change_finding,coverage=(issue("UNSUPPORTED_MANIFEST_PATH","after-0001",2),))
inspect_case("case-sensitive-path-rename-is-remove-add",[crafted/"case-before.txt"],[crafted/"case-after.txt"],
    records=(b(1,"system/File",conf),a(1,"system/file",conf)),changes=(("removed",1,None,all_fields),("added",None,2,all_fields)),compared=2,findings=change_finding)
inspect_case("unsupported-path-grammar-remains-unidentified",[crafted/"empty.txt"],[crafted/"unsupported.txt"],
    unidentified=tuple(("after","after-0001",i) for i in range(1,7)),coverage=tuple(issue("UNSUPPORTED_MANIFEST_PATH","after-0001",i) for i in range(1,7)))
inspect_case("inline-comment-is-not-silently-discarded",[crafted/"one-before.txt"],[crafted/"inline.txt"],**invalid_known)
inspect_case("utf8-bom-crlf-and-numeric-values",[crafted/"bom.txt"],[crafted/"one-after.txt"],records=(b(1,"system/a",conf),a(1,"system/a",conf)),compared=1,unchanged=1)
inspect_case("empty-comment-manifests-have-limited-scope",[crafted/"empty.txt"],[crafted/"comments.txt"])
inspect_case("nonexistent-declared-path-is-only-metadata",[crafted/"nonexistent-before.txt"],[crafted/"nonexistent-after.txt"],details=True,
    records=(b(1,"fictional/not-existing",fields(mode="7777")),a(1,"fictional/not-existing",fields(mode="7777"))),compared=1,unchanged=1)
def without_details(value):
    value=copy.deepcopy(value);value["details_included"]=False
    for row in value["records"]:row.pop("declared_identity",None);row.pop("fields",None)
    return value
for default,details in ((same_default,same_details),(changed_default,changed_details),(review_default,review_details),(invalid_default,invalid_details)):
    assert default==without_details(details)

def refuse(case,before,after,code,*,output=None):
    output=output or work/(case+"-report");existed=output.exists();args=[]
    for p in before:args += ["--before",p]
    for p in after:args += ["--after",p]
    args += ["--output",output]
    command(case,"permission_diff.py",args,2,dict(status="INCOMPLETE",error=code));assert output.exists()==existed,case
refuse("refuse-before-after-file-alias",[fixtures/"before.txt"],[fixtures/"before.txt"],"DUPLICATE_INPUT_FILE")
refuse("refuse-duplicate-after-file",[fixtures/"before.txt"],[fixtures/"same.txt",fixtures/"same.txt"],"DUPLICATE_INPUT_FILE")
refuse("refuse-existing-report",[fixtures/"before.txt"],[fixtures/"same.txt"],"OUTPUT_EXISTS",output=reports[0])
command("refuse-existing-generator-directory","examples/generate.py",["--output",fixtures],2,dict(status="INCOMPLETE",error="OUTPUT_EXISTS"))
refuse("refuse-relative-input",["fixtures/before.txt"],[fixtures/"same.txt"],"LOCAL_ABSOLUTE_PATH_REQUIRED")
refuse("refuse-required-before-missing",[],[fixtures/"same.txt"],"ARGUMENTS_INVALID")
refuse("refuse-invalid-utf8",[crafted/"empty.txt"],[crafted/"invalid.txt"],"UTF8_REQUIRED")
refuse("refuse-physical-control",[crafted/"empty.txt"],[crafted/"control.txt"],"TEXT_CONTROL_UNSUPPORTED")
refuse("refuse-physical-line-bound",[crafted/"empty.txt"],[crafted/"line.txt"],"TEXT_LINE_LIMIT")
refuse("refuse-input-byte-bound",[crafted/"empty.txt"],[crafted/"bytes.txt"],"INPUT_BYTE_LIMIT")
refuse("refuse-record-collection-bound",[crafted/"empty.txt"],[crafted/"record.txt"],"RECORD_LIMIT")
refuse("refuse-selected-file-count",[fixtures/"before.txt"],[fixtures/"same.txt"]*32,"INPUT_COUNT_LIMIT")
assert inputs=={name:digest((work/name).read_bytes()) for name in inputs}
assert runtime=={name:digest((module/name).read_bytes()) for name in runtime_names}
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
expected_files=set(inputs)
for output in reports:expected_files.update((output/name).relative_to(work).as_posix() for name in ("report.json","report.html","MANIFEST.json"))
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()}==expected_files
print(json.dumps(dict(outcomes=outcomes,reports_verified=len(reports),payload_hashes_verified=2*len(reports),input_hashes_checked=input_hashes_checked,
    fixture_files_preserved=len(inputs),expected_workspace_files=len(expected_files),unexpected_application_files=0,details_mode_counts=mode_counts,
    details_do_not_change_observations=True,bytecode_files=0,runtime_bytes_preserved=True,declared_paths_opened=False,filesystem_permissions_changed=False,
    filesystem_ownership_changed=False,selinux_policy_evaluated=False,capabilities_applied=False,effective_access_verified=False,
    devices_accessed=False,real_permission_manifests_used=False),sort_keys=True))
```

## Exact expected case outcomes

```json
[
  {
    "case": "create-fictional-permission-manifests",
    "exit_code": 0
  },
  {
    "case": "numeric-spelling-option-order-same-default",
    "exit_code": 0
  },
  {
    "case": "numeric-spelling-option-order-same-details",
    "exit_code": 0
  },
  {
    "case": "declared-owner-mode-mask-change-default",
    "exit_code": 1
  },
  {
    "case": "declared-owner-mode-mask-change-details",
    "exit_code": 1
  },
  {
    "case": "invalid-known-path-and-duplicates-held-default",
    "exit_code": 1
  },
  {
    "case": "invalid-known-path-and-duplicates-held-details",
    "exit_code": 1
  },
  {
    "case": "multi-before-after-sets-compare-no-precedence",
    "exit_code": 0
  },
  {
    "case": "all-five-supported-fields-change",
    "exit_code": 1
  },
  {
    "case": "omitted-capability-is-not-explicit-zero",
    "exit_code": 1
  },
  {
    "case": "uint32-and-uint64-hex-boundaries-normalize",
    "exit_code": 0
  },
  {
    "case": "selinux-category-order-is-literal-text",
    "exit_code": 1
  },
  {
    "case": "known-path-unknown-fields-held-default",
    "exit_code": 1
  },
  {
    "case": "known-path-unknown-fields-held-details",
    "exit_code": 1
  },
  {
    "case": "duplicate-optional-fields-hold-entire-path",
    "exit_code": 1
  },
  {
    "case": "invalid-numeric-and-mode-fields-keep-known-identities",
    "exit_code": 1
  },
  {
    "case": "before-duplicates-never-paired",
    "exit_code": 1
  },
  {
    "case": "equal-after-duplicates-still-held",
    "exit_code": 1
  },
  {
    "case": "duplicate-across-selected-files-held",
    "exit_code": 1
  },
  {
    "case": "unknown-before-path-holds-apparent-addition",
    "exit_code": 1
  },
  {
    "case": "unknown-after-path-holds-apparent-removal",
    "exit_code": 1
  },
  {
    "case": "unique-change-visible-beside-unknown-path-hold",
    "exit_code": 1
  },
  {
    "case": "case-sensitive-path-rename-is-remove-add",
    "exit_code": 1
  },
  {
    "case": "unsupported-path-grammar-remains-unidentified",
    "exit_code": 1
  },
  {
    "case": "inline-comment-is-not-silently-discarded",
    "exit_code": 1
  },
  {
    "case": "utf8-bom-crlf-and-numeric-values",
    "exit_code": 0
  },
  {
    "case": "empty-comment-manifests-have-limited-scope",
    "exit_code": 0
  },
  {
    "case": "nonexistent-declared-path-is-only-metadata",
    "exit_code": 0
  },
  {
    "case": "refuse-before-after-file-alias",
    "exit_code": 2
  },
  {
    "case": "refuse-duplicate-after-file",
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
    "case": "refuse-required-before-missing",
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
    "case": "refuse-record-collection-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-selected-file-count",
    "exit_code": 2
  }
]
```

The summary records forty cases: eight exit 0, twenty review exit 1 and twelve
incomplete exit 2 results. Twenty-seven manifests cover 54 report payloads;
57 selected input hash observations, 42 unchanged fictional inputs and 123
exact input/report files are checked. Twenty reports use defaults and seven
request details; four privacy pairs preserve supported observations.

All eight scope fields remain false: declared target opening, permission/ownership
changes, SELinux evaluation, capability application, effective-access verification,
device access and real manifests. Read [FORMAT.md](docs/FORMAT.md) and
[QUALIFICATION.md](docs/QUALIFICATION.md). Invalid known fields and unidentified
paths deliberately constrain comparisons; neither is a fabricated access result.
