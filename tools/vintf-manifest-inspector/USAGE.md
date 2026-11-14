# Fictional VINTF declaration indexing and comparison walkthrough

This guide reviews invented saved XML only. It never uses a native XML parser,
opens external resources, merges device configuration, applies overrides,
evaluates compatibility matrices, checks runtime HALs or accesses devices.
Selected declaration observations are not device/service compatibility proof.

Use Python 3.12–3.15 without third-party packages. Formal guide evidence uses a
fresh no-pip CPython 3.15.2 environment with external copies of the actual four
runtime/generator files. Assertions must stay enabled. Actual CLI commands use
`-E -s -B` to preserve sibling imports while disabling environment/user-site
settings and bytecode writes. The driver itself uses `-I -B`.

From the extracted module folder, save the single Python block below as
`fictional_vintf_walkthrough.py` in an existing absolute private directory
outside the source tree. Replace the fictional path with an owned directory;
avoid links/reparse routes, network paths and actual device manifests. The
driver creates one new workspace and never deletes earlier evidence.

PowerShell 5.1 or newer:

```powershell
$module = (Get-Location).Path
$privateParent = 'D:\Private-Review'
python -I -B "$privateParent/fictional_vintf_walkthrough.py" "$module" "$privateParent"
```

POSIX shell, using an existing owned private directory:

```sh
module="$PWD"
privateParent="$HOME/private-review"
python3 -I -B "$privateParent/fictional_vintf_walkthrough.py" "$module" "$privateParent"
```

Generated examples cover HIDL/AIDL indexing, equivalent interface/fqname forms,
transport/architecture changes and version removal/addition. Review XML includes
duplicate declarations, an unevaluated override, a processing instruction and
out-of-scope metadata. A separate comparison explicitly selects two before and
two current fragments without inferring an effective merged device manifest.

Other fixtures check instance/type identity changes, duplicates held on either
side, conflicting transports, distinct device/framework keys, target-level
outside instance-diff scope, namespace/XInclude coverage, unknown transport
omission, missing AIDL defaults and unsupported old AIDL metadata. Valid empty
manifests have only limited empty scope. BOM/CRLF and numeric references are
supported; raw/unsupported values are not guessed into accepted fields.

The included restricted reader decodes supported references once; its preserved
tests separately check exact reference decoding. It does not resolve includes,
schemas, DTDs or external entities. Twenty-five controlled refusals cover
DTD/entity/CDATA, malformed trees/references, duplicate attributes, encoded
controls, XML declaration/structure/text/attribute bounds, UTF-8/control/line/file
bounds, input aliases across roles, existing outputs, arguments and file count.

Four default/details pairs preserve observations after stripping only opt-in
fields/mode. An additional details report checks unknown transport text stays
omitted. Raw XML/comments/local filenames remain omitted in both modes. HTML
escapes the complete JSON representation. Hashes, element ordinals, IDs and
structure can identify inputs: omission is not anonymization.

Expected declaration ordinals, identities, changes, ambiguity and findings are
supplied explicitly; the driver does not import or reuse the inspector/parser.
It checks whole reports, exact stdout bytes and empty stderr; independently
recomputes selected input/report hashes; and checks unchanged fixtures/runtime
bytes, exact created files and no bytecode. Review/incomplete exits are checked
internally; the driver exits 0 only when every assertion passes. Unsigned hashes
show consistency rather than authenticity, rights or device correctness.

## Executable driver

```python
"""Review authored VINTF XML only; never merge device state or contact HALs."""
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
work = Path(tempfile.mkdtemp(prefix="fictional-vintf-text-", dir=parent)).resolve()
assert work.parent == parent
runtime_names = ("vintf_inspector.py", "restricted_xml.py", "inspection_support.py", "examples/generate.py")
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
runtime = {name: digest((module/name).read_bytes()) for name in runtime_names}
outcomes = []

def command(case, script, args, expected_exit, expected_stdout):
    before = {p.relative_to(work).as_posix(): digest(p.read_bytes()) for p in work.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-E", "-s", "-B", str(module/script), *map(str,args)],
                            cwd=work, capture_output=True, timeout=60)
    assert result.returncode == expected_exit and result.stderr == b"", (case,result.stdout,result.stderr)
    assert json.loads(result.stdout) == expected_stdout, (case,result.stdout)
    assert result.stdout == (json.dumps(expected_stdout,sort_keys=True)+os.linesep).encode(), case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before == {name: digest((work/name).read_bytes()) for name in before}, case
    outcomes.append(dict(case=case,exit_code=result.returncode))

command("create-fictional-vintf-text","examples/generate.py",["--output",work/"fixtures"],0,
        dict(status="FICTIONAL_EXAMPLES_CREATED",files=4))
fixtures=work/"fixtures"
assert {p.name for p in fixtures.iterdir()} == {"clean.xml","same.xml","changed.xml","review.xml"}
crafted=work/"crafted"; crafted.mkdir()
def manifest(content="",kind="device",version="2.0",extra=""):
    return f'<manifest version="{version}" type="{kind}"{extra}>{content}</manifest>\n'
def hidl(fq="@2.1::IDemo/default",transport='<transport>hwbinder</transport>',extra=""):
    return '<hal'+extra+'><name>example.hardware.demo</name>'+transport+'<fqname>'+fq+'</fqname></hal>'
def aidl(version="1",instance="default"):
    return '<hal format="aidl"><name>example.hardware.helper</name><version>'+version+'</version><fqname>IHelper/'+instance+'</fqname></hal>'
values={
    "hidl-before.xml":manifest(hidl()),
    "hidl-current.xml":manifest(hidl()),
    "aidl-before.xml":manifest(aidl()),
    "aidl-current.xml":manifest(aidl()),
    "version.xml":manifest(hidl('@2.2::IDemo/default')),
    "instance.xml":manifest(hidl('@2.1::IDemo/alternate')),
    "duplicate.xml":manifest(hidl()+hidl()),
    "conflict.xml":manifest(hidl()+hidl(transport='<transport arch="32">passthrough</transport>')),
    "framework.xml":manifest(hidl(),kind="framework"),
    "root-metadata.xml":manifest(hidl(),extra=' target-level="99"'),
    "namespace.xml":'<manifest xmlns="urn:fiction" version="2.0" type="device"/>\n',
    "xinclude.xml":manifest('<x:include xmlns:x="http://www.w3.org/2001/XInclude" href="file:///fictional/not-opened.xml"/>'),
    "unknown-transport.xml":manifest(hidl(transport='<transport>fictional_unknown_transport</transport>')),
    "aidl-no-version.xml":manifest('<hal format="aidl"><name>example.hardware.helper</name><fqname>IHelper/default</fqname></hal>'),
    "aidl-old-meta.xml":manifest(aidl(),version="1.0"),
    "empty.xml":manifest(),
    "numeric-reference.xml":'<?xml version="1.0" encoding="UTF-8"?>\n'+manifest(hidl().replace('example.hardware.demo','ex&#97;mple.hardware.demo').replace('IDemo/default','IDemo/def&#x61;ult')),
    "once-reference.xml":manifest(hidl().replace('example.hardware.demo','example.hardware.&amp;lt;')),
    "dtd.xml":'<!DOCTYPE manifest SYSTEM "file:///fictional/not-opened.dtd">'+manifest(),
    "entity.xml":'<!ENTITY fiction "literal">'+manifest(),
    "cdata.xml":manifest('<![CDATA[fiction]]>'),
    "unbalanced.xml":'<manifest version="2.0" type="device">',
    "duplicate-attribute.xml":'<manifest version="2.0" type="device" type="framework"/>',
    "unknown-reference.xml":manifest('<x>&unknown;</x>'),
    "surrogate.xml":manifest('<x>&#xD800;</x>'),
    "reference-control.xml":manifest('<x>&#13;</x>'),
    "non-utf8-declaration.xml":'<?xml version="1.0" encoding="iso-8859-1"?>'+manifest(),
    "depth.xml":manifest('<a>'*33+'</a>'*33),
    "elements.xml":manifest('\n'+'\n'.join('<x/>' for _ in range(8001))+'\n'),
    "attributes.xml":'<manifest version="2.0" type="device" '+' '.join(f'a{i}="x"' for i in range(17))+'/>',
    "attribute-value.xml":manifest(extra=' other="'+('a'*1025)+'"'),
    "text.xml":manifest('<x>'+('\n'+('a'*100)+'<!-- fiction -->')*100+'</x>'),
    "physical-control.xml":manifest()+'\x00',
    "line.xml":'X'*8193,
    "bytes.xml":'#'*(1024*1024+1),
}
for name,text in values.items():
    (crafted/name).write_bytes(text.encode())
(crafted/"invalid-utf8.xml").write_bytes(b'\xff')
(crafted/"numeric-reference.xml").write_bytes(b'\xef\xbb\xbf'+(crafted/"numeric-reference.xml").read_bytes().replace(b'\n',b'\r\n'))
inputs={p.relative_to(work).as_posix():digest(p.read_bytes()) for folder in (fixtures,crafted) for p in folder.iterdir()}
assert len(inputs)==40
reports=[]; input_hashes_checked=0; mode_counts={"default":0,"included":0}
def did(index):
    return f"declaration-{index:04d}"
def signal(code,source,element):
    return dict(code=code,source=source,element=element)
def hidl_fields(version="2.1",instance="default",transport="hwbinder",arch=None):
    return dict(package="example.hardware.demo",version=version,interface="IDemo",instance=instance,transport=transport,arch=arch)
def aidl_fields(version="1",instance="default"):
    return dict(package="example.hardware.helper",version=version,interface="IHelper",instance=instance,transport=None,arch=None)
def decl(source,side,element,fmt="hidl",kind="device",fields=None):
    return (source,side,element,fmt,kind,fields or hidl_fields())
def expected_report(current,before=None,*,declarations=(),hal_count=0,changes=(),ambiguity=(),findings=(),coverage=(),details=False):
    # Every identity, pairing, ordinal, change and finding expectation is explicit.
    # This helper neither parses XML nor computes declaration matches.
    src=[(f"before-{i:04d}",p) for i,p in enumerate(before or (),1)]+[(f"current-{i:04d}",p) for i,p in enumerate(current,1)]
    result=dict(schema_version=1,tool="Android VINTF Manifest Inspector",
        scope="Literal supported HAL instances in selected XML; no effective manifest merge or compatibility evaluation.",
        details_included=details,comparison_requested=before is not None,
        inputs=[dict(id=label,bytes=len(p.read_bytes()),sha256=digest(p.read_bytes())) for label,p in src],
        hal_elements_observed=hal_count,declarations=[],changes=[],ambiguous_comparisons=[],findings=list(findings),coverage_issues=list(coverage))
    for index,(source,side,element,fmt,kind,fields) in enumerate(declarations,1):
        row=dict(id=did(index),source=source,side=side,element=element,format=fmt,manifest_type=kind)
        if details:row["fields"]=fields
        result["declarations"].append(row)
    for kind,previous,now,fields in changes:
        result["changes"].append(dict(kind=kind,before_id=did(previous) if previous else None,current_id=did(now) if now else None,fields_changed=list(fields)))
    for previous,now in ambiguity:
        result["ambiguous_comparisons"].append(dict(before_ids=[did(i) for i in previous],current_ids=[did(i) for i in now]))
    result["comparison_scope"]="Identity includes manifest type, format, package, version, interface and instance. Version changes are removal/addition. Duplicates are never arbitrarily paired."
    result["status"]="REVIEW_REQUIRED" if findings or coverage else "NO_SCOPE_FINDINGS"
    return result
def inspect_case(case,current,before=None,*,details=False,**expectations):
    global input_hashes_checked
    current=tuple(current);before=tuple(before) if before is not None else None
    output=work/(case+"-report")
    expected=expected_report(current,before,details=details,**expectations)
    args=[]
    for path in before or ():args += ["--before",path]
    for path in current:args += ["--file",path]
    args += ["--output",output]
    if details:args += ["--include-details"]
    status=expected["status"]
    command(case,"vintf_inspector.py",args,int(status!="NO_SCOPE_FINDINGS"),
        dict(status=status,declarations=len(expected["declarations"]),changes=len(expected["changes"]),coverage_issues=len(expected["coverage_issues"])))
    assert {p.name for p in output.iterdir()}=={"report.json","report.html","MANIFEST.json"}
    raw=(output/"report.json").read_bytes();page=(output/"report.html").read_bytes()
    assert json.loads(raw)==expected,case
    assert raw==(json.dumps(expected,indent=2,ensure_ascii=True,allow_nan=False)+"\n").encode(),case
    assert b"<script" not in page and b"http://" not in page and b"https://" not in page
    assert b"<pre>"+html.escape(raw.decode(),quote=True).encode()+b"</pre>" in page
    manifest_value=json.loads((output/"MANIFEST.json").read_bytes())
    assert manifest_value==dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=digest(data))
        for name,data in sorted({"report.json":raw,"report.html":page}.items())])
    if not details:
        assert not any(word in raw for word in (b'"fields"',b'example.hardware',b'IDemo',b'IHelper',b'fictional_unknown_transport'))
    assert str(work).encode() not in raw and str(module).encode() not in raw
    input_hashes_checked+=len(expected["inputs"]);mode_counts["included" if details else "default"]+=1
    reports.append(output);return expected

index=dict(declarations=(decl("current-0001","current",8),decl("current-0001","current",12,"aidl",fields=aidl_fields())),hal_count=2)
index_default=inspect_case("index-supported-hidl-aidl-default",[fixtures/"clean.xml"],**index)
index_details=inspect_case("index-supported-hidl-aidl-details",[fixtures/"clean.xml"],details=True,**index)
equivalent=dict(declarations=(decl("before-0001","before",8),decl("before-0001","before",12,"aidl",fields=aidl_fields()),
    decl("current-0001","current",5),decl("current-0001","current",11,"aidl",fields=aidl_fields())),hal_count=4)
equivalent_default=inspect_case("equivalent-interface-fqname-forms-default",[fixtures/"same.xml"],[fixtures/"clean.xml"],**equivalent)
equivalent_details=inspect_case("equivalent-interface-fqname-forms-details",[fixtures/"same.xml"],[fixtures/"clean.xml"],details=True,**equivalent)
changed=dict(declarations=(decl("before-0001","before",8),decl("before-0001","before",12,"aidl",fields=aidl_fields()),
    decl("current-0001","current",5,fields=hidl_fields(transport="passthrough",arch="64")),decl("current-0001","current",9,"aidl",fields=aidl_fields(version="2"))),hal_count=4,
    changes=(("changed",1,3,("transport","arch")),("removed",2,None,()),("added",None,4,())),
    findings=(signal("SELECTED_HAL_DECLARATIONS_CHANGED","comparison",0),))
changed_default=inspect_case("transport-arch-and-version-review-default",[fixtures/"changed.xml"],[fixtures/"clean.xml"],**changed)
changed_details=inspect_case("transport-arch-and-version-review-details",[fixtures/"changed.xml"],[fixtures/"clean.xml"],details=True,**changed)
review=dict(declarations=(decl("current-0001","current",5),decl("current-0001","current",6)),hal_count=1,
    findings=(signal("REPEATED_SELECTED_DECLARATION","current-0001",5),signal("REPEATED_SELECTED_DECLARATION","current-0001",6)),
    coverage=(signal("PROCESSING_INSTRUCTION_UNINSPECTED","current-0001",0),signal("HAL_MODIFIERS_NOT_EVALUATED","current-0001",2),signal("UNINSPECTED_MANIFEST_ELEMENT","current-0001",7)))
review_default=inspect_case("duplicate-override-and-processing-instruction-default",[fixtures/"review.xml"],**review)
review_details=inspect_case("duplicate-override-and-processing-instruction-details",[fixtures/"review.xml"],details=True,**review)
inspect_case("two-before-two-current-selected-fragments",[crafted/"hidl-current.xml",crafted/"aidl-current.xml"],[crafted/"hidl-before.xml",crafted/"aidl-before.xml"],
    declarations=(decl("before-0001","before",5),decl("before-0002","before",5,"aidl",fields=aidl_fields()),
                  decl("current-0001","current",5),decl("current-0002","current",5,"aidl",fields=aidl_fields())),hal_count=4)
change_finding=(signal("SELECTED_HAL_DECLARATIONS_CHANGED","comparison",0),)
inspect_case("hidl-version-change-is-removal-addition",[crafted/"version.xml"],[crafted/"hidl-before.xml"],
    declarations=(decl("before-0001","before",5),decl("current-0001","current",5,fields=hidl_fields(version="2.2"))),hal_count=2,
    changes=(("removed",1,None,()),("added",None,2,())),findings=change_finding)
inspect_case("instance-identity-change-is-removal-addition",[crafted/"instance.xml"],[crafted/"hidl-before.xml"],
    declarations=(decl("before-0001","before",5),decl("current-0001","current",5,fields=hidl_fields(instance="alternate"))),hal_count=2,
    changes=(("removed",1,None,()),("added",None,2,())),findings=change_finding)
inspect_case("current-duplicates-held-without-pairing",[crafted/"duplicate.xml"],[crafted/"hidl-before.xml"],
    declarations=(decl("before-0001","before",5),decl("current-0001","current",5),decl("current-0001","current",9)),hal_count=3,
    ambiguity=(((1,),(2,3)),),findings=(signal("REPEATED_SELECTED_DECLARATION","current-0001",5),signal("REPEATED_SELECTED_DECLARATION","current-0001",9)))
inspect_case("before-duplicates-held-without-pairing",[crafted/"hidl-current.xml"],[crafted/"duplicate.xml"],
    declarations=(decl("before-0001","before",5),decl("before-0001","before",9),decl("current-0001","current",5)),hal_count=3,
    ambiguity=(((1,2),(3,)),),findings=(signal("REPEATED_SELECTED_DECLARATION","before-0001",5),signal("REPEATED_SELECTED_DECLARATION","before-0001",9)))
inspect_case("conflicting-selected-transport-declarations",[crafted/"conflict.xml"],
    declarations=(decl("current-0001","current",5),decl("current-0001","current",9,fields=hidl_fields(transport="passthrough",arch="32"))),hal_count=2,
    findings=(signal("CONFLICTING_SELECTED_DECLARATION","current-0001",5),signal("CONFLICTING_SELECTED_DECLARATION","current-0001",9)))
inspect_case("device-framework-keys-remain-distinct",[crafted/"hidl-current.xml",crafted/"framework.xml"],
    declarations=(decl("current-0001","current",5),decl("current-0002","current",5,kind="framework")),hal_count=2)
inspect_case("manifest-type-change-is-removal-addition",[crafted/"framework.xml"],[crafted/"hidl-before.xml"],
    declarations=(decl("before-0001","before",5),decl("current-0001","current",5,kind="framework")),hal_count=2,
    changes=(("removed",1,None,()),("added",None,2,())),findings=change_finding)
inspect_case("target-level-outside-instance-diff",[crafted/"root-metadata.xml"],[crafted/"hidl-before.xml"],
    declarations=(decl("before-0001","before",5),decl("current-0001","current",5)),hal_count=2)
inspect_case("namespace-is-coverage-not-inferred-declarations",[crafted/"namespace.xml"],
    coverage=(signal("UNSUPPORTED_XML_NAMESPACE","current-0001",1),))
inspect_case("xinclude-resource-not-followed",[crafted/"xinclude.xml"],coverage=(signal("UNSUPPORTED_XML_NAMESPACE","current-0001",1),))
unknown=inspect_case("unknown-transport-omitted-even-with-details",[crafted/"unknown-transport.xml"],details=True,
    declarations=(decl("current-0001","current",5,fields=hidl_fields(transport=None)),),hal_count=1,
    coverage=(signal("HIDL_TRANSPORT_NEEDS_REVIEW","current-0001",4),))
assert "fictional_unknown_transport" not in json.dumps(unknown)
inspect_case("aidl-default-version-not-inferred",[crafted/"aidl-no-version.xml"],hal_count=1,
    coverage=(signal("EXPLICIT_SINGLE_AIDL_VERSION_REQUIRED","current-0001",2),signal("HAL_WITHOUT_SUPPORTED_INSTANCE_DECLARATION","current-0001",2)))
inspect_case("aidl-old-meta-version-remains-coverage",[crafted/"aidl-old-meta.xml"],hal_count=1,
    coverage=(signal("AIDL_REQUIRES_SUPPORTED_META_VERSION","current-0001",2),))
inspect_case("valid-empty-manifest-limited-scope",[crafted/"empty.xml"])
inspect_case("bom-crlf-and-numeric-references",[crafted/"numeric-reference.xml"],declarations=(decl("current-0001","current",5),),hal_count=1)
inspect_case("reference-output-not-guessed-as-package",[crafted/"once-reference.xml"],hal_count=1,
    coverage=(signal("UNSUPPORTED_PACKAGE_NAME","current-0001",2),))
def without_details(value):
    value=copy.deepcopy(value);value["details_included"]=False
    for row in value["declarations"]:row.pop("fields",None)
    return value
for default,details in ((index_default,index_details),(equivalent_default,equivalent_details),(changed_default,changed_details),(review_default,review_details)):
    assert default==without_details(details)

def refuse(case,current,code,*,before=(),output=None):
    output=output or work/(case+"-report");existed=output.exists();args=[]
    for path in before:args += ["--before",path]
    for path in current:args += ["--file",path]
    args += ["--output",output]
    command(case,"vintf_inspector.py",args,2,dict(status="INCOMPLETE",error=code))
    assert output.exists()==existed,case
refuse("refuse-dtd-before-external-resolution",[crafted/"dtd.xml"],"XML_DECLARATIONS_REJECTED")
refuse("refuse-entity-declaration",[crafted/"entity.xml"],"XML_DECLARATIONS_REJECTED")
refuse("refuse-cdata-markup",[crafted/"cdata.xml"],"XML_MARKUP_UNSUPPORTED")
refuse("refuse-unbalanced-xml",[crafted/"unbalanced.xml"],"INVALID_XML")
refuse("refuse-duplicate-attribute",[crafted/"duplicate-attribute.xml"],"DUPLICATE_XML_ATTRIBUTE")
refuse("refuse-unknown-reference",[crafted/"unknown-reference.xml"],"INVALID_XML_REFERENCE")
refuse("refuse-surrogate-reference",[crafted/"surrogate.xml"],"INVALID_XML_REFERENCE")
refuse("refuse-encoded-control",[crafted/"reference-control.xml"],"XML_REFERENCE_CONTROL_UNSUPPORTED")
refuse("refuse-non-utf8-declaration",[crafted/"non-utf8-declaration.xml"],"XML_UTF8_DECLARATION_REQUIRED")
refuse("refuse-tree-depth-bound",[crafted/"depth.xml"],"XML_STRUCTURE_LIMIT")
refuse("refuse-element-count-bound",[crafted/"elements.xml"],"XML_STRUCTURE_LIMIT")
refuse("refuse-attribute-count-bound",[crafted/"attributes.xml"],"XML_ATTRIBUTE_LIMIT")
refuse("refuse-attribute-value-bound",[crafted/"attribute-value.xml"],"XML_ATTRIBUTE_LIMIT")
refuse("refuse-accumulated-text-bound",[crafted/"text.xml"],"XML_TEXT_LIMIT")
refuse("refuse-invalid-utf8-bytes",[crafted/"invalid-utf8.xml"],"UTF8_REQUIRED")
refuse("refuse-physical-control",[crafted/"physical-control.xml"],"TEXT_CONTROL_UNSUPPORTED")
refuse("refuse-physical-line-bound",[crafted/"line.xml"],"TEXT_LINE_LIMIT")
refuse("refuse-input-byte-bound",[crafted/"bytes.xml"],"INPUT_BYTE_LIMIT")
refuse("refuse-repeated-current-file",[fixtures/"clean.xml",fixtures/"clean.xml"],"DUPLICATE_INPUT_FILE")
refuse("refuse-before-current-same-file",[fixtures/"clean.xml"],"DUPLICATE_INPUT_FILE",before=[fixtures/"clean.xml"])
refuse("refuse-existing-report",[fixtures/"clean.xml"],"OUTPUT_EXISTS",output=reports[0])
command("refuse-existing-generator-directory","examples/generate.py",["--output",fixtures],2,dict(status="INCOMPLETE",error="OUTPUT_EXISTS"))
refuse("refuse-relative-input",["fixtures/clean.xml"],"LOCAL_ABSOLUTE_PATH_REQUIRED")
refuse("refuse-required-current-selection-missing",[],"ARGUMENTS_INVALID")
refuse("refuse-total-selected-file-count",[crafted/"empty.xml"]*33,"INPUT_COUNT_LIMIT")
assert inputs=={name:digest((work/name).read_bytes()) for name in inputs}
assert runtime=={name:digest((module/name).read_bytes()) for name in runtime_names}
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
expected_files=set(inputs)
for output in reports:
    expected_files.update((output/name).relative_to(work).as_posix() for name in ("report.json","report.html","MANIFEST.json"))
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()}==expected_files
print(json.dumps(dict(outcomes=outcomes,reports_verified=len(reports),payload_hashes_verified=2*len(reports),
    input_hashes_checked=input_hashes_checked,fixture_files_preserved=len(inputs),expected_workspace_files=len(expected_files),
    unexpected_application_files=0,details_mode_counts=mode_counts,details_do_not_change_observations=True,
    bytecode_files=0,runtime_bytes_preserved=True,native_xml_parser_used=False,external_resources_opened=False,
    device_configuration_merged=False,overrides_applied=False,compatibility_matrix_evaluated=False,
    runtime_hal_services_checked=False,devices_accessed=False,real_device_manifests_used=False),sort_keys=True))
```

## Exact expected case outcomes

```json
[
  {
    "case": "create-fictional-vintf-text",
    "exit_code": 0
  },
  {
    "case": "index-supported-hidl-aidl-default",
    "exit_code": 0
  },
  {
    "case": "index-supported-hidl-aidl-details",
    "exit_code": 0
  },
  {
    "case": "equivalent-interface-fqname-forms-default",
    "exit_code": 0
  },
  {
    "case": "equivalent-interface-fqname-forms-details",
    "exit_code": 0
  },
  {
    "case": "transport-arch-and-version-review-default",
    "exit_code": 1
  },
  {
    "case": "transport-arch-and-version-review-details",
    "exit_code": 1
  },
  {
    "case": "duplicate-override-and-processing-instruction-default",
    "exit_code": 1
  },
  {
    "case": "duplicate-override-and-processing-instruction-details",
    "exit_code": 1
  },
  {
    "case": "two-before-two-current-selected-fragments",
    "exit_code": 0
  },
  {
    "case": "hidl-version-change-is-removal-addition",
    "exit_code": 1
  },
  {
    "case": "instance-identity-change-is-removal-addition",
    "exit_code": 1
  },
  {
    "case": "current-duplicates-held-without-pairing",
    "exit_code": 1
  },
  {
    "case": "before-duplicates-held-without-pairing",
    "exit_code": 1
  },
  {
    "case": "conflicting-selected-transport-declarations",
    "exit_code": 1
  },
  {
    "case": "device-framework-keys-remain-distinct",
    "exit_code": 0
  },
  {
    "case": "manifest-type-change-is-removal-addition",
    "exit_code": 1
  },
  {
    "case": "target-level-outside-instance-diff",
    "exit_code": 0
  },
  {
    "case": "namespace-is-coverage-not-inferred-declarations",
    "exit_code": 1
  },
  {
    "case": "xinclude-resource-not-followed",
    "exit_code": 1
  },
  {
    "case": "unknown-transport-omitted-even-with-details",
    "exit_code": 1
  },
  {
    "case": "aidl-default-version-not-inferred",
    "exit_code": 1
  },
  {
    "case": "aidl-old-meta-version-remains-coverage",
    "exit_code": 1
  },
  {
    "case": "valid-empty-manifest-limited-scope",
    "exit_code": 0
  },
  {
    "case": "bom-crlf-and-numeric-references",
    "exit_code": 0
  },
  {
    "case": "reference-output-not-guessed-as-package",
    "exit_code": 1
  },
  {
    "case": "refuse-dtd-before-external-resolution",
    "exit_code": 2
  },
  {
    "case": "refuse-entity-declaration",
    "exit_code": 2
  },
  {
    "case": "refuse-cdata-markup",
    "exit_code": 2
  },
  {
    "case": "refuse-unbalanced-xml",
    "exit_code": 2
  },
  {
    "case": "refuse-duplicate-attribute",
    "exit_code": 2
  },
  {
    "case": "refuse-unknown-reference",
    "exit_code": 2
  },
  {
    "case": "refuse-surrogate-reference",
    "exit_code": 2
  },
  {
    "case": "refuse-encoded-control",
    "exit_code": 2
  },
  {
    "case": "refuse-non-utf8-declaration",
    "exit_code": 2
  },
  {
    "case": "refuse-tree-depth-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-element-count-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-attribute-count-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-attribute-value-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-accumulated-text-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-invalid-utf8-bytes",
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
    "case": "refuse-repeated-current-file",
    "exit_code": 2
  },
  {
    "case": "refuse-before-current-same-file",
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
    "case": "refuse-required-current-selection-missing",
    "exit_code": 2
  },
  {
    "case": "refuse-total-selected-file-count",
    "exit_code": 2
  }
]
```

The summary records 51 cases: ten exit 0, sixteen review exit 1 and twenty-five
incomplete exit 2 results. Twenty-five report manifests cover fifty payloads;
39 selected input hash observations, forty preserved fictional inputs and 115
exact input/report files are checked. Twenty reports use defaults and five
request details; four pairs preserve observations.

All eight scope fields stay false: native XML parser use, external resource
access, effective device merging, override application, compatibility-matrix
evaluation, runtime HAL service checks, device access and real device manifests.
Read [FORMAT.md](docs/FORMAT.md) and [QUALIFICATION.md](docs/QUALIFICATION.md).
Clean selected results do not prove a full schema, effective state, successful
boot or runtime service presence. Unsupported grammar remains coverage.
