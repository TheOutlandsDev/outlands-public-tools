"""Independent copied VINTF consumers; no native XML parser, external resolution or device evaluation. MIT."""
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
RUNTIME = ("vintf_inspector.py", "restricted_xml.py", "inspection_support.py", "examples/generate.py")
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
 assert name.split('.')[0] not in {'xml','pyexpat','_elementtree','lxml'},'NATIVE_XML_IMPORT'
 return original_import(name,*args,**kwargs)
builtins.__import__=no_native
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import vintf_inspector as e
import restricted_xml as r
import inspection_support as s
assert Path(e.__file__).resolve()==base/'vintf_inspector.py'
assert Path(r.__file__).resolve()==base/'restricted_xml.py'
assert Path(s.__file__).resolve()==base/'inspection_support.py'
assert e.parse is r.parse and r.TextError is s.TextError and e.source_inputs is s.source_inputs and e.write_report is s.write_report
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import generate as g
 assert Path(g.__file__).resolve()==base/'examples/generate.py' and g.canonical_directory is s.canonical_directory
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)));raise SystemExit(0)
selected=[Path(args[i+1]) for i,flag in enumerate(args) if flag in ('--before','--file')]
output=Path(args[args.index('--output')+1])
if kind=='audit':
 e.Parser(description=e.__doc__);b'\xef\xbb\xbfprewarm'.decode('utf-8-sig')
 allowed={base/name for name in ('vintf_inspector.py','restricted_xml.py','inspection_support.py','examples/generate.py')}
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



def manifest(content='',kind='device',version='2.0',extra=''):
    return '<manifest version="'+version+'" type="'+kind+'"'+extra+'>'+content+'</manifest>'


def hidl(version='2.1',instance='default',transport='<transport>hwbinder</transport>',interface=False,extra=''):
    form=('<version>'+version+'</version><interface><name>IFiction</name><instance>'+instance+'</instance></interface>') if interface else '<fqname>@'+version+'::IFiction/'+instance+'</fqname>'
    return '<hal><name>example.hardware.fiction</name>'+transport+form+extra+'</hal>'


def aidl(version='1',instance='default',interface=False,extra=''):
    form=('<interface><name>IHelper</name><instance>'+instance+'</instance></interface>') if interface else '<fqname>IHelper/'+instance+'</fqname>'
    return '<hal format="aidl"><name>example.hardware.helper</name><version>'+version+'</version>'+form+extra+'</hal>'




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
        self.temp = tempfile.TemporaryDirectory(prefix="vintf-cli-", dir=parent)
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
        self.fixture(manifest(hidl()).encode())
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

    def fixture(self, current, before=None):
        self.current=[];self.before=[]
        for side,values in (('before',before),('current',current)):
            if values is None:continue
            if isinstance(values,(bytes,str)):values=[values]
            for i,data in enumerate(values):
                path=self.work/('fictional '+side+' '+str(i)+'.xml')
                path.write_bytes(data.encode() if isinstance(data,str) else data)
                (self.before if side=='before' else self.current).append(path)
        self.inputs=self.before+self.current
    def new_output(self, suffix):self.output=self.work/('new report '+str(suffix))
    def args(self):
        result=[]
        for flag,values in (('--before',self.before),('--file',self.current)):
            for path in values:result += [flag,path]
        return result+['--output',self.output]
    def call(self,args,*,error=None,output=None,probe=None,allow=(),ignore=(),env=None):
        before=self.snapshot();prefix=['-c',PROBE,self.copy,probe] if probe else [self.copy/'vintf_inspector.py']
        done=self.run_child([*prefix,*args],env=env)
        self.assertEqual(done.stderr,b'',done.stderr.decode(errors='replace')[:3000])
        value=json.loads(done.stdout);self.assertEqual(done.stdout,json.dumps(value,sort_keys=probe!='affinity').encode()+NEWLINE)
        if error is not None:self.assertEqual(value,dict(status='INCOMPLETE',error=error));code=2
        elif probe=='affinity':self.assertEqual(value,dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0));code=0
        else:
            report=self.check_report(output,args)
            self.assertEqual(value,dict(status=report['status'],declarations=len(report['declarations']),changes=len(report['changes']),coverage_issues=len(report['coverage_issues'])))
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
        self.assertEqual(set(report),{'schema_version','tool','scope','details_included','comparison_requested','inputs','hal_elements_observed','declarations','changes','ambiguous_comparisons','findings','coverage_issues','comparison_scope','status'})
        self.assertEqual((report['schema_version'],report['tool']),(1,'Android VINTF Manifest Inspector'))
        details='--include-details' in args;self.assertIs(report['details_included'],details);self.assertIs(report['comparison_requested'],'--before' in args)
        self.assertEqual(report['status'],'REVIEW_REQUIRED' if report['findings'] or report['coverage_issues'] else 'NO_SCOPE_FINDINGS')
        inputs=[]
        for flag,side in (('--before','before'),('--file','current')):
            values=[Path(args[i+1]) for i,item in enumerate(args) if item==flag]
            inputs.extend(dict(id=side+'-'+str(i).zfill(4),bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for i,path in enumerate(values,1))
        self.assertEqual(report['inputs'],inputs)
        ids=[row['id'] for row in report['declarations']];self.assertEqual(ids,['declaration-'+str(i).zfill(4) for i in range(1,len(ids)+1)])
        for row in report['declarations']:
            self.assertEqual(set(row),{'id','source','side','element','format','manifest_type'}|({'fields'} if details else set()))
            self.assertIn(row['side'],{'before','current'});self.assertTrue(row['source'].startswith(row['side']+'-'));self.assertGreaterEqual(row['element'],1)
            self.assertIn(row['format'],{'hidl','aidl'});self.assertIn(row['manifest_type'],{'device','framework'})
            if details:self.assertEqual(set(row['fields']),{'package','version','interface','instance','transport','arch'})
        for row in report['changes']:
            self.assertEqual(set(row),{'kind','before_id','current_id','fields_changed'});self.assertIn(row['kind'],{'added','removed','changed'})
            for key in ('before_id','current_id'):
                if row[key] is not None:self.assertIn(row[key],ids)
            if row['kind']=='added':self.assertIsNone(row['before_id']);self.assertEqual(row['fields_changed'],[])
            elif row['kind']=='removed':self.assertIsNone(row['current_id']);self.assertEqual(row['fields_changed'],[])
            else:self.assertTrue(row['fields_changed']);self.assertTrue(set(row['fields_changed'])<={'transport','arch'})
        for row in report['ambiguous_comparisons']:
            self.assertEqual(set(row),{'before_ids','current_ids'});self.assertTrue(len(row['before_ids'])>1 or len(row['current_ids'])>1)
            self.assertTrue(set(row['before_ids']+row['current_ids'])<=set(ids));self.assertFalse(set(row['before_ids']+row['current_ids'])&{v for change in report['changes'] for v in (change['before_id'],change['current_id'])})
        for row in report['findings']+report['coverage_issues']:
            self.assertEqual(set(row),{'code','source','element'});self.assertGreaterEqual(row['element'],0)
        self.assertNotIn(str(self.work),raw.decode())
        markup=(output/'report.html').read_bytes();parsed=StaticHTML();parsed.feed(markup.decode());parsed.close()
        self.assertEqual(parsed.tags.count('html'),1);self.assertEqual(parsed.csp,["default-src 'none'; style-src 'unsafe-inline'"])
        self.assertIn(html.escape(raw.decode(),quote=True).encode(),markup)
        members={name:(output/name).read_bytes() for name in ('report.json','report.html')}
        expected=dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=sha(data)) for name,data in sorted(members.items())])
        self.assertEqual((output/'MANIFEST.json').read_bytes(),encoded(expected));return report
    def report(self,details=False,**kwargs):return self.call(self.args()+(['--include-details'] if details else []),output=self.output,allow=[self.output],**kwargs)
    def codes(self,report,coverage=False):return {r['code'] for r in report['coverage_issues' if coverage else 'findings']}
    def symlink(self,path,target,directory=False):
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            if os.name=='nt' and getattr(error,'winerror',None)==1314 and os.environ.get('OUTLANDS_VINTF_REQUIRE_LINKS')!='1':self.skipTest(PROCESS_SYMLINK_REASON)
            raise


    def test_copied_runtime_affinity_help_and_no_native_parser(self):
        self.call([],probe='affinity')
        for script in (self.copy/'vintf_inspector.py',self.copy/'examples/generate.py'):
            before=self.snapshot();done=self.run_child([script,'--help']);self.assertEqual((done.returncode,done.stderr),(0,b''));self.assertIn(b'--output',done.stdout);self.assertEqual(self.snapshot(),before)
        self.assertEqual(self.report(probe='reader')['status'],'NO_SCOPE_FINDINGS')
    def test_generator_four_fictional_xml_files_and_fresh_output(self):
        target=self.work/'generated';before=self.snapshot();done=self.run_child([self.copy/'examples/generate.py','--output',target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(0,b'',json.dumps(dict(status='FICTIONAL_EXAMPLES_CREATED',files=4),sort_keys=True).encode()+NEWLINE))
        self.assertEqual({p.name for p in target.iterdir()},{'clean.xml','same.xml','changed.xml','review.xml'});self.assertEqual({k:self.snapshot().get(k) for k in before},before)
        for name,prior,status in (('clean',None,'NO_SCOPE_FINDINGS'),('same','clean','NO_SCOPE_FINDINGS'),('changed','clean','REVIEW_REQUIRED'),('review',None,'REVIEW_REQUIRED')):
            self.current=[target/(name+'.xml')];self.before=[target/(prior+'.xml')] if prior else [];self.inputs=self.before+self.current;self.new_output(name);self.assertEqual(self.report()['status'],status)
        before=self.snapshot();done=self.run_child([self.copy/'examples/generate.py','--output',target]);self.assertEqual((done.returncode,done.stderr),(2,b''));self.assertEqual(json.loads(done.stdout),dict(status='INCOMPLETE',error='OUTPUT_EXISTS'));self.assertEqual(self.snapshot(),before)
    def test_index_hidl_and_explicit_aidl_equivalent_forms(self):
        self.fixture([manifest(hidl(interface=True)),manifest(aidl(interface=True))]);report=self.report(details=True)
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertFalse(report['comparison_requested']);self.assertEqual(report['changes'],[])
        self.assertEqual([(r['format'],r['fields']['version'],r['fields']['interface']) for r in report['declarations']],[('hidl','2.1','IFiction'),('aidl','1','IHelper')])
    def test_multifragment_before_current_equivalence_ignores_form_and_order(self):
        self.fixture([manifest(aidl(interface=True)),manifest(hidl(interface=True))],[manifest(hidl()),manifest(aidl())]);report=self.report()
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertEqual(report['changes'],[]);self.assertEqual(report['ambiguous_comparisons'],[])
        self.assertEqual([r['source'] for r in report['declarations']],['before-0001','before-0002','current-0001','current-0002'])
    def test_identity_version_instance_type_and_format_changes_are_remove_add(self):
        for i,(old,new) in enumerate(((manifest(hidl()),manifest(hidl('2.2'))),(manifest(aidl()),manifest(aidl('2'))),(manifest(hidl()),manifest(hidl(instance='alternate'))),(manifest(hidl()),manifest(hidl(),kind='framework')),(manifest(hidl()),manifest(aidl())))):
            self.fixture(new,old);self.new_output(i);report=self.report();self.assertEqual([r['kind'] for r in report['changes']],['removed','added']);self.assertEqual(self.codes(report),{'SELECTED_HAL_DECLARATIONS_CHANGED'})
    def test_transport_and_arch_changes_only_pair_unique_matching_identity(self):
        self.fixture(manifest(hidl(transport='<transport arch="64">passthrough</transport>')),manifest(hidl()));report=self.report()
        self.assertEqual(report['changes'],[dict(kind='changed',before_id='declaration-0001',current_id='declaration-0002',fields_changed=['transport','arch'])])
        self.fixture(manifest(hidl(transport='<transport arch="32+64">passthrough</transport>')),manifest(hidl(transport='<transport arch="32">passthrough</transport>')));self.new_output('arch');self.assertEqual(self.report()['changes'][0]['fields_changed'],['arch'])
    def test_duplicate_identity_on_either_side_is_never_arbitrarily_paired(self):
        for i,(current,before) in enumerate(((manifest(hidl()+hidl()),manifest(hidl())),(manifest(hidl()),manifest(hidl()+hidl())),(manifest(hidl()+hidl()),manifest(hidl()+hidl())))):
            self.fixture(current,before);self.new_output(i);report=self.report();self.assertEqual(report['changes'],[]);self.assertEqual(len(report['ambiguous_comparisons']),1);self.assertEqual(self.codes(report),{'REPEATED_SELECTED_DECLARATION'})
    def test_conflicting_transports_and_cross_fragment_duplicates_are_held(self):
        self.fixture([manifest(hidl()),manifest(hidl(transport='<transport arch="32">passthrough</transport>'))],manifest(hidl()));report=self.report()
        self.assertEqual(self.codes(report),{'CONFLICTING_SELECTED_DECLARATION'});self.assertEqual(report['changes'],[])
        self.assertEqual(report['ambiguous_comparisons'],[dict(before_ids=['declaration-0001'],current_ids=['declaration-0002','declaration-0003'])])
    def test_hidl_fqname_carries_own_version_and_repeated_versions_are_findings(self):
        self.fixture(manifest(hidl(extra='<version>1.0</version>')));report=self.report(details=True);self.assertEqual(report['declarations'][0]['fields']['version'],'2.1')
        self.fixture(manifest(hidl(interface=True,extra='<version>2.1</version>')));self.new_output('repeated');report=self.report();self.assertTrue({'REPEATED_VERSION_DECLARATION','MULTIPLE_HIDL_VERSIONS_SAME_MAJOR','REPEATED_SELECTED_DECLARATION'}<=self.codes(report))
    def test_aidl_requires_meta_two_one_explicit_version_and_holds_transport(self):
        cases=((manifest(aidl(),version='1.0'),'AIDL_REQUIRES_SUPPORTED_META_VERSION'),(manifest(aidl().replace('<version>1</version>','')),'EXPLICIT_SINGLE_AIDL_VERSION_REQUIRED'),(manifest(aidl(extra='<version>2</version>')),'EXPLICIT_SINGLE_AIDL_VERSION_REQUIRED'),(manifest(aidl(extra='<transport ip="fictional">inet</transport>')),'AIDL_TRANSPORT_UNINSPECTED'))
        for i,(text,code) in enumerate(cases):
            self.fixture(text);self.new_output(i);report=self.report();self.assertIn(code,self.codes(report,True));self.assertEqual(report['status'],'REVIEW_REQUIRED')
    def test_namespaces_modifiers_unknown_nested_and_mixed_text_are_coverage(self):
        cases=((manifest(hidl(),extra=' xmlns="urn:fiction"'),'UNSUPPORTED_XML_NAMESPACE'),(manifest(hidl().replace('<hal>','<hal override="true" max-level="7">')),'HAL_MODIFIERS_NOT_EVALUATED'),(manifest(hidl()+'<kernel version="fiction"/>'),'UNINSPECTED_MANIFEST_ELEMENT'),(manifest(hidl(extra='<unknown private="never-copy"/>')),'UNINSPECTED_HAL_ELEMENT'),(manifest('mixed'+hidl()+'tail'),'UNINSPECTED_MIXED_TEXT'))
        for i,(text,code) in enumerate(cases):
            self.fixture(text);self.new_output(i);report=self.report();self.assertIn(code,self.codes(report,True));self.assertNotIn('never-copy',json.dumps(report))
    def test_root_metadata_outside_instance_diff_and_framework_identity_separate(self):
        self.fixture(manifest(hidl(),extra=' target-level="9"'),manifest(hidl(),extra=' target-level="7"'));report=self.report();self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertEqual(report['changes'],[])
        self.fixture([manifest(hidl()),manifest(hidl(),kind='framework')]);self.new_output('separate');report=self.report(details=True);self.assertEqual([r['manifest_type'] for r in report['declarations']],['device','framework']);self.assertEqual(report['findings'],[])
    def test_once_only_references_normalization_and_xml_declaration_forms(self):
        for i,declaration in enumerate(('<?xml version="1.0"?>','<?xml version="1.0" encoding="UTF-8"?>','<?xml version="1.0" encoding="UTF8" standalone="no"?>')):
            text=manifest(hidl()).replace('example.hardware.fiction','example.hardware.fict&#x69;on');self.fixture(declaration+text,manifest(hidl()));self.new_output(i);self.assertEqual(self.report(probe='reader')['status'],'NO_SCOPE_FINDINGS')
        self.fixture(manifest(hidl()).replace('example.hardware.fiction','example.hardware.&amp;#102;iction'));self.new_output('once');self.assertIn('UNSUPPORTED_PACKAGE_NAME',self.codes(self.report(),True))
    def test_dtd_entity_markers_even_inside_comments_are_refused_without_resolution(self):
        for i,prefix in enumerate(('<!DOCTYPE manifest SYSTEM "file:///fictional/not-opened.xml">','<!ENTITY x "fiction">','<!-- inert <!DOCTYPE manifest> marker -->','<!-- <!ENTITY x "fiction"> -->')):
            self.fixture(prefix+manifest());self.new_output(i);self.report(error='XML_DECLARATIONS_REJECTED');self.assertFalse(self.output.exists())
    def test_unknown_numeric_control_references_and_cdata_markup_are_refused(self):
        cases=(('&unknown;','INVALID_XML_REFERENCE'),('&amp','INVALID_XML_REFERENCE'),('&#0;','INVALID_XML_REFERENCE'),('&#xD800;','INVALID_XML_REFERENCE'),('&#13;','XML_REFERENCE_CONTROL_UNSUPPORTED'),('&#x2028;','XML_REFERENCE_CONTROL_UNSUPPORTED'),('&#X41;','INVALID_XML_REFERENCE'))
        for i,(value,code) in enumerate(cases):
            self.fixture('<unsupported>'+value+'</unsupported>');self.new_output(i);self.report(error=code)
        self.fixture('<unsupported><![CDATA[fiction]]></unsupported>');self.new_output('cdata');self.report(error='XML_MARKUP_UNSUPPORTED')
    def test_actual_xml_depth_element_attribute_count_name_and_value_limits(self):
        pairs=(('<x>'*32+'</x>'*32,None),('<x>'*33+'</x>'*33,'XML_STRUCTURE_LIMIT'),('<x>\n'+'\n'.join('<y/>' for _ in range(7999))+'\n</x>',None),('<x>\n'+'\n'.join('<y/>' for _ in range(8000))+'\n</x>','XML_STRUCTURE_LIMIT'),('<x '+' '.join('a'+str(i)+'="v"' for i in range(16))+'/>',None),('<x '+' '.join('a'+str(i)+'="v"' for i in range(17))+'/>','XML_ATTRIBUTE_LIMIT'),('<x '+('a'*256)+'="v"/>',None),('<x '+('a'*257)+'="v"/>','INVALID_XML_ATTRIBUTES'),('<x a="'+('a'*1024)+'"/>',None),('<x a="'+('a'*1025)+'"/>','XML_ATTRIBUTE_LIMIT'))
        for i,(text,code) in enumerate(pairs):
            self.fixture(text);self.new_output(i);report=self.report(error=code) if code else self.report()
            if code:self.assertFalse(self.output.exists())
            else:self.assertEqual(report['status'],'REVIEW_REQUIRED')
    def test_actual_text_and_tail_accumulation_limits_across_fragments(self):
        for prefix,suffix in (('<x>','</x>'),('<x><y/>','</x>')):
            for count,code in ((8192,None),(8193,'XML_TEXT_LIMIT')):
                text=prefix+'a'*4095+'\n'+'a'*(count-4096)+suffix;self.fixture(text);self.new_output(str(len(prefix))+str(count));self.report(error=code) if code else self.report()
        self.fixture('<x>'+('a'*100+'<!-- ignored -->\n')*100+'</x>');self.new_output('comments');self.report(error='XML_TEXT_LIMIT')
    def test_malformed_tags_attributes_comments_and_declarations_refuse(self):
        cases=(('', 'INVALID_XML'),('<a>','INVALID_XML'),('<a/><b/>','INVALID_XML'),('<a></b>','INVALID_XML'),('<x a="v" a="w"/>','DUPLICATE_XML_ATTRIBUTE'),('<x a="v"b="w"/>','INVALID_XML_ATTRIBUTES'),('<x><!-- a--b --></x>','INVALID_XML'),(' <?xml version="1.0"?><x/>','INVALID_XML'),('<?xml encoding="UTF-8" version="1.0"?><x/>','INVALID_XML_DECLARATION'),('<?xml version="1.0" encoding="latin1"?><x/>','XML_UTF8_DECLARATION_REQUIRED'))
        for i,(text,code) in enumerate(cases):self.fixture(text);self.new_output(i);self.report(error=code);self.assertFalse(self.output.exists())
    def test_encoding_controls_and_bom_crlf_hashes_on_both_input_roles(self):
        text=manifest(hidl());self.fixture(b'\xef\xbb\xbf'+text.encode()+b'\r\n');report=self.report();self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        cases=((b'\xff','UTF8_REQUIRED'),(b'\0','TEXT_CONTROL_UNSUPPORTED'),(b'a\rb','TEXT_CONTROL_UNSUPPORTED'),(chr(0x2028).encode(),'TEXT_CONTROL_UNSUPPORTED'))
        for side in ('current','before'):
            for i,(raw,code) in enumerate(cases):self.fixture(raw if side=='current' else text,raw if side=='before' else text);self.new_output(side+str(i));self.report(error=code);self.assertFalse(self.output.exists())
    def test_selected_file_count_aggregate_byte_and_physical_line_budgets(self):
        clean=manifest().encode();self.fixture([clean]*31,[clean]);self.assertEqual(len(self.report()['inputs']),32)
        self.fixture([clean]*32,[clean]);self.new_output('count');self.report(error='INPUT_COUNT_LIMIT')
        start=b'<x><!--\n';end=b'--></x>';padding=1048576-len(start)-len(end);chunk=b'a'*4095+b'\n';raw=start+chunk*(padding//len(chunk))+b'a'*(padding%len(chunk))+end;self.assertEqual(len(raw),1048576)
        self.fixture([raw,raw],[raw,raw]);self.new_output('aggregate-exact');self.assertEqual(sum(r['bytes'] for r in self.report()['inputs']),4194304)
        self.fixture([raw,raw,clean],[raw,raw]);self.new_output('aggregate-over');self.report(error='TOTAL_BYTE_LIMIT')
        self.fixture(raw+b' ');self.new_output('bytes-over');self.report(error='INPUT_BYTE_LIMIT')
        self.fixture(b'\n'*19999+clean);self.new_output('lines-exact');self.assertEqual(self.report()['status'],'NO_SCOPE_FINDINGS')
        self.fixture(b'\n'*20000+clean);self.new_output('lines-over');self.report(error='TEXT_LINE_LIMIT')
        self.fixture(b'<!--'+b'a'*8185+b'-->\n'+clean);self.new_output('length-exact');self.assertEqual(self.report()['status'],'NO_SCOPE_FINDINGS')
        self.fixture(b'<!--'+b'a'*8186+b'-->\n'+clean);self.new_output('length-over');self.report(error='TEXT_LINE_LIMIT')
    def test_default_privacy_details_and_static_html_preserve_observations(self):
        self.fixture(manifest(hidl(transport='<transport arch="64">passthrough</transport>')),manifest(hidl()));basic=self.report();self.new_output('details');detailed=self.report(details=True)
        self.assertNotIn('example.hardware',json.dumps(basic));self.assertIn('example.hardware',json.dumps(detailed))
        for key in set(basic)-{'declarations','details_included'}:self.assertEqual(basic[key],detailed[key])
        self.assertEqual(basic['declarations'],[{k:v for k,v in r.items() if k!='fields'} for r in detailed['declarations']])
        self.new_output('escaped');report=self.report(probe='scope_escape');self.assertIn('<script>',report['scope']);markup=(self.output/'report.html').read_bytes();self.assertNotIn(b'<script>',markup);self.assertIn(b'&lt;script&gt;never_execute&lt;/script&gt;',markup)
    def test_selected_file_audit_never_resolves_xinclude_uri_or_native_xml(self):
        payload=self.work/'external-secret.xml';payload.write_bytes(b'FICTIONAL_PRIVATE_EXTERNAL_DO_NOT_READ')
        text=manifest('<x:include xmlns:x="http://www.w3.org/2001/XInclude" href="'+payload.as_uri()+'"/>');self.fixture(text);report=self.report(probe='audit');self.assertEqual(self.codes(report,True),{'UNSUPPORTED_XML_NAMESPACE'});self.assertEqual(payload.read_bytes(),b'FICTIONAL_PRIVATE_EXTERNAL_DO_NOT_READ')
        self.fixture(manifest(hidl()+aidl()));self.new_output('clean');self.assertEqual(self.report(probe='audit')['status'],'NO_SCOPE_FINDINGS')
    def test_cli_requires_current_absolute_regular_inputs_and_fresh_output(self):
        for args in ([],['--before',self.current[0],'--output',self.output],self.args()+['--private-unknown=secret']):self.call(args,error='ARGUMENTS_INVALID')
        self.fixture(manifest(hidl()),manifest(hidl()))
        for role in ('--file','--before'):
            for path,code in (('relative.xml','LOCAL_ABSOLUTE_PATH_REQUIRED'),(self.work/'..'/'fictional.xml','LOCAL_ABSOLUTE_PATH_REQUIRED'),('//fictional/share/file.xml','LOCAL_ABSOLUTE_PATH_REQUIRED'),(str(self.current[0])+'\nprivate','INVALID_LOCAL_PATH'),(self.copy,'REGULAR_FILE_REQUIRED'),(self.work/'absent.xml','IO_OR_INPUT_ERROR')):
                args=self.args();args[args.index(role)+1]=path;self.call(args,error=code)
        args=self.args();args[-1]=self.work/'missing'/'report';self.call(args,error='IO_OR_INPUT_ERROR')
        self.report();self.report(error='OUTPUT_EXISTS')
        for destination in (*self.inputs,self.work,self.copy):args=self.args();args[-1]=destination;self.call(args,error='OUTPUT_EXISTS')
    def test_same_file_hardlink_aliases_across_roles_and_hostile_environment(self):
        self.fixture(manifest(hidl()),manifest(hidl()));alias=self.work/'hardlink.xml';os.link(self.current[0],alias);self.assertTrue(self.current[0].samefile(alias))
        for path in (self.current[0],alias):
            args=self.args();args[args.index('--before')+1]=path;self.call(args,error='DUPLICATE_INPUT_FILE')
            args=self.args();args[0:0]=['--file',path];self.call(args,error='DUPLICATE_INPUT_FILE')
        hostile=self.work/'hostile imports';hostile.mkdir()
        for name in ('sitecustomize.py','usercustomize.py','json.py','restricted_xml.py'):(hostile/name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env=dict(self.env,PYTHONPATH=str(hostile),PYTHONHOME=str(hostile),PYTHONSTARTUP=str(hostile/'sitecustomize.py'));self.report(env=env)
    def test_changed_short_reads_partial_manifest_and_serialized_report_bound(self):
        self.report(probe='changed_input',error='INPUT_CHANGED',ignore=[self.current[0]]);self.assertFalse(self.output.exists())
        self.fixture(manifest(hidl()));self.report(probe='short_read',error='INPUT_CHANGED');self.assertFalse(self.output.exists())
        self.report(probe='manifest_failure',error='IO_OR_INPUT_ERROR');self.assertEqual({p.name for p in self.output.iterdir()},{'report.json','report.html'});self.report(error='OUTPUT_EXISTS')
        self.new_output('budget');self.report(probe='limit:{"MAX_REPORT":100}',error='REPORT_BYTE_LIMIT');self.assertFalse(self.output.exists())
    def test_fragment_positions_and_input_ids_are_selected_order_not_global_identity(self):
        self.fixture([manifest(aidl()),manifest(hidl())]);report=self.report(details=True)
        self.assertEqual([(r['id'],r['source'],r['element']) for r in report['declarations']],[('declaration-0001','current-0001',5),('declaration-0002','current-0002',5)])
        self.assertEqual([r['fields']['interface'] for r in report['declarations']],['IHelper','IFiction'])
        self.fixture([manifest(hidl()),manifest(aidl())]);self.new_output('reordered');report=self.report(details=True);self.assertEqual([r['fields']['interface'] for r in report['declarations']],['IFiction','IHelper'])
        self.fixture(manifest(),manifest());self.new_output('empty');report=self.report();self.assertEqual(report['declarations'],[]);self.assertEqual(report['changes'],[]);self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
    def test_actual_declaration_record_and_coverage_collection_bounds(self):
        text=manifest('<hal><name>example.hardware.fiction</name><transport>hwbinder</transport><version>1.0</version><interface><name>IFiction</name>\n'+'\n'.join('<instance>i'+str(i)+'</instance>' for i in range(4001))+'\n</interface></hal>');self.fixture(text);self.report(error='RECORD_LIMIT');self.assertFalse(self.output.exists())
        self.fixture(manifest('\n'+'\n'.join('<unknown/>' for _ in range(4001))+'\n'));self.new_output('coverage');self.report(error='RECORD_LIMIT');self.assertFalse(self.output.exists())
    def test_native_symlink_inputs_and_output_parents(self):
        self.fixture(manifest(hidl()),manifest(hidl()));alias=self.work/'linked.xml';self.symlink(alias,self.current[0])
        for flag in ('--before','--file'):args=self.args();args[args.index(flag)+1]=alias;self.call(args,error='LINKED_PATH_REJECTED')
        route=self.work/'linked directory';self.symlink(route,self.work,directory=True);args=self.args();args[args.index('--file')+1]=route/self.current[0].name;self.call(args,error='LINKED_PATH_REJECTED')
        args=self.args();args[-1]=route/'new-report';self.call(args,error='LINKED_PATH_REJECTED')
        dangling=self.work/'dangling report';self.symlink(dangling,self.work/'nonexistent');args=self.args();args[-1]=dangling;self.call(args,error='OUTPUT_EXISTS')
    @unittest.skipUnless(os.name=='nt',PROCESS_WINDOWS_REASON)
    def test_native_windows_junction_and_stream_routes(self):
        self.fixture(manifest(hidl()),manifest(hidl()));junction=self.work/'junction';done=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(junction),str(self.work)],capture_output=True,timeout=15)
        self.assertEqual(done.returncode,0,done.stderr.decode(errors='replace'));self.addCleanup(lambda:junction.rmdir() if junction.exists() else None)
        for flag,path in (('--before',self.before[0]),('--file',self.current[0]),('--output',self.output)):
            args=self.args();args[args.index(flag)+1]=junction/path.name;self.call(args,error='LINKED_PATH_REJECTED')
            args=self.args();args[args.index(flag)+1]=str(path)+':stream';self.call(args,error='DEVICE_OR_STREAM_PATH_REJECTED')
    @unittest.skipUnless(os.name!='nt',PROCESS_POSIX_REASON)
    def test_native_posix_special_files_and_sparse_bounds(self):
        self.fixture(manifest(hidl()),manifest(hidl()));fifo=self.work/'fictional.fifo';os.mkfifo(fifo)
        connection=socket.socket(socket.AF_UNIX);connection.bind(str(self.work/'fictional.sock'));self.addCleanup(connection.close)
        for path in (fifo,self.work/'fictional.sock'):
            for flag in ('--before','--file'):args=self.args();args[args.index(flag)+1]=path;self.call(args,error='REGULAR_FILE_REQUIRED')
        sparse=self.work/'fictional sparse.xml'
        with sparse.open('wb') as stream:stream.truncate(1<<34)
        self.assertEqual(sparse.stat().st_size,1<<34);self.assertLess(sparse.stat().st_blocks*512,1<<20)
        args=self.args();args[args.index('--file')+1]=sparse;self.call(args,error='INPUT_BYTE_LIMIT');self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
