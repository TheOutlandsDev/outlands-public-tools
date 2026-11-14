# Fictional literal-property snapshot comparison walkthrough

This guide compares invented saved text only. It never follows imports, changes
properties, merges effective state, evaluates precedence/permissions/runtime
compatibility, accesses devices or uses actual property snapshots. Selected
literal changes are not a complete or effective Android configuration.

Use Python 3.12–3.15 without third-party packages. Formal guide evidence uses a
fresh no-pip CPython 3.15.2 environment and external copies of the four actual
runtime/generator files. Assertions must remain enabled. CLI/generator uses
`-E -s -B` for sibling imports without environment/user-site settings or bytecode.
The independent driver uses `-I -B` and imports no inspector/comparison helper.

From the extracted module folder, save the single Python block below as
`fictional_property_walkthrough.py` in an existing absolute private directory
outside source. Replace the fictional path with an owned directory; avoid
links/reparse routes, network paths and actual configs. The driver creates one
new workspace and never deletes earlier evidence.

PowerShell 5.1 or newer:

```powershell
$module = (Get-Location).Path
$privateParent = 'D:\Private-Review'
python -I -B "$privateParent/fictional_property_walkthrough.py" "$module" "$privateParent"
```

POSIX shell, using an existing owned private directory:

```sh
module="$PWD"
privateParent="$HOME/private-review"
python3 -I -B "$privateParent/fictional_property_walkthrough.py" "$module" "$privateParent"
```

Generated same/changed/review examples cover unchanged comments/order/ASCII
whitespace, changed/added values and duplicate/import holds. Multi-file before
and after sets do not establish precedence. Duplicates stay ambiguous on either
side, across files or with equal values; no arbitrary winner/pair is chosen.
Unknown/import rows on the opposite side hold apparent additions/removals;
unique supported matched changes remain visible alongside coverage.

Literal fixtures check first equals, inline hash, quotes, trailing backslash,
dollar expression and empty values. Only ASCII spaces/tabs are trimmed; keys
are case-sensitive and nonbreaking spaces remain value data. Empty values are
declarations rather than absence. Reserved-looking prefixes have no inferred
runtime/service/permission semantics. Import targets are not opened or followed.

Four default/details pairs preserve observations after removing only accepted
opt-in keys/value fields and mode. Literal HTML detail values must be escaped.
Raw lines/import targets/local filenames stay omitted. Hashes, IDs and structure
can identify input: omission is not anonymization. Empty scope proves little.

Whole-report expectations explicitly supply record positions, changes, holds,
counts and coverage. No parsing/matching implementation is reused. The driver
checks exact stdout/empty stderr, independent selected input/report hashes,
unchanged fixtures/runtime, exact created files and no bytecode. Twelve
controlled refusals cover aliases, output reuse, arguments, UTF-8/controls and
line/file/record/count bounds. Review/refusal exits are checked internally; the
driver exits 0 only when all assertions pass. Unsigned hashes establish byte
consistency rather than origin, rights or device/runtime correctness.

## Executable driver

```python
"""Compare authored literal property snapshots only; never apply properties."""
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
work=Path(tempfile.mkdtemp(prefix="fictional-property-text-",dir=parent)).resolve();assert work.parent==parent
runtime_names=("property_diff.py","declaration_diff.py","inspection_support.py","examples/generate.py")
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
command("create-fictional-property-snapshots","examples/generate.py",["--output",work/"fixtures"],0,dict(status="FICTIONAL_EXAMPLES_CREATED",files=4))
fixtures=work/"fixtures";assert {p.name for p in fixtures.iterdir()}=={"before.prop","same.prop","changed.prop","review.prop"}
crafted=work/"crafted";crafted.mkdir()
literal=(('demo.equals','one=two#literal'),('demo.quote','"fictional value"'),('demo.single',"'quoted'"),
         ('demo.slash','trailing\\'),('demo.dollar','${fictional}'),('demo.empty',''))
values={
    "dup-before.prop":b'demo.a=one\ndemo.a=two\n',"dup-after.prop":b'demo.a=two\n',
    "dup-after-equal.prop":b'demo.a=one\ndemo.a=one\n',"one-before.prop":b'demo.a=one\n',"one-after.prop":b'demo.a=one\n',
    "empty.prop":b'',"unknown.prop":b'unsupported row\n',"import.prop":b'import /fictional/not-opened.prop\n',
    "mixed-before.prop":b'demo.a=one\ndemo.b=one\n',"mixed-after.prop":b'demo.a=two\nunsupported row\n',
    "literal-before.prop":''.join(' \t'+key+' = '+value+' \t\n' for key,value in literal).encode(),
    "literal-after.prop":''.join(key+'='+value+'\n' for key,value in reversed(literal)).encode(),
    "case-before.prop":b'demo.A=one\n',"case-after.prop":b'demo.a=one\n',
    "nbsp-before.prop":b'demo.a=one\n',"nbsp-after.prop":'demo.a=one\u00a0\n'.encode(),
    "unsupported.prop":b'unsupported row\ndemo a=one\nimport /fictional/not-opened.prop\n',
    "bom.prop":b'\xef\xbb\xbfdemo.a=one\r\n',"comments.prop":b'# Fictional empty scope.\n',
    "reserved-before.prop":b'ro.demo.value=one\nctl.demo=one\npersist.demo.rate=one\n',
    "reserved-after.prop":b'ro.demo.value=one\nctl.demo=one\npersist.demo.rate=one\n',
    "html-before.prop":b'demo.a=old\n',"html-after.prop":b'demo.a=</pre><script>fictional</script>\n',
    "invalid.prop":b'\xff',"control.prop":b'demo.a=\x00',"line.prop":b'demo.a='+b'X'*8193,
    "bytes.prop":b'#'*(1024*1024+1),"record.prop":''.join(f'demo.k{i}=x\n' for i in range(4001)).encode(),
    "multi-before-a.prop":b'demo.a=one\n',"multi-before-b.prop":b'demo.b=two\n',
    "multi-after-a.prop":b'demo.b=two\n',"multi-after-b.prop":b'demo.a=one\n',
}
for name,raw in values.items():(crafted/name).write_bytes(raw)
inputs={p.relative_to(work).as_posix():digest(p.read_bytes()) for folder in (fixtures,crafted) for p in folder.iterdir()}
assert len(inputs)==36
reports=[];input_hashes_checked=0;mode_counts={"default":0,"included":0}
def rid(index):return f"record-{index:04d}"
def issue(code,source,line):return dict(code=code,source=source,line=line)
def declaration(side,source,line,key,value):return (side,source,line,key,value)
def expected_report(before,after,*,records=(),changes=(),holds=(),unidentified=(),findings=(),coverage=(),compared=0,unchanged=0,details=False):
    # Record identities, pairing/holds, changes and finding order are supplied
    # explicitly. This helper does not parse source or compute key matches.
    src=[(f"before-{i:04d}",p) for i,p in enumerate(before,1)]+[(f"after-{i:04d}",p) for i,p in enumerate(after,1)]
    result=dict(schema_version=1,tool="Android Property Configuration Diff",
        scope="Literal unique selected key/value declarations only; no import/override/order/permission/runtime evaluation.",details_included=details,
        inputs=[dict(id=label,bytes=len(p.read_bytes()),sha256=digest(p.read_bytes())) for label,p in src],records=[],changes=[],held_identities=[],
        unidentified_rows=[dict(side=side,source=source,line=line) for side,source,line in unidentified],findings=list(findings),coverage_issues=list(coverage))
    for index,(side,source,line,key,value) in enumerate(records,1):
        row=dict(id=rid(index),side=side,source=source,line=line,supported=True)
        if details:row.update(declared_identity=key,fields=dict(value=value))
        result["records"].append(row)
    for kind,previous,now in changes:
        result["changes"].append(dict(kind=kind,before_id=rid(previous) if previous else None,after_id=rid(now) if now else None,fields_changed=["value"]))
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
    command(case,"property_diff.py",args,int(status!="NO_SCOPE_FINDINGS"),dict(status=status,changes=len(expected["changes"]),held_identities=len(expected["held_identities"]),coverage_issues=len(expected["coverage_issues"])))
    assert {p.name for p in output.iterdir()}=={"report.json","report.html","MANIFEST.json"}
    raw=(output/"report.json").read_bytes();page=(output/"report.html").read_bytes()
    assert json.loads(raw)==expected,case
    assert raw==(json.dumps(expected,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode(),case
    assert b'<script' not in page and b'http://' not in page and b'https://' not in page
    assert b'<pre>'+html.escape(raw.decode(),quote=True).encode()+b'</pre>' in page
    assert json.loads((output/"MANIFEST.json").read_bytes())==dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=digest(data)) for name,data in sorted({"report.json":raw,"report.html":page}.items())])
    if not details:assert b'"declared_identity"' not in raw and b'"fields"' not in raw and b'demo.' not in raw
    assert str(work).encode() not in raw and str(module).encode() not in raw and b'/fictional/not-opened.prop' not in raw
    input_hashes_checked+=len(before)+len(after);mode_counts["included" if details else "default"]+=1;reports.append(output);return expected
def b(line,key,value,source="before-0001"):return declaration("before",source,line,key,value)
def a(line,key,value,source="after-0001"):return declaration("after",source,line,key,value)
change_finding=(issue("SELECTED_DECLARATIONS_CHANGED","comparison",0),)
same=dict(records=(b(2,"ro.demo.name","Example"),b(3,"persist.demo.rate","10"),a(2,"persist.demo.rate","10"),a(3,"ro.demo.name","Example")),compared=2,unchanged=2)
same_default=inspect_case("comments-whitespace-order-same-default",[fixtures/"before.prop"],[fixtures/"same.prop"],**same)
same_details=inspect_case("comments-whitespace-order-same-details",[fixtures/"before.prop"],[fixtures/"same.prop"],details=True,**same)
changed=dict(records=(b(2,"ro.demo.name","Example"),b(3,"persist.demo.rate","10"),a(1,"ro.demo.name","Example"),a(2,"persist.demo.rate","20"),a(3,"ro.demo.extra","enabled")),
    compared=3,unchanged=1,changes=(("changed",2,4),("added",None,5)),findings=change_finding)
changed_default=inspect_case("changed-and-added-values-default",[fixtures/"before.prop"],[fixtures/"changed.prop"],**changed)
changed_details=inspect_case("changed-and-added-values-details",[fixtures/"before.prop"],[fixtures/"changed.prop"],details=True,**changed)
review=dict(records=(b(2,"ro.demo.name","Example"),b(3,"persist.demo.rate","10"),a(1,"ro.demo.name","Example"),a(2,"persist.demo.rate","10"),a(3,"persist.demo.rate","20")),
    compared=1,unchanged=1,holds=(("duplicate_declarations",(2,),(4,5)),),unidentified=(("after","after-0001",4),),
    findings=(issue("AMBIGUOUS_DUPLICATE_DECLARATION","before-0001",3),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0001",2),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0001",3)),
    coverage=(issue("PROPERTY_IMPORT_NOT_FOLLOWED","after-0001",4),))
review_default=inspect_case("duplicate-import-held-default",[fixtures/"before.prop"],[fixtures/"review.prop"],**review)
review_details=inspect_case("duplicate-import-held-details",[fixtures/"before.prop"],[fixtures/"review.prop"],details=True,**review)
inspect_case("multi-before-after-fragments-no-order-precedence",[crafted/"multi-before-a.prop",crafted/"multi-before-b.prop"],[crafted/"multi-after-a.prop",crafted/"multi-after-b.prop"],
    records=(b(1,"demo.a","one"),b(1,"demo.b","two","before-0002"),a(1,"demo.b","two"),a(1,"demo.a","one","after-0002")),compared=2,unchanged=2)
inspect_case("before-duplicates-do-not-invent-removal",[crafted/"dup-before.prop"],[crafted/"empty.prop"],
    records=(b(1,"demo.a","one"),b(2,"demo.a","two")),holds=(("duplicate_declarations",(1,2),()),),
    findings=(issue("AMBIGUOUS_DUPLICATE_DECLARATION","before-0001",1),issue("AMBIGUOUS_DUPLICATE_DECLARATION","before-0001",2)))
inspect_case("equal-after-duplicates-still-ambiguous",[crafted/"one-before.prop"],[crafted/"dup-after-equal.prop"],
    records=(b(1,"demo.a","one"),a(1,"demo.a","one"),a(2,"demo.a","one")),holds=(("duplicate_declarations",(1,),(2,3)),),
    findings=(issue("AMBIGUOUS_DUPLICATE_DECLARATION","before-0001",1),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0001",1),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0001",2)))
inspect_case("duplicate-across-after-files-held",[crafted/"one-before.prop"],[crafted/"one-after.prop",crafted/"dup-after.prop"],
    records=(b(1,"demo.a","one"),a(1,"demo.a","one"),a(1,"demo.a","two","after-0002")),holds=(("duplicate_declarations",(1,),(2,3)),),
    findings=(issue("AMBIGUOUS_DUPLICATE_DECLARATION","before-0001",1),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0001",1),issue("AMBIGUOUS_DUPLICATE_DECLARATION","after-0002",1)))
inspect_case("unknown-before-holds-apparent-addition",[crafted/"unknown.prop"],[crafted/"one-after.prop"],records=(a(1,"demo.a","one"),),
    holds=(("uninspected_identity_on_opposite_side",(),(1,)),),unidentified=(("before","before-0001",1),),coverage=(issue("UNSUPPORTED_PROPERTY_LINE","before-0001",1),))
inspect_case("import-after-holds-apparent-removal",[crafted/"one-before.prop"],[crafted/"import.prop"],records=(b(1,"demo.a","one"),),
    holds=(("uninspected_identity_on_opposite_side",(1,),()),),unidentified=(("after","after-0001",1),),coverage=(issue("PROPERTY_IMPORT_NOT_FOLLOWED","after-0001",1),))
inspect_case("matched-change-visible-beside-unknown-hold",[crafted/"mixed-before.prop"],[crafted/"mixed-after.prop"],
    records=(b(1,"demo.a","one"),b(2,"demo.b","one"),a(1,"demo.a","two")),changes=(("changed",1,3),),compared=1,
    holds=(("uninspected_identity_on_opposite_side",(2,),()),),unidentified=(("after","after-0001",2),),findings=change_finding,coverage=(issue("UNSUPPORTED_PROPERTY_LINE","after-0001",2),))
literal_records=tuple(b(i,key,value) for i,(key,value) in enumerate(literal,1))+tuple(a(i,key,value) for i,(key,value) in enumerate(reversed(literal),1))
inspect_case("literal-equals-hash-quotes-slash-dollar-empty",[crafted/"literal-before.prop"],[crafted/"literal-after.prop"],details=True,records=literal_records,compared=6,unchanged=6)
inspect_case("empty-values-are-declarations-not-absence",[crafted/"empty.prop"],[crafted/"literal-after.prop"],
    records=tuple(a(i,key,value) for i,(key,value) in enumerate(reversed(literal),1)),changes=tuple(("added",None,i) for i in range(1,7)),compared=6,findings=change_finding)
inspect_case("case-sensitive-key-rename-is-remove-add",[crafted/"case-before.prop"],[crafted/"case-after.prop"],
    records=(b(1,"demo.A","one"),a(1,"demo.a","one")),changes=(("removed",1,None),("added",None,2)),compared=2,findings=change_finding)
inspect_case("nonbreaking-space-is-literal-value-change",[crafted/"nbsp-before.prop"],[crafted/"nbsp-after.prop"],
    records=(b(1,"demo.a","one"),a(1,"demo.a","one\u00a0")),changes=(("changed",1,2),),compared=1,findings=change_finding)
inspect_case("unsupported-keys-rows-imports-stay-coverage",[crafted/"empty.prop"],[crafted/"unsupported.prop"],
    unidentified=tuple(("after","after-0001",i) for i in range(1,4)),coverage=(issue("UNSUPPORTED_PROPERTY_LINE","after-0001",1),issue("UNSUPPORTED_PROPERTY_KEY","after-0001",2),issue("PROPERTY_IMPORT_NOT_FOLLOWED","after-0001",3)))
inspect_case("utf8-bom-crlf-and-final-line",[crafted/"bom.prop"],[crafted/"one-after.prop"],records=(b(1,"demo.a","one"),a(1,"demo.a","one")),compared=1,unchanged=1)
inspect_case("empty-comment-snapshots-have-limited-scope",[crafted/"empty.prop"],[crafted/"comments.prop"])
reserved=(('ro.demo.value','one'),('ctl.demo','one'),('persist.demo.rate','one'))
inspect_case("reserved-looking-prefixes-have-no-runtime-semantics",[crafted/"reserved-before.prop"],[crafted/"reserved-after.prop"],
    records=tuple(b(i,k,v) for i,(k,v) in enumerate(reserved,1))+tuple(a(i,k,v) for i,(k,v) in enumerate(reserved,1)),compared=3,unchanged=3)
html_expect=dict(records=(b(1,"demo.a","old"),a(1,"demo.a","</pre><script>fictional</script>")),changes=(("changed",1,2),),compared=1,findings=change_finding)
html_default=inspect_case("literal-html-private-default",[crafted/"html-before.prop"],[crafted/"html-after.prop"],**html_expect)
html_details=inspect_case("literal-html-details-escaped",[crafted/"html-before.prop"],[crafted/"html-after.prop"],details=True,**html_expect)
assert b'&lt;script&gt;' in (reports[-1]/"report.html").read_bytes()
def without_details(value):
    value=copy.deepcopy(value);value["details_included"]=False
    for row in value["records"]:row.pop("declared_identity",None);row.pop("fields",None)
    return value
for default,details in ((same_default,same_details),(changed_default,changed_details),(review_default,review_details),(html_default,html_details)):
    assert default==without_details(details)
def refuse(case,before,after,code,*,output=None):
    output=output or work/(case+"-report");existed=output.exists();args=[]
    for p in before:args += ["--before",p]
    for p in after:args += ["--after",p]
    args += ["--output",output]
    command(case,"property_diff.py",args,2,dict(status="INCOMPLETE",error=code));assert output.exists()==existed,case
refuse("refuse-before-after-file-alias",[fixtures/"before.prop"],[fixtures/"before.prop"],"DUPLICATE_INPUT_FILE")
refuse("refuse-duplicate-after-file",[fixtures/"before.prop"],[fixtures/"same.prop",fixtures/"same.prop"],"DUPLICATE_INPUT_FILE")
refuse("refuse-existing-report",[fixtures/"before.prop"],[fixtures/"same.prop"],"OUTPUT_EXISTS",output=reports[0])
command("refuse-existing-generator-directory","examples/generate.py",["--output",fixtures],2,dict(status="INCOMPLETE",error="OUTPUT_EXISTS"))
refuse("refuse-relative-input",["fixtures/before.prop"],[fixtures/"same.prop"],"LOCAL_ABSOLUTE_PATH_REQUIRED")
refuse("refuse-required-before-missing",[],[fixtures/"same.prop"],"ARGUMENTS_INVALID")
refuse("refuse-invalid-utf8",[crafted/"empty.prop"],[crafted/"invalid.prop"],"UTF8_REQUIRED")
refuse("refuse-physical-control",[crafted/"empty.prop"],[crafted/"control.prop"],"TEXT_CONTROL_UNSUPPORTED")
refuse("refuse-physical-line-bound",[crafted/"empty.prop"],[crafted/"line.prop"],"TEXT_LINE_LIMIT")
refuse("refuse-input-byte-bound",[crafted/"empty.prop"],[crafted/"bytes.prop"],"INPUT_BYTE_LIMIT")
refuse("refuse-record-collection-bound",[crafted/"empty.prop"],[crafted/"record.prop"],"RECORD_LIMIT")
refuse("refuse-selected-file-count",[fixtures/"before.prop"],[fixtures/"same.prop"]*32,"INPUT_COUNT_LIMIT")
assert inputs=={name:digest((work/name).read_bytes()) for name in inputs}
assert runtime=={name:digest((module/name).read_bytes()) for name in runtime_names}
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
expected_files=set(inputs)
for output in reports:expected_files.update((output/name).relative_to(work).as_posix() for name in ("report.json","report.html","MANIFEST.json"))
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()}==expected_files
print(json.dumps(dict(outcomes=outcomes,reports_verified=len(reports),payload_hashes_verified=2*len(reports),input_hashes_checked=input_hashes_checked,
    fixture_files_preserved=len(inputs),expected_workspace_files=len(expected_files),unexpected_application_files=0,details_mode_counts=mode_counts,
    details_do_not_change_observations=True,bytecode_files=0,runtime_bytes_preserved=True,property_imports_followed=False,device_properties_changed=False,
    effective_properties_merged=False,override_precedence_evaluated=False,property_permissions_checked=False,runtime_compatibility_verified=False,
    devices_accessed=False,real_property_snapshots_used=False),sort_keys=True))
```

## Exact expected case outcomes

```json
[
  {
    "case": "create-fictional-property-snapshots",
    "exit_code": 0
  },
  {
    "case": "comments-whitespace-order-same-default",
    "exit_code": 0
  },
  {
    "case": "comments-whitespace-order-same-details",
    "exit_code": 0
  },
  {
    "case": "changed-and-added-values-default",
    "exit_code": 1
  },
  {
    "case": "changed-and-added-values-details",
    "exit_code": 1
  },
  {
    "case": "duplicate-import-held-default",
    "exit_code": 1
  },
  {
    "case": "duplicate-import-held-details",
    "exit_code": 1
  },
  {
    "case": "multi-before-after-fragments-no-order-precedence",
    "exit_code": 0
  },
  {
    "case": "before-duplicates-do-not-invent-removal",
    "exit_code": 1
  },
  {
    "case": "equal-after-duplicates-still-ambiguous",
    "exit_code": 1
  },
  {
    "case": "duplicate-across-after-files-held",
    "exit_code": 1
  },
  {
    "case": "unknown-before-holds-apparent-addition",
    "exit_code": 1
  },
  {
    "case": "import-after-holds-apparent-removal",
    "exit_code": 1
  },
  {
    "case": "matched-change-visible-beside-unknown-hold",
    "exit_code": 1
  },
  {
    "case": "literal-equals-hash-quotes-slash-dollar-empty",
    "exit_code": 0
  },
  {
    "case": "empty-values-are-declarations-not-absence",
    "exit_code": 1
  },
  {
    "case": "case-sensitive-key-rename-is-remove-add",
    "exit_code": 1
  },
  {
    "case": "nonbreaking-space-is-literal-value-change",
    "exit_code": 1
  },
  {
    "case": "unsupported-keys-rows-imports-stay-coverage",
    "exit_code": 1
  },
  {
    "case": "utf8-bom-crlf-and-final-line",
    "exit_code": 0
  },
  {
    "case": "empty-comment-snapshots-have-limited-scope",
    "exit_code": 0
  },
  {
    "case": "reserved-looking-prefixes-have-no-runtime-semantics",
    "exit_code": 0
  },
  {
    "case": "literal-html-private-default",
    "exit_code": 1
  },
  {
    "case": "literal-html-details-escaped",
    "exit_code": 1
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

The summary records 36 cases: eight exit 0, sixteen review exit 1 and twelve
incomplete exit 2 results. Twenty-three report manifests cover 46 payloads;
49 selected input hash observations, 36 unchanged fictional inputs and 105
exact input/report files are checked. Eighteen reports use defaults and five
request details; four privacy pairs preserve observations.

All eight scope fields stay false: import following, property modification,
effective merging, precedence/permission/runtime evaluation, device access and
real snapshots. Read [FORMAT.md](docs/FORMAT.md) and
[QUALIFICATION.md](docs/QUALIFICATION.md). Supported partial changes coexist
with coverage; unmatched holds deliberately avoid unsupported absence claims.
