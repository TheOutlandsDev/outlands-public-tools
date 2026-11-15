# EML/MIME Inspector 0.1.0 — executable fictional walkthrough

This guide uses invented EML bytes and reserved example.invalid addresses only.
It verifies complete MIME summaries from independent known-source/decoded-byte
expectations, without importing the inspector or standard-library email parser
as an oracle. No mailbox, provider, real message, send, renderer, attachment
extractor, authenticity check or malware-safety judgment is used.

## Prepare a new private run

Verify release checksums and select Python 3.12–3.15. Formal guide proof uses
fresh no-pip Python 3.15.2 and five copied runtime files. No package, admin, login,
GUI or network service is required. Keep all generated fixtures/reports outside
source in a new owned workspace under an existing ordinary private parent.

Save the single Python block below as `fictional_eml_walkthrough.py` outside source.
Copy only `inspect_eml.py`, `fictional_eml.py`, `message_core.py`, `toolkit.py` and
`native_windows.py` into a separate module directory. The driver checks that exact
inventory. Run assertion-enabled Python, never `-O`. Replace these invented paths:

```powershell
$module = (Resolve-Path .).Path
$privateWork = 'D:\Private-Review'
python -I -B fictional_eml_walkthrough.py "$module" "$privateWork"
```

```sh
module="$PWD"
privateWork='/owned/private-review'
python3 -I -B fictional_eml_walkthrough.py "$module" "$privateWork"
```

Point `$module` at the five-file copied runtime. The parent must exist outside
both source and the copy, and must not be a symlink/junction. Each run creates a
unique child and retains its fictional inputs/reports, including a 2 MiB+1 byte
refusal fixture. Children run `-E -s -B`; the driver runs isolated `-I -B`.

## Read the expectations first

The actual generator must reproduce exact independently authored CRLF sample
bytes. The sample's multipart/plain/binary decoded hashes, source hash and ordered
part graph must match. New compact report files must equal independently encoded
full summaries. Repeated stdout inspection is deterministic. Accepted examples
cover 7bit plain text, base64 UTF-8, inert HTML containing a reserved remote URL,
nested mixed/alternative DFS order, a text attachment, optional/encoded/folded
headers, case normalization, an empty text body and CRLF-only base64 wrapping.

Two invented subjects with identical bodies retain the same body fingerprints
but different source fingerprints. Every report omits raw header/body/name values;
this demonstrates field minimization, not anonymity. HTML/script/link-looking
bytes are hashed as data, never rendered/followed. A child audit refuses selected
network/browser/process events for the CLI fixture; this is not an OS sandbox.

Refusals cover narrow ordinary-mail/header/address grammar, duplicate recipients/
attachments, unsupported media/encoding/parameters, noncanonical base64, decoded
controls/UTF-8, source/line/header/subject/recipient/depth/child/part bounds and
nonempty multipart surroundings. Refused `--out` paths must remain nonexistent.
The native checks reject a hardlinked input, existing report/input-output alias,
source output and parent traversal. Expected native codes are explicit per OS.

A separate child-only `os.write` fault demonstrates retained unconfirmed output:
five authored bytes are written, then a synthetic OSError occurs. The exact prefix
must remain and a later CLI write to that path must be refused. This is an injected
I/O fixture, not a hardware/power-loss test or permission to delete/retry outputs.

```python
"""Inspect invented EML buffers/files only; no real mail, delivery or extraction."""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

if not __debug__:raise RuntimeError('ASSERTIONS_REQUIRED')
module=Path(sys.argv[1]).resolve(strict=True);parent=Path(sys.argv[2]).resolve(strict=True)
assert parent.is_dir() and not parent.is_relative_to(module) and not module.is_relative_to(parent)
assert not parent.is_symlink() and not getattr(parent,'is_junction',lambda:False)()
work=Path(tempfile.mkdtemp(prefix='fictional-eml-inspection-',dir=parent)).resolve();assert work.parent==parent
runtimes=('inspect_eml.py','fictional_eml.py','message_core.py','toolkit.py','native_windows.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
runtime_hashes={name:sha((module/name).read_bytes()) for name in runtimes}
inputs=work/'inputs';reports=work/'reports';inputs.mkdir();reports.mkdir()

def plain(body=b'Fictional plain body.\r\n',kind=b'text/plain; charset=utf-8',extra=b'',subject=b'Fictional review'):
    return b'From: robot@example.invalid\r\nTo: reviewer@example.invalid\r\nSubject: '+subject+b'\r\nMIME-Version: 1.0\r\nContent-Type: '+kind+b'\r\n'+extra+b'\r\n'+body
def leaf(kind,payload,*,name=None):
    headers=b'Content-Type: '+kind+b'\r\n'
    if name is not None:headers+=b'Content-Disposition: attachment; filename="'+name+b'"\r\n'
    headers+=b'Content-Transfer-Encoding: base64\r\n'
    return headers+b'\r\n'+base64.b64encode(payload)+b'\r\n'
def multipart(boundary,children,*,kind=b'mixed'):
    return b'Content-Type: multipart/'+kind+b'; boundary="'+boundary+b'"\r\n\r\n'+b''.join(b'--'+boundary+b'\r\n'+child for child in children)+b'--'+boundary+b'--\r\n'
root_headers=b'From: robot@example.invalid\r\nTo: reviewer@example.invalid\r\nSubject: Fictional sample\r\nMIME-Version: 1.0\r\n'
sample=root_headers+multipart(b'fictional_boundary',[leaf(b'text/plain; charset=utf-8',b'Invented notice.\n'),leaf(b'application/octet-stream',b'sample\n',name=b'sample.txt')])
def part(number,depth,kind,payload,attachment=False):
    return dict(part=number,depth=depth,media_type=kind,attachment=attachment,bytes=len(payload),sha256=sha(payload))
def summary(raw,rows):
    return dict(status='PASS',format='outlands-mime-summary-v1',input_sha256=sha(raw),parts=rows,
        decoded_bytes=sum(row.get('bytes',0) for row in rows),attachment_count=sum(row.get('attachment',False) for row in rows),
        bodies_rendered=False,files_extracted=False,real_delivery_verified=False)
sample_rows=[dict(part=1,depth=0,media_type='multipart/mixed',children=2),
             part(2,1,'text/plain',b'Invented notice.\n'),part(3,1,'application/octet-stream',b'sample\n',True)]
utf8='Fictional café.\n'.encode('utf-8');html=b'<p>Fictional HTML.</p><img src="https://example.invalid/pixel"><script>fictional()</script>'
plain_raw=plain();utf8_raw=plain(base64.b64encode(utf8)+b'\r\n',extra=b'Content-Transfer-Encoding: base64\r\n')
html_raw=plain(html,kind=b'text/html; charset=us-ascii')
nested=root_headers+multipart(b'outer',[multipart(b'inner',[leaf(b'text/plain; charset=utf-8',b'Fictional alternative.\n'),leaf(b'text/html; charset=utf-8',b'<p>Fictional alternative.</p>')],kind=b'alternative'),leaf(b'application/octet-stream',b'\x00\x01\xff',name=b'fictional.bin')])
nested_rows=[dict(part=1,depth=0,media_type='multipart/mixed',children=2),dict(part=2,depth=1,media_type='multipart/alternative',children=2),
    part(3,2,'text/plain',b'Fictional alternative.\n'),part(4,2,'text/html',b'<p>Fictional alternative.</p>'),part(5,1,'application/octet-stream',b'\x00\x01\xff',True)]
text_attachment=plain(base64.b64encode(b'Fictional attached text.\n')+b'\r\n',extra=b'Content-Transfer-Encoding: base64\r\nContent-Disposition: attachment; filename="notes.txt"\r\n')
opaque_headers=plain(extra=b'Date: Tue, 10 Nov 2026 10:00:00 +0000\r\nMessage-ID: <fictional@example.invalid>\r\nX-Reference: invented\r\n',subject=b'=?utf-8?b?RmljdGlvbmFs?=')
folded=plain(subject=b'Fictional\r\n\tcontinued review')
case_variant=plain_raw.replace(b'Content-Type: text/plain; charset=utf-8',b'cOnTeNt-TyPe: TEXT/PLAIN; charset=UTF-8')
changed_headers=plain(subject=b'Different fictional header; identical body')
accepted=[
 ('plain-7bit',plain_raw,[part(1,0,'text/plain',b'Fictional plain body.\r\n')]),
 ('utf8-base64',utf8_raw,[part(1,0,'text/plain',utf8)]),
 ('html-is-hashed-not-rendered',html_raw,[part(1,0,'text/html',html)]),
 ('nested-alternative-mixed-order',nested,nested_rows),
 ('text-attachment-omits-filename',text_attachment,[part(1,0,'text/plain',b'Fictional attached text.\n',True)]),
 ('opaque-optional-headers-and-encoded-subject',opaque_headers,[part(1,0,'text/plain',b'Fictional plain body.\r\n')]),
 ('folded-subject-omitted',folded,[part(1,0,'text/plain',b'Fictional plain body.\r\n')]),
 ('media-and-header-case-normalized',case_variant,[part(1,0,'text/plain',b'Fictional plain body.\r\n')]),
 ('changed-header-keeps-body-fingerprint',changed_headers,[part(1,0,'text/plain',b'Fictional plain body.\r\n')]),
 ('empty-text-is-zero-byte-payload',plain(b''),[part(1,0,'text/plain',b'')]),
 ('canonical-base64-wraps-only-crlf',plain(b'YWJj\r\nZGVm\r\n',extra=b'Content-Transfer-Encoding: base64\r\n'),[part(1,0,'text/plain',b'abcdef')])]
deep=leaf(b'text/plain; charset=utf-8',b'Fictional deep leaf')
for index in range(9):deep=multipart(('depth'+str(index)).encode(),[deep])
branches=[multipart(('branch'+str(index)).encode(),[leaf(b'text/plain; charset=utf-8',b'Fictional branch')]*10) for index in range(3)]
bad=[
 ('refuse-lf-only-source',sample.replace(b'\r\n',b'\n'),'EML_7BIT_CRLF_REQUIRED'),
 ('refuse-nul-source',plain(b'\x00'),'EML_7BIT_CRLF_REQUIRED'),
 ('refuse-raw-eight-bit-source',plain(b'\xff'),'EML_7BIT_CRLF_REQUIRED'),
 ('refuse-physical-line-bound',plain(b'X'*999),'EML_LINE_LIMIT'),
 ('refuse-root-header-byte-bound',plain(extra=b'X-Reference: '+b'A'*900+b'\r\n'+(b' '+b'A'*900+b'\r\n')*74),'HEADER_LIMIT'),
 ('refuse-missing-mime-version',plain_raw.replace(b'MIME-Version: 1.0\r\n',b''),'MESSAGE_HEADERS_REQUIRED'),
 ('refuse-missing-content-type',plain_raw.replace(b'Content-Type: text/plain; charset=utf-8\r\n',b''),'CONTENT_TYPE_REQUIRED'),
 ('refuse-ordinary-received-header',plain(extra=b'Received: fictional trace\r\n'),'HEADER_UNSUPPORTED_OR_DUPLICATE'),
 ('refuse-duplicate-root-subject',plain(extra=b'sUbJeCt: second\r\n'),'HEADER_UNSUPPORTED_OR_DUPLICATE'),
 ('refuse-duplicate-mime-header',plain(extra=b'Content-Type: text/plain; charset=utf-8\r\n'),'HEADER_UNSUPPORTED_OR_DUPLICATE'),
 ('refuse-nested-subject-header',sample.replace(b'Content-Type: application/octet-stream',b'Subject: child\r\nContent-Type: application/octet-stream'),'PART_HEADER_FORBIDDEN'),
 ('refuse-duplicate-recipient-across-fields',plain(extra=b'Bcc: reviewer@example.invalid\r\n'),'DUPLICATE_RECIPIENT'),
 ('refuse-display-name-address',plain_raw.replace(b'robot@example.invalid',b'Robot <robot@example.invalid>'),'ADDRESS_INVALID'),
 ('refuse-recipient-group-bound',plain_raw.replace(b'To: reviewer@example.invalid',b'To: '+b','.join(('r'+str(i)+'@example.invalid').encode() for i in range(33))),'RECIPIENT_LIMIT'),
 ('refuse-subject-character-bound',plain(subject=b'S'*161),'TEXT_INVALID'),
 ('refuse-unfolded-header-bound',plain(extra=b'X-Reference: '+b'A'*900+b'\r\n'+(b' '+b'A'*900+b'\r\n')*9),'HEADER_INVALID'),
 ('refuse-unsupported-image-media',plain(kind=b'image/png'),'CONTENT_TYPE_UNSUPPORTED'),
 ('refuse-quoted-charset',plain(kind=b'text/plain; charset="utf-8"'),'CONTENT_TYPE_UNSUPPORTED'),
 ('refuse-missing-charset',plain(kind=b'text/plain'),'CHARSET_REQUIRED'),
 ('refuse-quoted-printable',plain(extra=b'Content-Transfer-Encoding: quoted-printable\r\n'),'TRANSFER_ENCODING_UNSUPPORTED'),
 ('refuse-noncanonical-base64',plain(b'YR==',extra=b'Content-Transfer-Encoding: base64\r\n'),'BASE64_NONCANONICAL'),
 ('refuse-base64-extra-whitespace',plain(b' YQ==',extra=b'Content-Transfer-Encoding: base64\r\n'),'MIME_INVALID'),
 ('refuse-invalid-decoded-utf8',plain(b'/w==',extra=b'Content-Transfer-Encoding: base64\r\n'),'MIME_INVALID'),
 ('refuse-decoded-control',plain(base64.b64encode(b'Fictional\x00text'),extra=b'Content-Transfer-Encoding: base64\r\n'),'TEXT_CONTROL_FORBIDDEN'),
 ('refuse-binary-without-attachment',sample.replace(b'Content-Disposition: attachment; filename="sample.txt"\r\n',b''),'ATTACHMENT_DISPOSITION_REQUIRED'),
 ('refuse-binary-without-base64',sample.replace(b'Content-Transfer-Encoding: base64',b'Content-Transfer-Encoding: 7bit'),'BINARY_BASE64_REQUIRED'),
 ('refuse-attachment-path-name',sample.replace(b'filename="sample.txt"',b'filename="../sample.txt"'),'DISPOSITION_UNSUPPORTED'),
 ('refuse-reserved-attachment-name',sample.replace(b'filename="sample.txt"',b'filename="CON.txt"'),'FILENAME_INVALID'),
 ('refuse-casefold-duplicate-attachment',root_headers+multipart(b'fictional_boundary',[leaf(b'application/octet-stream',b'A',name=b'sample.txt'),leaf(b'application/octet-stream',b'B',name=b'SAMPLE.TXT')]),'DUPLICATE_ATTACHMENT'),
 ('refuse-nonempty-preamble',sample.replace(b'\r\n\r\n--fictional_boundary',b'\r\n\r\nFictional preamble\r\n--fictional_boundary',1),'MIME_EXTRA_CONTENT'),
 ('refuse-nonempty-epilogue',sample+b'Fictional epilogue\r\n','MIME_EXTRA_CONTENT'),
 ('refuse-child-count-bound',root_headers+multipart(b'many',[leaf(b'text/plain; charset=utf-8',b'Fictional child')]*17),'MIME_STRUCTURE_LIMIT'),
 ('refuse-depth-bound',root_headers+deep,'MIME_STRUCTURE_LIMIT'),
 ('refuse-total-parts-across-branches',root_headers+multipart(b'total',branches),'MIME_STRUCTURE_LIMIT')]
for name,raw,rows in accepted:(inputs/(name+'.eml')).write_bytes(raw)
for name,raw,error in bad:(inputs/(name+'.eml')).write_bytes(raw)
(inputs/'over-input-bound.eml').write_bytes(b'X'*(2*1024*1024+1))
(inputs/'empty-source.eml').write_bytes(b'')
(inputs/'hard-original.eml').write_bytes(plain_raw);os.link(inputs/'hard-original.eml',inputs/'hard-alias.eml')
assert (inputs/'hard-original.eml').stat().st_nlink==2
def snapshot(root):
    result={}
    for path in root.rglob('*'):
        assert not path.is_symlink() and not getattr(path,'is_junction',lambda:False)()
        info=path.lstat()
        if stat.S_ISDIR(info.st_mode):result[path.relative_to(root).as_posix()]=dict(kind='directory')
        else:
            assert stat.S_ISREG(info.st_mode);raw=path.read_bytes()
            result[path.relative_to(root).as_posix()]=dict(kind='file',bytes=len(raw),sha256=sha(raw),links=info.st_nlink)
    return result
outcomes=[];observations=[];report_rows=[];input_hash_checks=0
audit="""import runpy,sys
def guard(event,args):
    if event in ('socket.connect','socket.getaddrinfo','socket.sendto','urllib.Request','webbrowser.open','subprocess.Popen','os.system'):
        raise RuntimeError('FICTIONAL_GUIDE_FORBIDS_REMOTE_OR_PROCESS_ACTION')
sys.addaudithook(guard)
script=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(script,run_name='__main__')
"""
def run_case(case,arguments,code,expected,*,script='inspect_eml.py',readonly=True,helper=None):
    global input_hash_checks
    before=snapshot(work);source_before=snapshot(inputs)
    command=[sys.executable,'-E','-s','-B','-c',helper if helper else audit]
    command+=list(map(str,arguments)) if helper else [str(module/script),*map(str,arguments)]
    result=subprocess.run(command,cwd=module,capture_output=True,timeout=30)
    assert result.returncode==code and not result.stderr,(case,result.returncode,result.stdout,result.stderr)
    value=json.loads(result.stdout);assert value==expected,(case,value,expected)
    assert str(work).encode() not in result.stdout and str(module).encode() not in result.stdout
    if readonly:assert snapshot(work)==before,case
    assert snapshot(inputs)==source_before,case;input_hash_checks+=len([row for row in source_before.values() if row['kind']=='file'])
    outcomes.append(dict(case=case,exit_code=code));observations.append(dict(case=case,exit_code=code,result=value))
    return value
def read_report(case,path,raw,rows):
    expected=summary(raw,rows);assert path.read_bytes()==encoded(expected)
    if os.name!='nt':assert path.stat().st_mode & 0o777==0o600
    report_rows.append(dict(case=case,path=path.relative_to(work).as_posix(),bytes=path.stat().st_size,sha256=sha(path.read_bytes()),input_sha256=sha(raw)))

# Generator adds a new selected input; its result is checked before capturing the full input snapshot.
sample_path=work/'fictional.eml'
run_case('generate-fictional-eml',['--out',sample_path],0,dict(status='PASS',fictional_message_written=True),script='fictional_eml.py',readonly=False)
assert sample_path.read_bytes()==sample
run_case('inspect-generator-stdout',['--input',sample_path],0,summary(sample,sample_rows))
run_case('fresh-compact-report',['--input',sample_path,'--out',reports/'sample.json'],0,dict(status='PASS',report_written=True),readonly=False)
read_report('fresh-compact-report',reports/'sample.json',sample,sample_rows)
run_case('repeat-stdout-is-deterministic',['--input',sample_path],0,summary(sample,sample_rows))
for name,raw,rows in accepted:
    path=reports/(name+'.json')
    run_case(name,['--input',inputs/(name+'.eml'),'--out',path],0,dict(status='PASS',report_written=True),readonly=False)
    read_report(name,path,raw,rows)
for name,raw,error in bad:
    path=reports/(name+'.json')
    run_case(name,['--input',inputs/(name+'.eml'),'--out',path],2,dict(status='ERROR',code=error))
    assert not path.exists()
for name,path,error in (
    ('refuse-source-byte-bound',inputs/'over-input-bound.eml','INPUT_SIZE_LIMIT' if os.name=='nt' else 'INPUT_LIMIT'),
    ('refuse-empty-source',inputs/'empty-source.eml','EML_SIZE_LIMIT'),
    ('native-hardlink-source-refused',inputs/'hard-alias.eml','CONTROL_NOT_SINGLE_LINK' if os.name=='nt' else 'INPUT_UNSAFE')):
    run_case(name,['--input',path],2,dict(status='ERROR',code=error))
run_case('refuse-overwriting-report',['--input',sample_path,'--out',reports/'sample.json'],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
run_case('refuse-input-output-alias',['--input',sample_path,'--out',sample_path],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
run_case('refuse-output-inside-copied-source',['--input',sample_path,'--out',module/'FICTIONAL-REFUSED.json'],2,
         dict(status='ERROR',code='OUTPUT_INSIDE_REPOSITORY' if os.name=='nt' else 'OUTPUT_INSIDE_SOURCE'))
assert not (module/'FICTIONAL-REFUSED.json').exists()
run_case('refuse-parent-traversal-spelling',['--input',inputs/'..'/'fictional.eml'],2,dict(status='ERROR',code='PATH_INVALID'))
run_case('refuse-unsupported-details-option',['--input',sample_path,'--include-details'],2,dict(status='ERROR',code='ARGUMENTS_INVALID'))
run_case('refuse-generator-overwrite',['--out',sample_path],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'),script='fictional_eml.py')
failure="""import json,os,sys,toolkit as t
real=os.write;calls=0
def controlled(fd,data):
    global calls
    calls+=1
    if calls==1:return real(fd,data[:5])
    raise OSError('Fictional write interruption')
os.write=controlled
try:t.write_new(sys.argv[1],b'Fictional partial output.\\n')
except OSError:print(json.dumps({'controlled_write_failure':True,'partial_output_retained':True}))
else:raise AssertionError('EXPECTED_WRITE_INTERRUPTION')
finally:os.write=real
"""
run_case('controlled-write-failure-retains-unconfirmed-file',[work/'partial-output.bin'],0,
         dict(controlled_write_failure=True,partial_output_retained=True),readonly=False,helper=failure)
assert (work/'partial-output.bin').read_bytes()==b'Ficti'
run_case('refuse-reusing-partial-output',['--input',sample_path,'--out',work/'partial-output.bin'],2,dict(status='ERROR',code='INPUT_OR_OUTPUT_REFUSED'))
assert (work/'partial-output.bin').read_bytes()==b'Ficti'
assert sample_path.read_bytes()==sample
assert runtime_hashes=={name:sha((module/name).read_bytes()) for name in runtimes}
assert {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()}==set(runtimes)
assert not list(work.rglob('*.pyc')) and not list(module.rglob('*.pyc'))
all_reports=[json.loads((work/row['path']).read_bytes()) for row in report_rows]
for value in all_reports:
    wire=encoded(value)
    assert all(marker not in wire for marker in (b'robot@',b'reviewer@',b'fictional.bin',b'sample.txt',b'notes.txt',b'<script>',b'https://example.invalid/pixel',b'Fictional plain body'))
assert all_reports[1]['parts']==all_reports[9]['parts'] and all_reports[1]['input_sha256']!=all_reports[9]['input_sha256']
ledger=dict(schema=1,cases=observations,reports=report_rows,controlled_failure='retained_five_byte_prefix')
(work/'OBSERVATIONS.json').write_bytes((json.dumps(ledger,sort_keys=True,indent=2)+'\n').encode())
files=[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(work.rglob('*'),key=lambda p:p.relative_to(work).as_posix()) if p.is_file()]
(work/'GUIDE-MANIFEST.json').write_bytes((json.dumps(dict(schema=1,files=files),sort_keys=True,indent=2)+'\n').encode())
assert all((work/row['path']).stat().st_size==row['bytes'] and sha((work/row['path']).read_bytes())==row['sha256'] for row in files)
print(json.dumps(dict(outcomes=outcomes,cases=len(outcomes),exit_code_counts={str(code):sum(row['exit_code']==code for row in outcomes) for code in (0,2)},
    reports_verified=len(report_rows),decoded_payload_hashes_checked=sum('sha256' in row for value in all_reports for row in value['parts']),
    input_hash_observations=input_hash_checks,fixture_files_preserved=len(accepted)+len(bad)+5,partial_output_bytes_retained=5,
    artifact_payload_hashes_checked=len(files),artifact_manifest_readbacks=1,expected_workspace_files=len(files)+1,
    unexpected_application_files=0,bytecode_files=0,runtime_bytes_preserved=True,fictional_eml_flow_checked=True,native_file_guards_checked=True,
    real_mail_used=False,mailboxes_accessed=False,messages_sent=False,bodies_rendered=False,files_extracted=False,
    remote_resources_followed=False,message_authenticity_verified=False,attachment_safety_verified=False,real_delivery_verified=False),sort_keys=True))
```

Expected ordered `outcomes` follow. Exit 0 for the controlled write case means
its synthetic failure/retention was observed; it does not certify a completed
report. Exit 2 is an intentional refusal, with no partial MIME summary emitted.

```json
[
  {
    "case": "generate-fictional-eml",
    "exit_code": 0
  },
  {
    "case": "inspect-generator-stdout",
    "exit_code": 0
  },
  {
    "case": "fresh-compact-report",
    "exit_code": 0
  },
  {
    "case": "repeat-stdout-is-deterministic",
    "exit_code": 0
  },
  {
    "case": "plain-7bit",
    "exit_code": 0
  },
  {
    "case": "utf8-base64",
    "exit_code": 0
  },
  {
    "case": "html-is-hashed-not-rendered",
    "exit_code": 0
  },
  {
    "case": "nested-alternative-mixed-order",
    "exit_code": 0
  },
  {
    "case": "text-attachment-omits-filename",
    "exit_code": 0
  },
  {
    "case": "opaque-optional-headers-and-encoded-subject",
    "exit_code": 0
  },
  {
    "case": "folded-subject-omitted",
    "exit_code": 0
  },
  {
    "case": "media-and-header-case-normalized",
    "exit_code": 0
  },
  {
    "case": "changed-header-keeps-body-fingerprint",
    "exit_code": 0
  },
  {
    "case": "empty-text-is-zero-byte-payload",
    "exit_code": 0
  },
  {
    "case": "canonical-base64-wraps-only-crlf",
    "exit_code": 0
  },
  {
    "case": "refuse-lf-only-source",
    "exit_code": 2
  },
  {
    "case": "refuse-nul-source",
    "exit_code": 2
  },
  {
    "case": "refuse-raw-eight-bit-source",
    "exit_code": 2
  },
  {
    "case": "refuse-physical-line-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-root-header-byte-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-missing-mime-version",
    "exit_code": 2
  },
  {
    "case": "refuse-missing-content-type",
    "exit_code": 2
  },
  {
    "case": "refuse-ordinary-received-header",
    "exit_code": 2
  },
  {
    "case": "refuse-duplicate-root-subject",
    "exit_code": 2
  },
  {
    "case": "refuse-duplicate-mime-header",
    "exit_code": 2
  },
  {
    "case": "refuse-nested-subject-header",
    "exit_code": 2
  },
  {
    "case": "refuse-duplicate-recipient-across-fields",
    "exit_code": 2
  },
  {
    "case": "refuse-display-name-address",
    "exit_code": 2
  },
  {
    "case": "refuse-recipient-group-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-subject-character-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-unfolded-header-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-unsupported-image-media",
    "exit_code": 2
  },
  {
    "case": "refuse-quoted-charset",
    "exit_code": 2
  },
  {
    "case": "refuse-missing-charset",
    "exit_code": 2
  },
  {
    "case": "refuse-quoted-printable",
    "exit_code": 2
  },
  {
    "case": "refuse-noncanonical-base64",
    "exit_code": 2
  },
  {
    "case": "refuse-base64-extra-whitespace",
    "exit_code": 2
  },
  {
    "case": "refuse-invalid-decoded-utf8",
    "exit_code": 2
  },
  {
    "case": "refuse-decoded-control",
    "exit_code": 2
  },
  {
    "case": "refuse-binary-without-attachment",
    "exit_code": 2
  },
  {
    "case": "refuse-binary-without-base64",
    "exit_code": 2
  },
  {
    "case": "refuse-attachment-path-name",
    "exit_code": 2
  },
  {
    "case": "refuse-reserved-attachment-name",
    "exit_code": 2
  },
  {
    "case": "refuse-casefold-duplicate-attachment",
    "exit_code": 2
  },
  {
    "case": "refuse-nonempty-preamble",
    "exit_code": 2
  },
  {
    "case": "refuse-nonempty-epilogue",
    "exit_code": 2
  },
  {
    "case": "refuse-child-count-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-depth-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-total-parts-across-branches",
    "exit_code": 2
  },
  {
    "case": "refuse-source-byte-bound",
    "exit_code": 2
  },
  {
    "case": "refuse-empty-source",
    "exit_code": 2
  },
  {
    "case": "native-hardlink-source-refused",
    "exit_code": 2
  },
  {
    "case": "refuse-overwriting-report",
    "exit_code": 2
  },
  {
    "case": "refuse-input-output-alias",
    "exit_code": 2
  },
  {
    "case": "refuse-output-inside-copied-source",
    "exit_code": 2
  },
  {
    "case": "refuse-parent-traversal-spelling",
    "exit_code": 2
  },
  {
    "case": "refuse-unsupported-details-option",
    "exit_code": 2
  },
  {
    "case": "refuse-generator-overwrite",
    "exit_code": 2
  },
  {
    "case": "controlled-write-failure-retains-unconfirmed-file",
    "exit_code": 0
  },
  {
    "case": "refuse-reusing-partial-output",
    "exit_code": 2
  }
]
```

## Retained artifacts and limits

Expected totals are 60 cases:16 accepted/control observations and44 refusals.
Twelve full report files verify15 decoded payload hashes. Fifty authored fixture
files remain, including the generated sample and the two hardlink spellings;
2,940 input-file hash observations are repeated checks, not unique messages.
The retained partial output is exactly five bytes. `OBSERVATIONS.json` records
only these fictional results, and `GUIDE-MANIFEST.json` binds64 payload files by
size/SHA-256, making65 workspace files. Formal verification checks exact expected
file names/bytes/reports/manifest and17 selected source hashes.

The positives `fictional_eml_flow_checked` and `native_file_guards_checked` are
true. All nine exclusion fields are false:real mail used, mailboxes accessed,
messages sent, bodies rendered, files extracted, remote resources followed,
message authenticity verified, attachment safety verified and real delivery
verified. Bounds describe the application, not OS resource confinement, hostile
filesystem containment or a hard overall timeout. Selected inputs/parents must
remain trusted and quiescent. Output permissions follow platform behavior and
do not establish confidentiality. JSON escaping/fingerprints are not anonymity.

No ordinary-mail interoperability, provider integration, SPF/DKIM/signature
verification, virus scanning, safe-to-open conclusion or rights review is implied.
Preserve unconfirmed files and choose a fresh output after private review.
Read [README.md](README.md) and the retained [I/O safety contract](IO-SAFETY.md).
