"""Independent copied saved-event consumers; no live logs, native event decoding or native XML parser. MIT."""
import hashlib
import html
from html.parser import HTMLParser
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("event_timeline.py", "restricted_xml.py", "inspection_support.py", "examples/generate.py")
NEWLINE = b"\r\n" if os.name == "nt" else b"\n"
PROCESS_WINDOWS_ID = "test_download.Download.test_native_windows_junction_and_stream_routes"
PROCESS_WINDOWS_REASON = "Native Windows junction and stream fixtures"
PROCESS_POSIX_ID = "test_download.Download.test_native_posix_special_files_and_sparse_bounds"
PROCESS_POSIX_REASON = "Native POSIX FIFO, socket and sparse fixtures"
PROCESS_SYMLINK_ID = "test_download.Download.test_native_symlink_inputs_and_output_parents"
PROCESS_SYMLINK_REASON = "Native symlink privilege unavailable"
REQUIRED_WINDOWS_SKIPS = {(PROCESS_POSIX_ID, PROCESS_POSIX_REASON)}
REQUIRED_POSIX_SKIPS = {(PROCESS_WINDOWS_ID, PROCESS_WINDOWS_REASON)}
OPTIONAL_WINDOWS_LINK_SKIPS = {(PROCESS_SYMLINK_ID, PROCESS_SYMLINK_REASON)}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()


PROBE = r'''
import builtins,hashlib,importlib.metadata,json,os,sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and not list(importlib.metadata.distributions())
original_import=builtins.__import__
def no_native(name,*args,**kwargs):
 assert name.split('.')[0] not in {'xml','pyexpat','_elementtree','lxml','win32evtlog','win32evtlogutil','win32com','socket','urllib','http'},'NATIVE_XML_IMPORT'
 return original_import(name,*args,**kwargs)
builtins.__import__=no_native
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import event_timeline as e
import restricted_xml as r
import inspection_support as s
assert Path(e.__file__).resolve()==base/'event_timeline.py'
assert Path(r.__file__).resolve()==base/'restricted_xml.py'
assert Path(s.__file__).resolve()==base/'inspection_support.py'
assert e.parse_xml is r.parse and r.TextError is s.TextError and e.source_inputs is s.source_inputs and e.write_report is s.write_report
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import generate as g
 assert Path(g.__file__).resolve()==base/'examples/generate.py' and g.canonical_directory is s.canonical_directory
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)));raise SystemExit(0)
selected=[Path(args[i+1]) for i,flag in enumerate(args) if flag=='--file']
output=Path(args[args.index('--output')+1])
if kind=='audit':
 e.Parser(description=e.__doc__);b'\xef\xbb\xbfprewarm'.decode('utf-8-sig')
 allowed={base/name for name in ('event_timeline.py','restricted_xml.py','inspection_support.py','examples/generate.py')}
 allowed.update(selected);allowed.update(output/name for name in ('report.json','report.html','MANIFEST.json'))
 read_counts={path:0 for path in selected};original=os.read
 def audited_read(fd,size):
  before=os.fstat(fd);raw=original(fd,size);matched=[]
  for path in read_counts:
   info=path.stat()
   if (before.st_dev,before.st_ino)==(info.st_dev,info.st_ino):matched.append(path)
  assert len(matched)==1,'UNEXPECTED_FILE_DESCRIPTOR_READ'
  read_counts[matched[0]]+=len(raw);return raw
 os.read=audited_read
 def audit(event,values):
  if event.startswith(('socket.','subprocess.')) or event in ('os.system','os.startfile','webbrowser.open','ctypes.dlopen','compile','exec'):
   raise AssertionError('UNEXPECTED_EXTERNAL_ACTION')
  if event=='open' and not isinstance(values[0],int):assert Path(values[0]) in allowed,'UNEXPECTED_FILE_OPEN'
 sys.addaudithook(audit);code=e.main(args)
 assert read_counts=={path:path.stat().st_size for path in selected}
 raise SystemExit(code)
elif kind=='reader':
 tree,positions=r.parse(b'<r a="a\tb\nc&#x9;d" b="&amp;lt;">&#65;&#x42;<c/>tail&amp;</r>',lambda:None)
 assert tree.attrib=={'a':'a b c\td','b':'&lt;'} and tree.text=='AB' and tree.children[0].tail=='tail&'
 assert [positions[id(n)] for n in tree.iter()]==[1,2]
 assert r.parse(b'<r>&#13;</r>',lambda:None)[0].text=='\r'
elif kind.startswith('limit:'):
 for name,value in json.loads(kind[6:]).items():
  assert name in ('MAX_ITEMS','MAX_REPORT','MAX_LINE','MAX_LINES');setattr(s,name,value)
elif kind=='scope_escape':
 original=e.inspect
 def summarized(*values):
  report=original(*values);report['scope']='Fictional </pre><script>never_execute</script> & "quoted"';return report
 e.inspect=summarized
elif kind=='manifest_failure':
 original=os.open
 def failed(path,*a,**kw):
  if Path(path).name=='MANIFEST.json':raise OSError('FICTIONAL_PRIVATE_REPORT_DETAIL')
  return original(path,*a,**kw)
 os.open=failed
elif kind=='changed_input':
 original=os.read;changed=False
 def changed_read(*values):
  global changed
  raw=original(*values)
  if not changed:
   changed=True
   with selected[0].open('ab') as stream:stream.write(b'fictional mutation')
  return raw
 os.read=changed_read
elif kind=='short_read':os.read=lambda *unused:b''
else:raise AssertionError('UNKNOWN_CONTROLLED_PROBE')
raise SystemExit(e.main(args))
'''



class StaticHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.csp = []
    def handle_starttag(self, tag, attributes):
        assert tag in {"html", "meta", "title", "style", "h1", "p", "pre"}
        for key, value in attributes:
            assert not key.lower().startswith("on") and key not in {"src", "srcdoc", "href"}
            if key == "http-equiv":
                assert value == "Content-Security-Policy"
                self.csp.append(dict(attributes)["content"])
        self.tags.append(tag)



NAMESPACE='http://schemas.microsoft.com/win/2004/08/events/event'
def record(**changes):
    return {**dict(provider='Fictional.Provider',event_id=100,time_created='2026-01-01T00:00:00Z',channel='Fictional/Diagnostic',computer='FICTIONAL_PRIVATE_COMPUTER',record_id=1,level=4),**changes}
def export(events):return json.dumps(dict(schema_version=1,events=events),ensure_ascii=True).encode()
def xml_event(event=None,payload='',system_extra='',root_extra='',namespace=NAMESPACE):
    row=record() if event is None else event
    esc=lambda v:html.escape(str(v),quote=True)
    provider='<Provider Name="'+esc(row['provider'])+'"'+(' Guid="'+esc(row['provider_guid'])+'"' if row.get('provider_guid') is not None else '')+'/>'
    identity='<EventID'+(' Qualifiers="'+esc(row['qualifiers'])+'"' if row.get('qualifiers') is not None else '')+'>'+str(row['event_id'])+'</EventID>'
    fields=''.join('<'+tag+'>'+esc(row[key])+'</'+tag+'>' for key,tag in (('channel','Channel'),('computer','Computer'),('record_id','EventRecordID'),('level','Level'),('version','Version')) if row.get(key) is not None)
    return '<Event'+(' xmlns="'+namespace+'"' if namespace is not None else '')+root_extra+'><System>'+provider+identity+'<TimeCreated SystemTime="'+esc(row['time_created'])+'"/>'+fields+system_extra+'</System>'+payload+'</Event>'
def events_xml(*events):return '<Events>'+''.join(events)+'</Events>'

class Download(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.python_binary = Path(sys._base_executable).resolve()
        cls.python_pin = sha(cls.python_binary.read_bytes())
        cls.python_bytes = cls.python_binary.stat().st_size
        cls.python_version = ".".join(map(str, sys.version_info[:3]))
        if cls.python_pin != os.environ["OUTLANDS_TEST_PYTHON_SHA256"] or cls.python_version != os.environ["OUTLANDS_TEST_PYTHON_VERSION"]:
            raise AssertionError("EXPECTED_PYTHON_BINARY_OR_VERSION_DIFFERS")
    @classmethod
    def tearDownClass(cls):
        if sha(cls.python_binary.read_bytes()) != cls.python_pin or cls.python_binary.stat().st_size != cls.python_bytes:
            raise AssertionError("PYTHON_BINARY_CHANGED")
    def setUp(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        self.assertEqual(list(importlib.metadata.distributions()), [])
        parent = Path(os.environ.get("OUTLANDS_TEST_TEMP_ROOT") or tempfile.gettempdir())
        self.assertTrue(parent.is_absolute() and parent.is_dir())
        self.temp = tempfile.TemporaryDirectory(prefix="event-cli-", dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.copy = self.work / "copied runtime"; self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            raw = (ROOT/name).read_bytes(); target = self.copy/name
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw); self.pins[name] = sha(raw)
        self.inputs = []; self.output = self.work/"new report"
        self.env = {k:v for k,v in os.environ.items() if not k.upper().startswith(("PYTHON", "PIP_"))}
        self.env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_COLORS="0", NO_COLOR="1")
        self.addCleanup(self.runtime_preserved)
        self.fixture(export([record()]))
    def runtime_preserved(self):
        self.assertEqual({p.relative_to(self.copy).as_posix() for p in self.copy.rglob("*") if p.is_file()}, set(RUNTIME))
        self.assertEqual({name:sha((self.copy/name).read_bytes()) for name in RUNTIME}, self.pins)
        self.assertEqual(list(self.work.rglob("*.pyc")), [])
    def snapshot(self):
        rows = {}
        def visit(folder):
            for path in folder.iterdir():
                key = path.relative_to(self.work).as_posix(); info = path.lstat()
                if path.is_symlink() or getattr(path, "is_junction", lambda:False)(): rows[key] = ("LINK", os.readlink(path))
                elif stat.S_ISDIR(info.st_mode): rows[key] = ("DIRECTORY",); visit(path)
                elif stat.S_ISREG(info.st_mode):
                    if info.st_size > 8*1024*1024:
                        with path.open("rb") as stream:
                            sample = stream.read(64); stream.seek(-64, os.SEEK_END); sample += stream.read(64)
                        digest = "SPARSE_ENDPOINTS:"+sha(sample)
                    else: digest = sha(path.read_bytes())
                    rows[key] = (digest, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino, info.st_nlink)
                else: rows[key] = ("SPECIAL", info.st_mode)
        visit(self.work); return rows
    def run_child(self, command, env=None):
        if str(command[0]).endswith(".py"):
            bootstrap = "import runpy,sys;from pathlib import Path;p=Path(sys.argv[1]).resolve();sys.path.insert(0,str(p.parent));sys.argv=sys.argv[1:];runpy.run_path(str(p),run_name='__main__')"
            command = ["-c", bootstrap, *command]
        return subprocess.run([sys.executable,"-I","-B","-W","error",*map(str,command)], cwd=self.work,
                              env=self.env if env is None else env, stdin=subprocess.DEVNULL, capture_output=True, timeout=90)


    def fixture(self, values, kind='json'):
        self.kind=kind
        if isinstance(values,(str,bytes)):values=[values]
        self.files=[]
        for i,raw in enumerate(values):
            path=self.work/('fictional events '+str(i)+'.'+kind);path.write_bytes(raw.encode() if isinstance(raw,str) else raw);self.files.append(path)
        self.inputs=list(self.files)
    def new_output(self,suffix):self.output=self.work/('new report '+str(suffix))
    def args(self):
        result=[]
        for path in self.files:result+=['--file',path]
        return result+['--format',self.kind,'--output',self.output]
    def call(self,args,*,error=None,output=None,probe=None,allow=(),ignore=(),env=None):
        before=self.snapshot();prefix=['-c',PROBE,self.copy,probe] if probe else [self.copy/'event_timeline.py']
        done=self.run_child([*prefix,*args],env=env)
        self.assertEqual(done.stderr,b'',done.stderr.decode(errors='replace')[:3000])
        value=json.loads(done.stdout);self.assertEqual(done.stdout,json.dumps(value,sort_keys=probe!='affinity').encode()+NEWLINE)
        if error is not None:self.assertEqual(value,dict(status='INCOMPLETE',error=error));code=2
        elif probe=='affinity':self.assertEqual(value,dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0));code=0
        else:
            report=self.check_report(output,args)
            self.assertEqual(value,dict(status=report['status'],events=len(report['timeline']),groups=len(report['groups']),gaps=len(report['gaps']),coverage_issues=len(report['coverage_issues'])))
            value=report;code=int(report['status']!='NO_SCOPE_FINDINGS')
        self.assertEqual(done.returncode,code)
        for private in (str(self.work).encode(),b'FICTIONAL_PRIVATE',b'Traceback'):self.assertNotIn(private,done.stdout+done.stderr)
        after=self.snapshot();ignored={Path(p).relative_to(self.work).as_posix() for p in ignore}
        self.assertEqual({k:v for k,v in before.items() if k not in ignored},{k:after.get(k) for k in before if k not in ignored})
        for key in after.keys()-before.keys():
            path=self.work/key;self.assertTrue(any(path==Path(root) or path.is_relative_to(root) for root in allow),'Unexpected application write: '+key)
        self.runtime_preserved();return value
    def check_report(self,output,args):
        self.assertIsNotNone(output);self.assertEqual({p.name for p in output.iterdir()},{'report.json','report.html','MANIFEST.json'})
        raw=(output/'report.json').read_bytes();report=json.loads(raw);self.assertEqual(raw,encoded(report))
        self.assertEqual(set(report),{'schema_version','tool','input_format','details_included','scope','gap_threshold_seconds','inputs','timeline','groups','gaps','findings','coverage_issues','computer_and_payload_fields_omitted','input_order_was_chronological','repeated_groups','duplicate_scope','status'})
        self.assertEqual((report['schema_version'],report['tool']),(1,'Windows Event Timeline Inspector'))
        details='--include-details' in args;self.assertIs(report['details_included'],details);self.assertTrue(report['computer_and_payload_fields_omitted'])
        self.assertEqual(report['input_format'],args[args.index('--format')+1]);self.assertEqual(report['gap_threshold_seconds'],int(args[args.index('--gap-seconds')+1]) if '--gap-seconds' in args else 300)
        self.assertEqual(report['status'],'REVIEW_REQUIRED' if report['findings'] or report['coverage_issues'] else 'NO_SCOPE_FINDINGS')
        paths=[Path(args[i+1]) for i,item in enumerate(args) if item=='--file']
        self.assertEqual(report['inputs'],[dict(id='input-'+str(i).zfill(4),bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for i,path in enumerate(paths,1)])
        ids=[row['id'] for row in report['timeline']];self.assertEqual(set(ids),{'event-'+str(i).zfill(4) for i in range(1,len(ids)+1)});self.assertEqual(len(ids),len(set(ids)))
        groups=report['groups'];self.assertEqual([g['id'] for g in groups],['group-'+str(i).zfill(4) for i in range(1,len(groups)+1)])
        for group in groups:
            self.assertEqual(set(group),{'id','event_id','version','qualifiers','count','levels'}|({'provider','provider_guid','channel'} if details else set()))
            self.assertEqual(group['count'],sum(r['group_id']==group['id'] for r in report['timeline']))
        previous=0
        for i,row in enumerate(report['timeline']):
            self.assertEqual(set(row),{'id','source','record_index','group_id','event_id','level','elapsed_100ns','delta_100ns'}|({'time_created_utc','record_id'} if details else set()))
            self.assertIn(row['group_id'],[g['id'] for g in groups]);self.assertIn(row['source'],[r['id'] for r in report['inputs']]);self.assertGreater(row['record_index'],0)
            self.assertIs(type(row['elapsed_100ns']),str);elapsed=int(row['elapsed_100ns']);self.assertGreaterEqual(elapsed,previous)
            self.assertEqual(row['delta_100ns'],str(elapsed-previous) if i else None);previous=elapsed
            if details:
                self.assertTrue(row['time_created_utc'].endswith('Z'));self.assertEqual(len(row['time_created_utc'].split('.')[1]),8)
                self.assertTrue(row['record_id'] is None or type(row['record_id']) is str)
        for gap in report['gaps']:
            self.assertEqual(set(gap),{'before_id','after_id','duration_100ns'});self.assertIn(gap['before_id'],ids);self.assertIn(gap['after_id'],ids);self.assertGreater(int(gap['duration_100ns']),report['gap_threshold_seconds']*10000000)
        self.assertEqual(report['repeated_groups'],sum(g['count']>1 for g in groups))
        for row in report['findings']+report['coverage_issues']:self.assertEqual(set(row),{'code','source','record_index'});self.assertGreaterEqual(row['record_index'],0)
        self.assertNotIn(str(self.work),raw.decode());self.assertNotIn('FICTIONAL_PRIVATE',raw.decode())
        markup=(output/'report.html').read_bytes();parsed=StaticHTML();parsed.feed(markup.decode());parsed.close()
        self.assertEqual(parsed.tags.count('html'),1);self.assertEqual(parsed.csp,["default-src 'none'; style-src 'unsafe-inline'"]);self.assertIn(html.escape(raw.decode(),quote=True).encode(),markup)
        members={name:(output/name).read_bytes() for name in ('report.json','report.html')}
        expected=dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=sha(data)) for name,data in sorted(members.items())]);self.assertEqual((output/'MANIFEST.json').read_bytes(),encoded(expected));return report
    def report(self,details=False,gap=None,**kwargs):return self.call(self.args()+(['--include-details'] if details else [])+(['--gap-seconds',str(gap)] if gap is not None else []),output=self.output,allow=[self.output],**kwargs)
    def codes(self,report,coverage=False):return {r['code'] for r in report['coverage_issues' if coverage else 'findings']}
    def symlink(self,path,target,directory=False):
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            if os.name=='nt' and getattr(error,'winerror',None)==1314 and os.environ.get('OUTLANDS_EVENT_REQUIRE_LINKS')!='1':self.skipTest(PROCESS_SYMLINK_REASON)
            raise


    def test_copied_runtime_affinity_help_and_no_native_or_log_imports(self):
        self.call([],probe='affinity')
        for script in (self.copy/'event_timeline.py',self.copy/'examples/generate.py'):
            before=self.snapshot();done=self.run_child([script,'--help']);self.assertEqual((done.returncode,done.stderr),(0,b''));self.assertIn(b'--output',done.stdout);self.assertEqual(self.snapshot(),before)
        self.assertEqual(self.report(probe='reader')['status'],'NO_SCOPE_FINDINGS')
    def test_generator_json_xml_examples_and_existing_output_refusal(self):
        target=self.work/'generated';before=self.snapshot();done=self.run_child([self.copy/'examples/generate.py','--output',target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(0,b'',json.dumps(dict(status='FICTIONAL_EXAMPLES_CREATED',files=4),sort_keys=True).encode()+NEWLINE));self.assertEqual({p.name for p in target.iterdir()},{'clean.json','review.json','clean.xml','review.xml'});self.assertEqual({k:self.snapshot().get(k) for k in before},before)
        reports={}
        for kind in ('json','xml'):
            for name in ('clean','review'):
                self.files=[target/(name+'.'+kind)];self.inputs=list(self.files);self.kind=kind;self.new_output(name+kind);reports[name+kind]=self.report(details=True);self.assertEqual(reports[name+kind]['status'],'NO_SCOPE_FINDINGS' if name=='clean' else 'REVIEW_REQUIRED')
        self.assertEqual(reports['cleanjson']['timeline'],reports['cleanxml']['timeline']);self.assertEqual(reports['cleanjson']['groups'],reports['cleanxml']['groups'])
        before=self.snapshot();done=self.run_child([self.copy/'examples/generate.py','--output',target]);self.assertEqual((done.returncode,done.stderr),(2,b''));self.assertEqual(json.loads(done.stdout),dict(status='INCOMPLETE',error='OUTPUT_EXISTS'));self.assertEqual(self.snapshot(),before)
    def test_independent_json_xml_metadata_and_payload_equivalence(self):
        rows=[record(),record(record_id=2,time_created='2026-01-01T00:00:01.0000001Z')];self.fixture(export(rows));left=self.report(details=True)
        text=events_xml(*(xml_event(row,payload='<EventData><Data>FICTIONAL_PRIVATE_PAYLOAD&#13;</Data></EventData><UserData><Secret>FICTIONAL_PRIVATE_USER</Secret></UserData>',system_extra='<Security UserID="FICTIONAL_PRIVATE_SECURITY"/><Execution ProcessID="7"/>') for row in rows))
        self.fixture(text,'xml');self.new_output('xml');right=self.report(details=True)
        for key in set(left)-{'inputs','input_format'}:self.assertEqual(left[key],right[key])
        self.assertEqual([r['elapsed_100ns'] for r in right['timeline']],['0','10000001']);self.assertEqual(right['groups'][0]['count'],2)
    def test_offsets_fraction_order_pre_epoch_and_large_decimal_precision(self):
        rows=[record(time_created='2026-01-01T01:00:00.1234567+01:00',record_id=2**64-1),record(time_created='2026-01-01T00:00:00.1234566Z',record_id=2),record(time_created='1969-12-31T23:59:59.9999999Z',record_id=3)]
        self.fixture(export(rows));report=self.report(details=True,gap=0)
        self.assertEqual([r['id'] for r in report['timeline']],['event-0003','event-0002','event-0001']);self.assertEqual(report['timeline'][-1]['delta_100ns'],'1');self.assertEqual(report['timeline'][-1]['record_id'],'18446744073709551615')
        self.assertEqual(report['timeline'][-1]['time_created_utc'],'2026-01-01T00:00:00.1234567Z');self.assertEqual(report['timeline'][-1]['elapsed_100ns'],'17672256001234568')
    def test_timestamp_edge_offsets_minimum_maximum_and_invalid_coverage(self):
        self.fixture(export([record(time_created='0001-01-01T00:00:00Z'),record(time_created='9999-12-31T23:59:59.9999999Z',record_id=2)]));report=self.report(details=True,gap=0)
        self.assertEqual([r['time_created_utc'] for r in report['timeline']],['0001-01-01T00:00:00.0000000Z','9999-12-31T23:59:59.9999999Z']);self.assertEqual(report['timeline'][1]['elapsed_100ns'],'3155378975999999999')
        self.fixture(export([record(time_created='2026-01-01T14:00:00+14:00'),record(time_created='2025-12-31T10:00:00-14:00',record_id=2)]));self.new_output('edge');report=self.report(details=True);self.assertEqual([r['time_created_utc'] for r in report['timeline']],['2026-01-01T00:00:00.0000000Z']*2)
        values=['2026-01-01T00:00:00','2026-01-01T00:00:00-00:00','2026-01-01T00:00:00+14:01','2026-02-30T00:00:00Z','2026-01-01T00:00:60Z','2026-01-01T00:00:00.12345678Z','0000-01-01T00:00:00Z','0001-01-01T00:00:00+01:00','9999-12-31T23:59:59-01:00','2026-01-01t00:00:00z']
        self.fixture(export([record(time_created=value,record_id=i) for i,value in enumerate(values)]));self.new_output('bad');report=self.report();self.assertEqual(report['timeline'],[]);self.assertEqual(self.codes(report,True),{'UNSUPPORTED_EVENT_TIMESTAMP'});self.assertEqual(len(report['coverage_issues']),len(values))
    def test_stable_ties_input_order_and_local_ids_across_files(self):
        self.fixture([export([record(event_id=102)]),export([record(event_id=101)])]);report=self.report()
        self.assertEqual([r['event_id'] for r in report['timeline']],[102,101]);self.assertEqual([r['source'] for r in report['timeline']],['input-0001','input-0002']);self.assertTrue(report['input_order_was_chronological']);self.assertEqual([r['delta_100ns'] for r in report['timeline']],[None,'0']);self.assertFalse(report['findings'])
    def test_group_optional_values_and_guid_canonicalization(self):
        changes=[{},dict(version=0),dict(version=1),dict(qualifiers=0),dict(provider_guid='{A0000000-0000-4000-8000-000000000001}'),dict(provider_guid='a0000000-0000-4000-8000-000000000001',level=2)]
        self.fixture(export([record(record_id=i+1,**value) for i,value in enumerate(changes)]));report=self.report(details=True)
        self.assertEqual(len(report['groups']),5);self.assertEqual(report['groups'][-1]['count'],2);self.assertEqual(report['groups'][-1]['levels'],[4,2]);self.assertEqual(report['groups'][-1]['provider_guid'],'a0000000-0000-4000-8000-000000000001');self.assertEqual([g['version'] for g in report['groups'][:3]],[None,0,1]);self.assertEqual(report['groups'][3]['qualifiers'],0)
    def test_gap_strict_threshold_disabled_and_argument_bounds(self):
        self.fixture(export([record(),record(record_id=2,time_created='2026-01-01T00:05:00Z')]));self.assertEqual(self.report()['gaps'],[])
        self.fixture(export([record(),record(record_id=2,time_created='2026-01-01T00:05:00.0000001Z')]));self.new_output('over');report=self.report();self.assertEqual(report['gaps'],[dict(before_id='event-0001',after_id='event-0002',duration_100ns='3000000001')]);self.assertEqual(self.codes(report),{'DECLARED_TIME_GAP_EXCEEDS_THRESHOLD'})
        self.new_output('disabled');self.assertEqual(self.report(gap=0)['gaps'],[])
        for i,value in enumerate((-1,31536001)):
            self.new_output(i);self.report(gap=value,error='GAP_THRESHOLD_INVALID');self.assertFalse(self.output.exists())
        self.new_output('max');self.assertEqual(self.report(gap=31536000)['gaps'],[])
    def test_duplicate_and_conflicting_record_signatures_keep_occurrences(self):
        self.fixture(export([record(),record(),record(event_id=101)]));report=self.report();self.assertEqual(len(report['timeline']),3);self.assertEqual(self.codes(report),{'DUPLICATE_EXPORTED_RECORD','CONFLICTING_EXPORTED_RECORD_ID'});self.assertEqual([(r['code'],r['record_index']) for r in report['findings']],[('DUPLICATE_EXPORTED_RECORD',2),('CONFLICTING_EXPORTED_RECORD_ID',3)])
    def test_record_identity_scoped_by_file_computer_channel_and_presence(self):
        rows=[record(),record(computer='OtherFictionalComputer'),record(channel='Other/Channel'),record(computer=None),record(computer=None),record(channel=None),record(channel=None),record(record_id=None),record(record_id=None)]
        self.fixture(export(rows));report=self.report();self.assertEqual(report['findings'],[]);self.assertEqual(len(report['timeline']),len(rows))
        self.fixture([export([record()]),export([record()])]);self.new_output('files');report=self.report();self.assertEqual(report['findings'],[]);self.assertEqual(len(report['timeline']),2)
    def test_default_details_observations_and_static_html_escape(self):
        self.fixture(export([record(provider='<script>fictional</script>'),record(provider='<script>fictional</script>',record_id=2)]));basic=self.report();self.new_output('details');detailed=self.report(details=True)
        for key in set(basic)-{'groups','timeline','details_included'}:self.assertEqual(basic[key],detailed[key])
        self.assertEqual(basic['groups'],[{k:v for k,v in row.items() if k not in {'provider','provider_guid','channel'}} for row in detailed['groups']]);self.assertEqual(basic['timeline'],[{k:v for k,v in row.items() if k not in {'time_created_utc','record_id'}} for row in detailed['timeline']])
        self.assertNotIn('Fictional/Diagnostic',json.dumps(basic));self.assertNotIn('<script>',(self.output/'report.html').read_text(encoding='utf-8'));self.assertIn('&lt;script&gt;', (self.output/'report.html').read_text(encoding='utf-8'))
    def test_json_strict_schema_duplicate_keys_numbers_and_booleans(self):
        cases=[(b'{','INVALID_JSON'),(b'\xff','INVALID_JSON'),(b'{"schema_version":1,"schema_version":1,"events":[]}', 'DUPLICATE_JSON_KEY'),(b'{"schema_version":1,"events":[],"extra":0}','INVALID_EVENT_EXPORT_SCHEMA'),(b'{"schema_version":true,"events":[]}','INVALID_EVENT_EXPORT_SCHEMA'),(b'{"schema_version":1,"events":{}}','INVALID_EVENT_EXPORT_SCHEMA'),(b'{"schema_version":1,"events":[{"n":1.1}]}','JSON_NUMBER_UNSUPPORTED'),(b'{"schema_version":1,"events":[{"n":NaN}]}','JSON_NUMBER_UNSUPPORTED')]
        for i,(raw,code) in enumerate(cases):self.fixture(raw);self.new_output(i);self.report(error=code);self.assertFalse(self.output.exists())
    def test_invalid_json_metadata_is_coverage_accepted_records_remain(self):
        invalid=[record(event_id=True),record(event_id=65536),record(record_id=-1),record(level=256),record(version=True),record(provider=''),record(provider_guid='not-a-guid'),record(time_created='naive'),{},None]
        self.fixture(export([record(),*invalid]));report=self.report();self.assertEqual(len(report['timeline']),1);self.assertEqual(len(report['coverage_issues']),len(invalid));self.assertEqual(self.codes(report,True),{'UNSUPPORTED_EVENT_RECORD','UNSUPPORTED_EVENT_TIMESTAMP'})
    def test_json_bom_long_lines_encoding_and_control_rules(self):
        self.fixture(b'\xef\xbb\xbf'+export([record()])+b'\r\n');self.assertEqual(self.report()['status'],'NO_SCOPE_FINDINGS')
        large=export([record(record_id=i) for i in range(100)]);self.assertGreater(len(large),8192);self.fixture(large);self.new_output('long');self.assertEqual(len(self.report()['timeline']),100)
        for i,raw in enumerate((b'{"schema_version":1,"events":[],"\\u202e":0}',b'{"schema_version":1,"events":[{"provider":"x\\u0000y"}]}')):
            self.fixture(raw);self.new_output(i);self.report(error='JSON_TEXT_UNSUPPORTED')
    def test_xml_single_event_default_namespace_and_reset_prefix_coverage(self):
        for i,text in enumerate((xml_event(),xml_event(namespace=None),events_xml(xml_event()))):
            self.fixture(text,'xml');self.new_output(i);self.assertEqual(len(self.report()['timeline']),1)
        cases=[xml_event(namespace='urn:fiction'),xml_event().replace('<Provider ','<Provider xmlns="" '),'<e:Event xmlns:e="'+NAMESPACE+'"/>']
        for i,text in enumerate(cases):self.fixture(text,'xml');self.new_output('bad'+str(i));report=self.report();self.assertEqual(report['timeline'],[]);self.assertTrue(report['coverage_issues'])
    def test_xml_required_fields_unknown_metadata_mixed_and_pi_coverage(self):
        clean=xml_event()
        cases=[clean.replace('<System>','<System><EventID>200</EventID>'),clean.replace('<System>','<System>mixed'),clean.replace('<EventID>100</EventID>','<EventID><Nested/></EventID>'),clean.replace('<System>','<System><Unknown/>'),clean.replace('<Provider ','<Provider Extra="uninspected" '),'<?fiction note?>'+clean]
        for i,text in enumerate(cases):self.fixture(text,'xml');self.new_output(i);report=self.report();self.assertTrue(report['coverage_issues']);self.assertEqual(report['status'],'REVIEW_REQUIRED')
    def test_xml_encoded_cr_text_is_supported_but_identity_controls_refused(self):
        self.fixture(xml_event(payload='<EventData><Data>FICTIONAL_PRIVATE_PAYLOAD&#13;</Data></EventData>'),'xml');self.assertEqual(self.report(probe='reader')['status'],'NO_SCOPE_FINDINGS')
        self.fixture(xml_event().replace('Fictional.Provider','Fictional&#13;Provider'),'xml');self.new_output('identity');report=self.report(details=True);self.assertEqual(report['timeline'],[]);self.assertEqual(self.codes(report,True),{'UNSUPPORTED_EVENT_RECORD'})
        self.fixture(xml_event().replace('Fictional.Provider','Fictional&#x2e;Provider'),'xml');self.new_output('reference');self.assertEqual(self.report(details=True)['groups'][0]['provider'],'Fictional.Provider')
    def test_xml_declared_entities_cdata_refs_and_malformed_syntax_refused(self):
        target=self.work/'external.xml';target.write_bytes(b'FICTIONAL_PRIVATE_EXTERNAL')
        clean=xml_event();cases=[('<!DOCTYPE Event SYSTEM "'+target.as_uri()+'">'+clean,'XML_DECLARATIONS_REJECTED'),('<!-- <!ENTITY x "fictional"> -->'+clean,'XML_DECLARATIONS_REJECTED'),('<Event><![CDATA[x]]></Event>','XML_MARKUP_UNSUPPORTED'),('<Event>&unknown;</Event>','INVALID_XML_REFERENCE'),('<Event>&#0;</Event>','INVALID_XML_REFERENCE'),('<Event>&#x202e;</Event>','XML_REFERENCE_CONTROL_UNSUPPORTED'),('<Event>','INVALID_XML'),('<Event a="1" a="2"/>','DUPLICATE_XML_ATTRIBUTE'),('<?xml version="1.0" encoding="UTF-16"?>'+clean,'XML_UTF8_DECLARATION_REQUIRED')]
        for i,(text,code) in enumerate(cases):self.fixture(text,'xml');self.new_output(i);self.report(error=code);self.assertFalse(self.output.exists())
        self.assertEqual(target.read_bytes(),b'FICTIONAL_PRIVATE_EXTERNAL')
    def test_actual_xml_tree_attribute_and_text_limits(self):
        cases=[('<x>'*33+'</x>'*33,'XML_STRUCTURE_LIMIT'),('<x>\n'+'<c/>\n'*8000+'</x>','XML_STRUCTURE_LIMIT'),('<x'+''.join(' a'+str(i)+'="v"' for i in range(17))+'/>','XML_ATTRIBUTE_LIMIT'),('<x a="'+'v'*1025+'"/>','XML_ATTRIBUTE_LIMIT'),('<'+'a'*257+'/>','INVALID_XML_ATTRIBUTES'),('<x>'+'a'*5000+'\n'+'b'*3192+'</x>','XML_TEXT_LIMIT'),('<x><c/>'+'a'*5000+'\n'+'b'*3192+'</x>','XML_TEXT_LIMIT')]
        for i,(text,code) in enumerate(cases):self.fixture(text,'xml');self.new_output(i);self.report(error=code);self.assertFalse(self.output.exists())
    def test_actual_json_depth_node_string_and_event_count_limits(self):
        cases=[(export([record()]*4001),'EVENT_COUNT_LIMIT'),(b'{"schema_version":1,"events":[],"unused":'+b'['*9+b'0'+b']'*9+b'}','JSON_STRUCTURE_LIMIT'),(json.dumps(dict(schema_version=1,events=[],unused='x'*8193)).encode(),'JSON_TEXT_UNSUPPORTED'),(json.dumps(dict(schema_version=1,events=[],unused=[0]*40000)).encode(),'JSON_STRUCTURE_LIMIT')]
        for i,(raw,code) in enumerate(cases):self.fixture(raw);self.new_output(i);self.report(error=code);self.assertFalse(self.output.exists())
    def test_selected_file_count_aggregate_and_xml_physical_limits(self):
        empty=export([]);self.fixture([empty]*32);self.assertEqual(len(self.report()['inputs']),32)
        self.fixture([empty]*33);self.new_output('count');self.report(error='INPUT_COUNT_LIMIT')
        prefix=b'{"schema_version":1,"events":[]}';raw=prefix+b' '*(1048576-len(prefix));self.fixture([raw]*4);self.new_output('exact');self.assertEqual(sum(r['bytes'] for r in self.report()['inputs']),4194304)
        self.fixture([raw]*4+[empty]);self.new_output('aggregate');self.report(error='TOTAL_BYTE_LIMIT')
        self.fixture(raw+b' ');self.new_output('byte');self.report(error='INPUT_BYTE_LIMIT')
        for i,raw in enumerate((b'\n'*20000+b'<Events/>',b'<!--'+b'a'*8186+b'-->\n<Events/>',b'a\rb',b'\0',b'\xff')):
            self.fixture(raw,'xml');self.new_output('physical'+str(i));self.report(error='UTF8_REQUIRED' if i==4 else 'TEXT_LINE_LIMIT' if i<2 else 'TEXT_CONTROL_UNSUPPORTED')
    def test_selected_file_audit_never_queries_logs_network_or_native_xml(self):
        external=self.work/'external.bin';external.write_bytes(b'FICTIONAL_PRIVATE_EXTERNAL')
        self.fixture(export([record(extra_payload='FICTIONAL_PRIVATE_PAYLOAD')]));report=self.report(probe='audit');self.assertEqual(self.codes(report,True),{'UNINSPECTED_EVENT_FIELDS'})
        self.fixture(xml_event(payload='<EventData><x:include xmlns:x="http://www.w3.org/2001/XInclude" href="'+external.as_uri()+'"/></EventData>'),'xml');self.new_output('xml');self.assertEqual(self.report(probe='audit')['status'],'NO_SCOPE_FINDINGS');self.assertEqual(external.read_bytes(),b'FICTIONAL_PRIVATE_EXTERNAL')
    def test_cli_regular_absolute_inputs_fresh_output_aliases_and_hostile_environment(self):
        for args in ([],['--file',self.files[0],'--output',self.output],self.args()+['--private-unknown=secret']):self.call(args,error='ARGUMENTS_INVALID')
        for path,code in (('relative.json','LOCAL_ABSOLUTE_PATH_REQUIRED'),(self.work/'..'/'fictional.json','LOCAL_ABSOLUTE_PATH_REQUIRED'),('//fictional/share/file.json','LOCAL_ABSOLUTE_PATH_REQUIRED'),(str(self.files[0])+'\nprivate','INVALID_LOCAL_PATH'),(self.copy,'REGULAR_FILE_REQUIRED'),(self.work/'absent.json','IO_OR_INPUT_ERROR')):
            args=self.args();args[1]=path;self.call(args,error=code)
        alias=self.work/'hardlink.json';os.link(self.files[0],alias);self.assertTrue(alias.samefile(self.files[0]));self.call(self.args()+['--file',alias],error='DUPLICATE_INPUT_FILE');self.call(self.args()+['--file',self.files[0]],error='DUPLICATE_INPUT_FILE')
        hostile=self.work/'hostile imports';hostile.mkdir()
        for name in ('sitecustomize.py','usercustomize.py','json.py','restricted_xml.py'):(hostile/name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env=dict(self.env,PYTHONPATH=str(hostile),PYTHONHOME=str(hostile),PYTHONSTARTUP=str(hostile/'sitecustomize.py'));self.report(env=env);self.report(error='OUTPUT_EXISTS')
        for destination in (*self.inputs,self.work,self.copy):args=self.args();args[-1]=destination;self.call(args,error='OUTPUT_EXISTS')
        args=self.args();args[-1]=self.work/'missing'/'report';self.call(args,error='IO_OR_INPUT_ERROR')
    def test_changed_short_reads_partial_manifest_and_serialized_report_bound(self):
        self.report(probe='changed_input',error='INPUT_CHANGED',ignore=[self.files[0]]);self.assertFalse(self.output.exists());self.fixture(export([record()]));self.report(probe='short_read',error='INPUT_CHANGED');self.assertFalse(self.output.exists())
        self.report(probe='manifest_failure',error='IO_OR_INPUT_ERROR');self.assertEqual({p.name for p in self.output.iterdir()},{'report.json','report.html'});self.report(error='OUTPUT_EXISTS')
        self.new_output('budget');self.report(probe='limit:{"MAX_REPORT":100}',error='REPORT_BYTE_LIMIT');self.assertFalse(self.output.exists())
    def test_input_ids_positions_and_reordering_are_report_local(self):
        late=export([record(event_id=102,time_created='2026-01-01T00:01:00Z')]);early=export([record(event_id=101)])
        self.fixture([late,early]);report=self.report();self.assertEqual([(r['id'],r['source'],r['record_index']) for r in report['timeline']],[('event-0002','input-0002',1),('event-0001','input-0001',1)]);self.assertFalse(report['input_order_was_chronological'])
        self.fixture([early,late]);self.new_output('reordered');report=self.report();self.assertEqual([r['id'] for r in report['timeline']],['event-0001','event-0002']);self.assertTrue(report['input_order_was_chronological'])
    def test_empty_unknown_json_and_discarded_xml_security_scope(self):
        for i,(raw,kind) in enumerate(((export([]),'json'),('<Events/>','xml'))):self.fixture(raw,kind);self.new_output(i);report=self.report();self.assertEqual(report['timeline'],[]);self.assertEqual(report['groups'],[]);self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.fixture(export([record(message='FICTIONAL_PRIVATE_MESSAGE',security={'user':'FICTIONAL_PRIVATE_SECURITY'})]));self.new_output('json');report=self.report(details=True);self.assertEqual(self.codes(report,True),{'UNINSPECTED_EVENT_FIELDS'});self.assertEqual(len(report['timeline']),1)
        self.fixture(xml_event(system_extra='<Security UserID="FICTIONAL_PRIVATE_SECURITY"/>',payload='<UserData><User>FICTIONAL_PRIVATE_USER</User></UserData><RenderingInfo><Message>FICTIONAL_PRIVATE_MESSAGE</Message></RenderingInfo>'),'xml');self.new_output('xml');self.assertEqual(self.report(details=True)['status'],'NO_SCOPE_FINDINGS')
    def test_global_accepted_event_and_coverage_collection_limits(self):
        self.fixture([export([record(record_id=i) for i in range(2000)]),export([record(record_id=i) for i in range(2001)])]);self.report(error='RECORD_LIMIT');self.assertFalse(self.output.exists())
        self.fixture([export([None]*2000),export([None]*2001)]);self.new_output('coverage');self.report(error='RECORD_LIMIT');self.assertFalse(self.output.exists())
    def test_native_symlink_inputs_and_output_parents(self):
        self.fixture(export([record()]));alias=self.work/'linked.xml';self.symlink(alias,self.files[0])
        for flag in ('--file',):args=self.args();args[args.index(flag)+1]=alias;self.call(args,error='LINKED_PATH_REJECTED')
        route=self.work/'linked directory';self.symlink(route,self.work,directory=True);args=self.args();args[args.index('--file')+1]=route/self.files[0].name;self.call(args,error='LINKED_PATH_REJECTED')
        args=self.args();args[-1]=route/'new-report';self.call(args,error='LINKED_PATH_REJECTED')
        dangling=self.work/'dangling report';self.symlink(dangling,self.work/'nonexistent');args=self.args();args[-1]=dangling;self.call(args,error='OUTPUT_EXISTS')
    @unittest.skipUnless(os.name=='nt',PROCESS_WINDOWS_REASON)
    def test_native_windows_junction_and_stream_routes(self):
        self.fixture(export([record()]));junction=self.work/'junction';done=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(junction),str(self.work)],capture_output=True,timeout=15)
        self.assertEqual(done.returncode,0,done.stderr.decode(errors='replace'));self.addCleanup(lambda:junction.rmdir() if junction.exists() else None)
        for flag,path in (('--file',self.files[0]),('--output',self.output)):
            args=self.args();args[args.index(flag)+1]=junction/path.name;self.call(args,error='LINKED_PATH_REJECTED')
            args=self.args();args[args.index(flag)+1]=str(path)+':stream';self.call(args,error='DEVICE_OR_STREAM_PATH_REJECTED')
    @unittest.skipUnless(os.name!='nt',PROCESS_POSIX_REASON)
    def test_native_posix_special_files_and_sparse_bounds(self):
        self.fixture(export([record()]));fifo=self.work/'fictional.fifo';os.mkfifo(fifo)
        connection=socket.socket(socket.AF_UNIX);connection.bind(str(self.work/'fictional.sock'));self.addCleanup(connection.close)
        for path in (fifo,self.work/'fictional.sock'):
            for flag in ('--file',):args=self.args();args[args.index(flag)+1]=path;self.call(args,error='REGULAR_FILE_REQUIRED')
        sparse=self.work/'fictional sparse.xml'
        with sparse.open('wb') as stream:stream.truncate(1<<34)
        self.assertEqual(sparse.stat().st_size,1<<34);self.assertLess(sparse.stat().st_blocks*512,1<<20)
        args=self.args();args[args.index('--file')+1]=sparse;self.call(args,error='INPUT_BYTE_LIMIT');self.assertFalse(self.output.exists())

if __name__ == '__main__':
    unittest.main()
