# Fictional saved-event JSON and XML walkthrough

This guide reviews invented saved metadata only. It never queries live logs,
decodes EVTX/EVT binaries, uses a native XML parser or opens external resources.
Computers and raw payload/security fields are not serialized. Observed gaps,
groups or record IDs do not verify capture completeness, host identity or cause.

Use Python 3.12–3.15 without third-party packages. Formal guide evidence uses a
fresh no-pip CPython 3.15.2 environment with external copies of the actual four
runtime/generator files. Assertions must stay enabled. CLI/generator uses
`-E -s -B` for sibling imports without environment/user-site settings or bytecode.
The independent driver itself uses `-I -B`.

From the extracted module folder, save the single Python block below as
`fictional_event_walkthrough.py` in an existing absolute private directory
outside source. Replace the fictional path with an owned directory; avoid
links/reparse routes, network paths and actual event captures. The driver
creates one new workspace and never deletes earlier evidence.

PowerShell 5.1 or newer:

```powershell
$module = (Get-Location).Path
$privateParent = 'D:\Private-Review'
python -I -B "$privateParent/fictional_event_walkthrough.py" "$module" "$privateParent"
```

POSIX shell, using an existing owned private directory:

```sh
module="$PWD"
privateParent="$HOME/private-review"
python3 -I -B "$privateParent/fictional_event_walkthrough.py" "$module" "$privateParent"
```

Generated JSON/XML describe the same accepted events; both privacy modes must
preserve their timeline/groups. Review examples distinguish duplicate/conflicting
record IDs, gaps and naive-time coverage. Additional fixtures check one-tick
offset/fraction arithmetic, reverse input, stable ties, strict threshold versus
zero-disabled gaps, exact large decimal ticks/record IDs and distinct optional
group keys. Repeated accepted events stay counted, including identical copies
in separate files; missing identities do not imply duplicates.

Record-ID checks stay within one selected file plus declared computer/channel/ID.
Computers are never serialized, even with details. Unknown message/security
fields and XML payload markers remain omitted. A literal provider name in
details is escaped in HTML. Three privacy pairs preserve observations after
removing only accepted opt-in fields/mode. Omission is not anonymization.

XML namespace resets, unknown fields/instructions and encoded controls in
identifying metadata remain coverage. The original Event reader allows encoded
CR in discarded payload text, unlike some sibling tools. JSON uses separate
structure/string budgets and accepts a long physical line that XML would refuse.
No reader/helper is copied from another tool. No manual command from the
retained export guide is executed; all inputs are authored in this driver.

Whole-report expectations supply explicit timeline order, ticks, groups,
findings and coverage. The driver imports no inspector/parser and reuses no
timestamp/matching implementation. It checks exact stdout, empty stderr,
independent input/report hashes, immutable fixture/runtime bytes, exact created
files and no bytecode. Twenty-three controlled refusals cover strict JSON,
restricted XML, resource/file bounds, aliases, output reuse and arguments.
Review/refusal exits are checked internally; the driver exits 0 only when all
assertions pass. Unsigned hashes prove consistency rather than origin or rights.

## Executable driver

```python
"""Review fictional saved event metadata only; never query event logs."""
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
module=Path(sys.argv[1]).resolve(strict=True)
parent=Path(sys.argv[2]).resolve(strict=True)
assert module.is_absolute() and parent.is_absolute() and parent.is_dir()
assert not parent.is_relative_to(module) and not module.is_relative_to(parent)
assert not module.is_symlink() and not parent.is_symlink()
assert not getattr(parent,"is_junction",lambda:False)()
work=Path(tempfile.mkdtemp(prefix="fictional-event-text-",dir=parent)).resolve()
assert work.parent==parent
runtime_names=("event_timeline.py","restricted_xml.py","inspection_support.py","examples/generate.py")
def digest(raw):return hashlib.sha256(raw).hexdigest()
runtime={name:digest((module/name).read_bytes()) for name in runtime_names}
outcomes=[]
def command(case,script,args,expected_exit,expected_stdout):
    before={p.relative_to(work).as_posix():digest(p.read_bytes()) for p in work.rglob("*") if p.is_file()}
    result=subprocess.run([sys.executable,"-E","-s","-B",str(module/script),*map(str,args)],cwd=work,capture_output=True,timeout=60)
    assert result.returncode==expected_exit and result.stderr==b"",(case,result.stdout,result.stderr)
    assert json.loads(result.stdout)==expected_stdout,(case,result.stdout)
    assert result.stdout==(json.dumps(expected_stdout,sort_keys=True)+os.linesep).encode(),case
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    assert before=={name:digest((work/name).read_bytes()) for name in before},case
    outcomes.append(dict(case=case,exit_code=result.returncode))
command("create-fictional-saved-events","examples/generate.py",["--output",work/"fixtures"],0,
        dict(status="FICTIONAL_EXAMPLES_CREATED",files=4))
fixtures=work/"fixtures"
assert {p.name for p in fixtures.iterdir()}=={"clean.json","review.json","clean.xml","review.xml"}
crafted=work/"crafted";crafted.mkdir()
def event(**changes):
    return dict(provider="Example.Demo",event_id=100,time_created="2026-01-01T00:00:00Z",
                computer="FictionalComputer",channel="Example/Diagnostic",record_id=1,**changes)
def changed_event(**changes):
    value=event();value.update(changes);return value
json_events={
    "offsets.json":[changed_event(time_created="2026-01-01T01:00:00.1234568+01:00"),
                    changed_event(record_id=2,time_created="2026-01-01T00:00:00.1234567Z")],
    "ties.json":[changed_event(event_id=102,record_id=2),changed_event(event_id=101,record_id=3)],
    "gap-equal.json":[event(),changed_event(record_id=2,time_created="2026-01-01T00:05:00Z")],
    "gap-over.json":[event(),changed_event(record_id=2,time_created="2026-01-01T00:05:00.0000001Z")],
    "identity.json":[event(),event(),changed_event(event_id=101)],
    "cross-a.json":[event()],"cross-b.json":[event()],
    "scope.json":[event(),changed_event(computer="OtherFictionalComputer"),changed_event(channel="Other/Channel")],
    "missing-identity.json":[changed_event(computer=None),changed_event(computer=None)],
    "groups.json":[changed_event(record_id=i+1,**fields) for i,fields in enumerate(({},dict(version=0),dict(version=1),dict(qualifiers=0),
        dict(provider_guid="{A0000000-0000-4000-8000-000000000001}"),dict(provider_guid="a0000000-0000-4000-8000-000000000001")))],
    "bad-times.json":[changed_event(time_created=value) for value in ("2026-01-01T00:00:00","2026-01-01T00:00:00-00:00",
        "2026-01-01T00:00:00+14:01","2026-02-30T00:00:00Z","2026-01-01T00:00:60Z","2026-01-01T00:00:00.12345678Z")],
    "unknown.json":[changed_event(provider="<script>fictional</script>",message="fictional_payload_marker",security="fictional_security_marker")],
    "wide.json":[changed_event(time_created="1970-01-01T00:00:00Z",record_id=18446744073709551615),
                 changed_event(record_id=2,time_created="2000-01-01T00:00:00Z")],
    "long-line.json":[dict(provider="Example.Demo",event_id=100,time_created="2026-01-01T00:00:00Z") for _ in range(120)],
}
for name,events in json_events.items():
    (crafted/name).write_bytes((json.dumps(dict(schema_version=1,events=events),separators=(',',':'))+'\n').encode())
namespace="http://schemas.microsoft.com/win/2004/08/events/event"
system='<Provider Name="Example.Demo"/><EventID>100</EventID><TimeCreated SystemTime="2026-01-01T00:00:00Z"/>'
single='<Event xmlns="'+namespace+'"><System>'+system+'</System><EventData><Data>fictional_payload_marker&#13;</Data></EventData><UserData>fictional_security_marker</UserData></Event>\n'
values={
    "empty.json":b'\xef\xbb\xbf{"schema_version":1,"events":[]}',
    "duplicate-key.json":b'{"schema_version":1,"events":[],"events":[]}',
    "float.json":b'{"schema_version":1,"events":[1.5]}',
    "nan.json":b'{"schema_version":1,"events":[NaN]}',
    "schema.json":b'{"schema_version":true,"events":[]}',
    "string.json":json.dumps(dict(schema_version=1,events=[dict(provider='X'*8193,event_id=100,time_created='2026-01-01T00:00:00Z')])).encode(),
    "depth.json":('['*10+'0'+']'*10).encode(),
    "events.json":json.dumps(dict(schema_version=1,events=[{}]*4001)).encode(),
    "single.xml":single.encode(),
    "reset.xml":single.replace('<Provider ','<Provider xmlns="" ').encode(),
    "unknown-root.xml":single.replace(namespace,'urn:fictional').encode(),
    "control-identity.xml":single.replace('Example.Demo','Example&#13;Demo').encode(),
    "unknown.xml":('<?fiction note?>'+single.replace('</System>','<Unknown/></System>')).encode(),
    "dtd.xml":('<!DOCTYPE Event SYSTEM "file:///fictional/not-opened.dtd">'+single).encode(),
    "cdata.xml":single.replace('</Event>','<![CDATA[fiction]]></Event>').encode(),
    "unbalanced.xml":b'<Events>',
    "xml-depth.xml":('<a>'*33+'</a>'*33).encode(),
    "attributes.xml":('<Event '+' '.join(f'a{i}="x"' for i in range(17))+'/>').encode(),
    "reference.xml":b'<Event>&unknown;</Event>',
    "invalid.xml":b'\xff',
    "line.xml":b'X'*8193,
    "bytes.json":b'#'*(1024*1024+1),
}
for name,raw in values.items():(crafted/name).write_bytes(raw)
inputs={p.relative_to(work).as_posix():digest(p.read_bytes()) for folder in (fixtures,crafted) for p in folder.iterdir()}
assert len(inputs)==40
reports=[];input_hashes_checked=0;mode_counts={"default":0,"included":0}
def eid(index):return f"event-{index:04d}"
def gid(index):return f"group-{index:04d}"
def finding(code,index,source="input-0001"):return dict(code=code,source=source,record_index=index)
def row(index,group,event_id=100,*,position=None,source="input-0001",elapsed="0",delta=None,level=None,utc="2026-01-01T00:00:00.0000000Z",record_id="1"):
    return dict(id=eid(index),source=source,record_index=position or index,group_id=gid(group),event_id=event_id,level=level,
                elapsed_100ns=elapsed,delta_100ns=delta,time_created_utc=utc,record_id=record_id)
def group(index,count,event_id=100,*,version=None,qualifiers=None,levels=(None,),provider="Example.Demo",guid=None,channel="Example/Diagnostic"):
    return dict(id=gid(index),event_id=event_id,version=version,qualifiers=qualifiers,count=count,levels=list(levels),
                provider=provider,provider_guid=guid,channel=channel)
def expected_report(files,kind,*,timeline=(),groups=(),gaps=(),findings=(),coverage=(),chronological=True,threshold=300,details=False):
    # Order, elapsed/delta ticks, groups and all finding/coverage expectations are
    # supplied explicitly. This helper does not normalize records or timestamps.
    result=dict(schema_version=1,tool="Windows Event Timeline Inspector",input_format=kind,details_included=details,
        scope="Selected saved metadata only; declared clock times, source completeness and causation are unverified.",
        gap_threshold_seconds=threshold,inputs=[dict(id=f"input-{i:04d}",bytes=len(p.read_bytes()),sha256=digest(p.read_bytes())) for i,p in enumerate(files,1)],
        timeline=copy.deepcopy(list(timeline)),groups=copy.deepcopy(list(groups)),gaps=list(gaps),findings=list(findings),coverage_issues=list(coverage),
        computer_and_payload_fields_omitted=True,input_order_was_chronological=chronological,
        repeated_groups=sum(g["count"]>1 for g in groups),
        duplicate_scope="Within an individual selected source plus declared computer/channel/record ID only; unavailable identities and cross-file deduplication are not inferred.",
        status="REVIEW_REQUIRED" if findings or coverage else "NO_SCOPE_FINDINGS")
    if not details:
        for item in result["timeline"]:
            item.pop("time_created_utc");item.pop("record_id")
        for item in result["groups"]:
            for key in ("provider","provider_guid","channel"):item.pop(key)
    return result
def inspect_case(case,files,kind="json",*,details=False,**expectations):
    global input_hashes_checked
    output=work/(case+"-report");expected=expected_report(files,kind,details=details,**expectations);args=[]
    for path in files:args += ["--file",path]
    args += ["--format",kind,"--output",output]
    if "threshold" in expectations:args += ["--gap-seconds",expectations["threshold"]]
    if details:args += ["--include-details"]
    status=expected["status"]
    command(case,"event_timeline.py",args,int(status!="NO_SCOPE_FINDINGS"),dict(status=status,events=len(expected["timeline"]),groups=len(expected["groups"]),gaps=len(expected["gaps"]),coverage_issues=len(expected["coverage_issues"])))
    assert {p.name for p in output.iterdir()}=={"report.json","report.html","MANIFEST.json"}
    raw=(output/"report.json").read_bytes();page=(output/"report.html").read_bytes()
    assert json.loads(raw)==expected,case
    assert raw==(json.dumps(expected,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode(),case
    assert b'<script' not in page and b'http://' not in page and b'https://' not in page
    assert b'<pre>'+html.escape(raw.decode(),quote=True).encode()+b'</pre>' in page
    assert json.loads((output/"MANIFEST.json").read_bytes())==dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=digest(data)) for name,data in sorted({"report.json":raw,"report.html":page}.items())])
    assert not any(marker in raw for marker in (b'FictionalComputer',b'fictional_payload_marker',b'fictional_security_marker',b'"computer"'))
    if not details:assert not any(marker in raw for marker in (b'Example.Demo',b'Example/Diagnostic',b'2026-01-01',b'"record_id"',b'"time_created_utc"'))
    assert str(work).encode() not in raw and str(module).encode() not in raw
    reports.append(output);input_hashes_checked+=len(files);mode_counts["included" if details else "default"]+=1;return expected

clean=dict(timeline=(row(1,1,level=4,utc="2026-01-01T00:00:00.0000001Z"),
    row(2,1,level=4,elapsed="300000000",delta="300000000",utc="2026-01-01T00:00:30.0000001Z",record_id="2"),
    row(3,2,101,level=4,elapsed="600000000",delta="300000000",utc="2026-01-01T00:01:00.0000001Z",record_id="3")),
    groups=(group(1,2,version=0,levels=(4,)),group(2,1,101,version=0,levels=(4,))))
json_default=inspect_case("clean-json-default",[fixtures/"clean.json"],**clean)
json_details=inspect_case("clean-json-details",[fixtures/"clean.json"],details=True,**clean)
xml_default=inspect_case("same-events-xml-default",[fixtures/"clean.xml"],"xml",**clean)
xml_details=inspect_case("same-events-xml-details",[fixtures/"clean.xml"],"xml",details=True,**clean)
assert json_details["timeline"]==xml_details["timeline"] and json_details["groups"]==xml_details["groups"]
assert json_default["timeline"]==xml_default["timeline"] and json_default["groups"]==xml_default["groups"]
review=dict(timeline=(clean["timeline"][0],row(4,1,position=4,level=4,delta="0",utc="2026-01-01T00:00:00.0000001Z"),*clean["timeline"][1:],
    row(5,1,level=4,elapsed="8999999999",delta="8399999999",utc="2026-01-01T00:15:00.0000000Z",record_id="4")),
    groups=(group(1,4,version=0,levels=(4,)),group(2,1,101,version=0,levels=(4,))),
    gaps=(dict(before_id=eid(3),after_id=eid(5),duration_100ns="8399999999"),),
    findings=(finding("DUPLICATE_EXPORTED_RECORD",4),finding("DECLARED_TIME_GAP_EXCEEDS_THRESHOLD",5)),
    coverage=(finding("UNSUPPORTED_EVENT_TIMESTAMP",6),),chronological=False)
review_default=inspect_case("json-duplicate-gap-naive-time-default",[fixtures/"review.json"],**review)
review_details=inspect_case("json-duplicate-gap-naive-time-details",[fixtures/"review.json"],details=True,**review)
inspect_case("xml-record-conflict-and-gap",[fixtures/"review.xml"],"xml",details=True,
    timeline=(clean["timeline"][0],row(2,1,level=4,elapsed="6009999999",delta="6009999999",utc="2026-01-01T00:10:01.0000000Z")),
    groups=(group(1,2,version=0,levels=(4,)),),gaps=(dict(before_id=eid(1),after_id=eid(2),duration_100ns="6009999999"),),
    findings=(finding("CONFLICTING_EXPORTED_RECORD_ID",2),finding("DECLARED_TIME_GAP_EXCEEDS_THRESHOLD",2)))
inspect_case("offsets-reverse-input-exact-one-tick",[crafted/"offsets.json"],details=True,chronological=False,
    timeline=(row(2,1,position=2,utc="2026-01-01T00:00:00.1234567Z",record_id="2"),
              row(1,1,position=1,elapsed="1",delta="1",utc="2026-01-01T00:00:00.1234568Z")),groups=(group(1,2),))
inspect_case("equal-timestamps-retain-input-order",[crafted/"ties.json"],timeline=(row(1,1,102,record_id="2"),row(2,2,101,delta="0",record_id="3")),
    groups=(group(1,1,102),group(2,1,101)))
gap_equal=dict(timeline=(row(1,1),row(2,1,elapsed="3000000000",delta="3000000000",utc="2026-01-01T00:05:00.0000000Z",record_id="2")),groups=(group(1,2),))
inspect_case("gap-equal-threshold-is-not-finding",[crafted/"gap-equal.json"],**gap_equal)
gap_over=dict(timeline=(row(1,1),row(2,1,elapsed="3000000001",delta="3000000001",utc="2026-01-01T00:05:00.0000001Z",record_id="2")),groups=(group(1,2),))
inspect_case("gap-one-tick-over-threshold-review",[crafted/"gap-over.json"],**gap_over,
    gaps=(dict(before_id=eid(1),after_id=eid(2),duration_100ns="3000000001"),),findings=(finding("DECLARED_TIME_GAP_EXCEEDS_THRESHOLD",2),))
inspect_case("zero-gap-threshold-disables-gap-findings",[crafted/"gap-over.json"],threshold=0,**gap_over)
inspect_case("same-file-duplicate-and-conflicting-record-ids",[crafted/"identity.json"],
    timeline=(row(1,1),row(2,1,delta="0"),row(3,2,101,delta="0")),groups=(group(1,2),group(2,1,101)),
    findings=(finding("DUPLICATE_EXPORTED_RECORD",2),finding("CONFLICTING_EXPORTED_RECORD_ID",3)))
inspect_case("identical-cross-file-events-not-deduplicated",[crafted/"cross-a.json",crafted/"cross-b.json"],
    timeline=(row(1,1),row(2,1,position=1,source="input-0002",delta="0")),groups=(group(1,2),))
inspect_case("different-computers-and-channels-keep-identity-scope",[crafted/"scope.json"],
    timeline=(row(1,1),row(2,1,delta="0"),row(3,2,delta="0")),groups=(group(1,2),group(2,1,channel="Other/Channel")))
inspect_case("missing-computer-does-not-infer-duplicate",[crafted/"missing-identity.json"],
    timeline=(row(1,1),row(2,1,delta="0")),groups=(group(1,2),))
inspect_case("optional-group-keys-and-normalized-guid",[crafted/"groups.json"],
    timeline=tuple(row(i,g,delta=None if i==1 else "0",record_id=str(i)) for i,g in enumerate((1,2,3,4,5,5),1)),
    groups=(group(1,1),group(2,1,version=0),group(3,1,version=1),group(4,1,qualifiers=0),group(5,2,guid="a0000000-0000-4000-8000-000000000001")))
inspect_case("unsupported-times-remain-visible-coverage",[crafted/"bad-times.json"],
    coverage=tuple(finding("UNSUPPORTED_EVENT_TIMESTAMP",i) for i in range(1,7)))
inspect_case("unknown-payload-fields-omitted-details-html-escaped",[crafted/"unknown.json"],details=True,
    timeline=(row(1,1),),groups=(group(1,1,provider="<script>fictional</script>"),),coverage=(finding("UNINSPECTED_EVENT_FIELDS",1),))
assert b'&lt;script&gt;' in (reports[-1]/"report.html").read_bytes()
inspect_case("bom-empty-json-export-limited-scope",[crafted/"empty.json"])
inspect_case("single-event-xml-payload-control-is-omitted",[crafted/"single.xml"],"xml",
    timeline=(row(1,1,record_id=None),),groups=(group(1,1,channel=None),))
inspect_case("namespace-reset-not-guessed",[crafted/"reset.xml"],"xml",coverage=(finding("UNSUPPORTED_EVENT_XML_RECORD",1),))
inspect_case("unknown-xml-namespace-is-coverage",[crafted/"unknown-root.xml"],"xml",coverage=(finding("UNSUPPORTED_EVENT_XML_ROOT",0),))
inspect_case("encoded-cr-identity-rejected-without-leak",[crafted/"control-identity.xml"],"xml",coverage=(finding("UNSUPPORTED_EVENT_RECORD",1),))
inspect_case("processing-instruction-and-unknown-system-field",[crafted/"unknown.xml"],"xml",
    timeline=(row(1,1,record_id=None),),groups=(group(1,1,channel=None),),
    coverage=(finding("XML_PROCESSING_INSTRUCTION_UNINSPECTED",0),finding("UNINSPECTED_SYSTEM_FIELD",1)))
assert max(map(len,(crafted/"long-line.json").read_bytes().splitlines()))>8192
inspect_case("json-does-not-inherit-xml-physical-line-bound",[crafted/"long-line.json"],
    timeline=tuple(row(i,1,delta=None if i==1 else "0",record_id=None) for i in range(1,121)),groups=(group(1,120,channel=None),))
inspect_case("wide-interval-and-max-record-id-are-decimal-strings",[crafted/"wide.json"],details=True,threshold=0,
    timeline=(row(1,1,utc="1970-01-01T00:00:00.0000000Z",record_id="18446744073709551615"),
              row(2,1,elapsed="9466848000000000",delta="9466848000000000",utc="2000-01-01T00:00:00.0000000Z",record_id="2")),groups=(group(1,2),))
def without_details(value):
    value=copy.deepcopy(value);value["details_included"]=False
    for item in value["timeline"]:item.pop("time_created_utc",None);item.pop("record_id",None)
    for item in value["groups"]:
        for key in ("provider","provider_guid","channel"):item.pop(key,None)
    return value
for default,details in ((json_default,json_details),(xml_default,xml_details),(review_default,review_details)):
    assert default==without_details(details)
def refuse(case,files,kind,code,*,output=None,extra=()):
    output=output or work/(case+"-report");existed=output.exists();args=[]
    for path in files:args += ["--file",path]
    if kind is not None:args += ["--format",kind]
    args += ["--output",output,*extra]
    command(case,"event_timeline.py",args,2,dict(status="INCOMPLETE",error=code));assert output.exists()==existed,case
refuse("refuse-json-duplicate-key",[crafted/"duplicate-key.json"],"json","DUPLICATE_JSON_KEY")
refuse("refuse-json-float",[crafted/"float.json"],"json","JSON_NUMBER_UNSUPPORTED")
refuse("refuse-json-nan",[crafted/"nan.json"],"json","JSON_NUMBER_UNSUPPORTED")
refuse("refuse-json-invalid-root-schema",[crafted/"schema.json"],"json","INVALID_EVENT_EXPORT_SCHEMA")
refuse("refuse-json-string-bound",[crafted/"string.json"],"json","JSON_TEXT_UNSUPPORTED")
refuse("refuse-json-depth-bound",[crafted/"depth.json"],"json","JSON_STRUCTURE_LIMIT")
refuse("refuse-event-count-bound",[crafted/"events.json"],"json","EVENT_COUNT_LIMIT")
refuse("refuse-dtd-without-resource-resolution",[crafted/"dtd.xml"],"xml","XML_DECLARATIONS_REJECTED")
refuse("refuse-cdata",[crafted/"cdata.xml"],"xml","XML_MARKUP_UNSUPPORTED")
refuse("refuse-unbalanced-xml",[crafted/"unbalanced.xml"],"xml","INVALID_XML")
refuse("refuse-xml-depth-bound",[crafted/"xml-depth.xml"],"xml","XML_STRUCTURE_LIMIT")
refuse("refuse-xml-attribute-count",[crafted/"attributes.xml"],"xml","XML_ATTRIBUTE_LIMIT")
refuse("refuse-unknown-xml-reference",[crafted/"reference.xml"],"xml","INVALID_XML_REFERENCE")
refuse("refuse-non-utf8-xml",[crafted/"invalid.xml"],"xml","UTF8_REQUIRED")
refuse("refuse-xml-physical-line-bound",[crafted/"line.xml"],"xml","TEXT_LINE_LIMIT")
refuse("refuse-input-byte-bound",[crafted/"bytes.json"],"json","INPUT_BYTE_LIMIT")
refuse("refuse-duplicate-selected-file",[fixtures/"clean.json",fixtures/"clean.json"],"json","DUPLICATE_INPUT_FILE")
refuse("refuse-existing-report",[fixtures/"clean.json"],"json","OUTPUT_EXISTS",output=reports[0])
command("refuse-existing-generator-directory","examples/generate.py",["--output",fixtures],2,dict(status="INCOMPLETE",error="OUTPUT_EXISTS"))
refuse("refuse-required-format-missing",[fixtures/"clean.json"],None,"ARGUMENTS_INVALID")
refuse("refuse-invalid-gap-threshold",[fixtures/"clean.json"],"json","GAP_THRESHOLD_INVALID",extra=("--gap-seconds","-1"))
refuse("refuse-relative-input",["fixtures/clean.json"],"json","LOCAL_ABSOLUTE_PATH_REQUIRED")
refuse("refuse-selected-file-count",[fixtures/"clean.json"]*33,"json","INPUT_COUNT_LIMIT")
assert inputs=={name:digest((work/name).read_bytes()) for name in inputs}
assert runtime=={name:digest((module/name).read_bytes()) for name in runtime_names}
assert not list(work.rglob("*.pyc")) and not list(module.rglob("*.pyc"))
expected_files=set(inputs)
for output in reports:expected_files.update((output/name).relative_to(work).as_posix() for name in ("report.json","report.html","MANIFEST.json"))
assert {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()}==expected_files
print(json.dumps(dict(outcomes=outcomes,reports_verified=len(reports),payload_hashes_verified=2*len(reports),
    input_hashes_checked=input_hashes_checked,fixture_files_preserved=len(inputs),expected_workspace_files=len(expected_files),
    unexpected_application_files=0,details_mode_counts=mode_counts,details_do_not_change_observations=True,
    json_xml_observations_equivalent=True,bytecode_files=0,runtime_bytes_preserved=True,
    live_event_logs_queried=False,native_event_binaries_decoded=False,native_xml_parser_used=False,external_resources_opened=False,
    computer_names_serialized=False,raw_event_payloads_serialized=False,real_event_logs_used=False,causal_diagnosis_verified=False),sort_keys=True))
```

## Exact expected case outcomes

```json
[
  {
    "case": "create-fictional-saved-events",
    "exit_code": 0
  },
  {
    "case": "clean-json-default",
    "exit_code": 0
  },
  {
    "case": "clean-json-details",
    "exit_code": 0
  },
  {
    "case": "same-events-xml-default",
    "exit_code": 0
  },
  {
    "case": "same-events-xml-details",
    "exit_code": 0
  },
  {
    "case": "json-duplicate-gap-naive-time-default",
    "exit_code": 1
  },
  {
    "case": "json-duplicate-gap-naive-time-details",
    "exit_code": 1
  },
  {
    "case": "xml-record-conflict-and-gap",
    "exit_code": 1
  },
  {
    "case": "offsets-reverse-input-exact-one-tick",
    "exit_code": 0
  },
  {
    "case": "equal-timestamps-retain-input-order",
    "exit_code": 0
  },
  {
    "case": "gap-equal-threshold-is-not-finding",
    "exit_code": 0
  },
  {
    "case": "gap-one-tick-over-threshold-review",
    "exit_code": 1
  },
  {
    "case": "zero-gap-threshold-disables-gap-findings",
    "exit_code": 0
  },
  {
    "case": "same-file-duplicate-and-conflicting-record-ids",
    "exit_code": 1
  },
  {
    "case": "identical-cross-file-events-not-deduplicated",
    "exit_code": 0
  },
  {
    "case": "different-computers-and-channels-keep-identity-scope",
    "exit_code": 0
  },
  {
    "case": "missing-computer-does-not-infer-duplicate",
    "exit_code": 0
  },
  {
    "case": "optional-group-keys-and-normalized-guid",
    "exit_code": 0
  },
  {
    "case": "unsupported-times-remain-visible-coverage",
    "exit_code": 1
  },
  {
    "case": "unknown-payload-fields-omitted-details-html-escaped",
    "exit_code": 1
  },
  {
    "case": "bom-empty-json-export-limited-scope",
    "exit_code": 0
  },
  {
    "case": "single-event-xml-payload-control-is-omitted",
    "exit_code": 0
  },
  {
    "case": "namespace-reset-not-guessed",
    "exit_code": 1
  },
  {
    "case": "unknown-xml-namespace-is-coverage",
    "exit_code": 1
  },
  {
    "case": "encoded-cr-identity-rejected-without-leak",
    "exit_code": 1
  },
  {
    "case": "processing-instruction-and-unknown-system-field",
    "exit_code": 1
  },
  {
    "case": "json-does-not-inherit-xml-physical-line-bound",
    "exit_code": 0
  },
  {
    "case": "wide-interval-and-max-record-id-are-decimal-strings",
    "exit_code": 0
  },
  {
    "case": "refuse-json-duplicate-key",
    "exit_code": 2
  },
  {
    "case": "refuse-json-float",
    "exit_code": 2
  },
  {
    "case": "refuse-json-nan",
    "exit_code": 2
  },
  {
    "case": "refuse-json-invalid-root-schema",
    "exit_code": 2
  },
  {
    "case": "refuse-json-string-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-json-depth-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-event-count-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-dtd-without-resource-resolution",
    "exit_code": 2
  },
  {
    "case": "refuse-cdata",
    "exit_code": 2
  },
  {
    "case": "refuse-unbalanced-xml",
    "exit_code": 2
  },
  {
    "case": "refuse-xml-depth-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-xml-attribute-count",
    "exit_code": 2
  },
  {
    "case": "refuse-unknown-xml-reference",
    "exit_code": 2
  },
  {
    "case": "refuse-non-utf8-xml",
    "exit_code": 2
  },
  {
    "case": "refuse-xml-physical-line-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-input-byte-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-duplicate-selected-file",
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
    "case": "refuse-required-format-missing",
    "exit_code": 2
  },
  {
    "case": "refuse-invalid-gap-threshold",
    "exit_code": 2
  },
  {
    "case": "refuse-relative-input",
    "exit_code": 2
  },
  {
    "case": "refuse-selected-file-count",
    "exit_code": 2
  }
]
```

The summary records 51 cases: seventeen exit 0, eleven review exit 1 and
twenty-three incomplete exit 2 results. Twenty-seven report manifests cover
54 report payloads; 28 selected input hash observations, forty preserved
fictional inputs and 121 exact input/report files are checked. Twenty reports
use defaults and seven request details. Three privacy pairs preserve supported
observations; JSON/XML timeline/group equivalence is checked in both modes.

All eight scope fields stay false: live-log queries, native event-binary decoding,
native XML use, external resource access, serialized computer names/raw payloads,
real logs and causal diagnosis. Read [FORMAT.md](docs/FORMAT.md) and
[QUALIFICATION.md](docs/QUALIFICATION.md). Empty supported scope or a clean
timeline does not establish capture completeness, real host identity or failure
cause. Actual captures and identifying reports remain private.
