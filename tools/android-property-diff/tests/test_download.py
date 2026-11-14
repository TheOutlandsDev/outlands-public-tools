"""Independent copied literal-property consumers; no imports followed or properties applied. MIT."""
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
RUNTIME = ("property_diff.py", "declaration_diff.py", "inspection_support.py", "examples/generate.py")
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
def no_external(name,*args,**kwargs):
 assert name.split('.')[0] not in {'xml','pyexpat','_elementtree','lxml','socket','urllib','http','win32com'},'UNEXPECTED_PLATFORM_IMPORT'
 return original_import(name,*args,**kwargs)
builtins.__import__=no_external
base=Path(sys.argv[1]).resolve();sys.path.insert(0,str(base))
import property_diff as p
import declaration_diff as d
import inspection_support as s
assert Path(p.__file__).resolve()==base/'property_diff.py'
assert Path(d.__file__).resolve()==base/'declaration_diff.py'
assert Path(s.__file__).resolve()==base/'inspection_support.py'
assert p.cli is d.cli and p.inspect_sets is d.inspect_sets and p.register is d.register and p.unidentified is d.unidentified
assert p.issue is s.issue and p.text_lines is s.text_lines and d.source_inputs is s.source_inputs and d.write_report is s.write_report
kind=sys.argv[2];args=sys.argv[3:]
if kind=='affinity':
 sys.path.insert(0,str(base/'examples'));import generate as g
 assert Path(g.__file__).resolve()==base/'examples/generate.py' and g.canonical_directory is s.canonical_directory
 print(json.dumps(dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0)));raise SystemExit(0)
selected=[Path(args[i+1]) for i,flag in enumerate(args) if flag in ('--before','--after')]
output=Path(args[args.index('--output')+1])
if kind=='audit':
 d.Parser(description=p.__doc__);b'\xef\xbb\xbfprewarm'.decode('utf-8-sig')
 allowed={base/name for name in ('property_diff.py','declaration_diff.py','inspection_support.py','examples/generate.py')}
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
 sys.addaudithook(audit);code=p.main(args)
 assert read_counts=={path:path.stat().st_size for path in selected}
 raise SystemExit(code)
elif kind.startswith('limit:'):
 for name,value in json.loads(kind[6:]).items():
  assert name in ('MAX_ITEMS','MAX_REPORT','MAX_LINE','MAX_LINES');setattr(s,name,value)
elif kind=='scope_escape':
 original=p.inspect
 def summarized(*values):
  report=original(*values);report['scope']='Fictional </pre><script>never_execute</script> & "quoted"';return report
 p.inspect=summarized
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
raise SystemExit(p.main(args))
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
        self.temp = tempfile.TemporaryDirectory(prefix="property-cli-", dir=parent)
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
        self.fixture('demo.a=one\n','demo.a=two\n')
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



    def fixture(self,before,after):
        self.sides={}
        for side,values in (('before',before),('after',after)):
            if isinstance(values,(str,bytes)):values=[values]
            paths=[]
            for i,raw in enumerate(values):
                path=self.work/('fictional '+side+' '+str(i)+'.prop');path.write_bytes(raw.encode() if isinstance(raw,str) else raw);paths.append(path)
            self.sides[side]=paths
        self.inputs=[*self.sides['before'],*self.sides['after']]
    def new_output(self,suffix):self.output=self.work/('new report '+str(suffix))
    def args(self):
        result=[]
        for side in ('before','after'):
            for path in self.sides[side]:result+=['--'+side,path]
        return result+['--output',self.output]
    def call(self,args,*,error=None,output=None,probe=None,allow=(),ignore=(),env=None):
        before=self.snapshot();prefix=['-c',PROBE,self.copy,probe] if probe else [self.copy/'property_diff.py']
        done=self.run_child([*prefix,*args],env=env)
        self.assertEqual(done.stderr,b'',done.stderr.decode(errors='replace')[:3000])
        value=json.loads(done.stdout);self.assertEqual(done.stdout,json.dumps(value,sort_keys=probe!='affinity').encode()+NEWLINE)
        if error is not None:self.assertEqual(value,dict(status='INCOMPLETE',error=error));code=2
        elif probe=='affinity':self.assertEqual(value,dict(status='COPIED_RUNTIME_AFFINITY',dependencies=0));code=0
        else:
            report=self.check_report(output,args)
            self.assertEqual(value,dict(status=report['status'],changes=len(report['changes']),held_identities=len(report['held_identities']),coverage_issues=len(report['coverage_issues'])))
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
        self.assertEqual(set(report),{'schema_version','tool','scope','details_included','inputs','records','changes','held_identities','unidentified_rows','findings','coverage_issues','comparison_counts','comparison_scope','status'})
        self.assertEqual((report['schema_version'],report['tool']),(1,'Android Property Configuration Diff'))
        details='--include-details' in args;self.assertIs(report['details_included'],details)
        self.assertEqual(report['status'],'REVIEW_REQUIRED' if report['findings'] or report['coverage_issues'] else 'NO_SCOPE_FINDINGS')
        sources=[]
        for side in ('before','after'):
            paths=[Path(args[i+1]) for i,item in enumerate(args) if item=='--'+side]
            sources.extend(dict(id=side+'-'+str(i).zfill(4),bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for i,path in enumerate(paths,1))
        self.assertEqual(report['inputs'],sources);source_ids={r['id'] for r in sources}
        ids=[r['id'] for r in report['records']];self.assertEqual(ids,['record-'+str(i).zfill(4) for i in range(1,len(ids)+1)])
        by_id={r['id']:r for r in report['records']}
        for row in report['records']:
            self.assertEqual(set(row),{'id','side','source','line','supported'}|({'declared_identity','fields'} if details else set()))
            self.assertTrue(row['supported']);self.assertIn(row['side'],('before','after'));self.assertIn(row['source'],source_ids);self.assertTrue(row['source'].startswith(row['side']+'-'));self.assertGreater(row['line'],0)
            if details:self.assertEqual(set(row['fields']),{'value'})
        for row in report['changes']:
            self.assertEqual(set(row),{'kind','before_id','after_id','fields_changed'});self.assertIn(row['kind'],('added','removed','changed'));self.assertEqual(row['fields_changed'],['value'])
            for side in ('before','after'):
                identity=row[side+'_id']
                if identity is not None:self.assertIn(identity,ids);self.assertEqual(by_id[identity]['side'],side)
            self.assertEqual(row['before_id'] is None,row['kind']=='added');self.assertEqual(row['after_id'] is None,row['kind']=='removed')
        held_ids=set()
        for row in report['held_identities']:
            self.assertEqual(set(row),{'reason','before_ids','after_ids'});self.assertIn(row['reason'],('duplicate_declarations','unsupported_declaration','uninspected_identity_on_opposite_side'))
            for side in ('before','after'):
                for identity in row[side+'_ids']:self.assertIn(identity,ids);self.assertEqual(by_id[identity]['side'],side);held_ids.add(identity)
        self.assertFalse(held_ids & {row[key] for row in report['changes'] for key in ('before_id','after_id') if row[key] is not None})
        for row in report['unidentified_rows']:
            self.assertEqual(set(row),{'side','source','line'});self.assertIn(row['side'],('before','after'));self.assertIn(row['source'],source_ids);self.assertGreater(row['line'],0)
        for row in report['findings']+report['coverage_issues']:
            self.assertEqual(set(row),{'code','source','line'});self.assertTrue(row['source'] in source_ids or row['source']=='comparison');self.assertGreaterEqual(row['line'],0)
        counts=report['comparison_counts'];self.assertEqual(set(counts),{'unique_compared','unchanged','held'});self.assertEqual(counts['held'],len(report['held_identities']));self.assertEqual(counts['unique_compared'],counts['unchanged']+len(report['changes']))
        self.assertNotIn(str(self.work),raw.decode())
        if not details:
            self.assertNotIn('FICTIONAL_PRIVATE',raw.decode())
            self.assertTrue(all('fields' not in row and 'declared_identity' not in row for row in report['records']))
        markup=(output/'report.html').read_bytes();parsed=StaticHTML();parsed.feed(markup.decode());parsed.close()
        self.assertEqual(parsed.tags.count('html'),1);self.assertEqual(parsed.csp,["default-src 'none'; style-src 'unsafe-inline'"]);self.assertIn(html.escape(raw.decode(),quote=True).encode(),markup)
        members={name:(output/name).read_bytes() for name in ('report.json','report.html')}
        expected=dict(schema_version=1,files=[dict(path=name,bytes=len(data),sha256=sha(data)) for name,data in sorted(members.items())]);self.assertEqual((output/'MANIFEST.json').read_bytes(),encoded(expected));return report
    def report(self,details=False,**kwargs):return self.call(self.args()+(['--include-details'] if details else []),output=self.output,allow=[self.output],**kwargs)
    def codes(self,report,coverage=False):return {r['code'] for r in report['coverage_issues' if coverage else 'findings']}
    def symlink(self,path,target,directory=False):
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            if os.name=='nt' and getattr(error,'winerror',None)==1314 and os.environ.get('OUTLANDS_PROPERTY_REQUIRE_LINKS')!='1':self.skipTest(PROCESS_SYMLINK_REASON)
            raise

    def test_copied_runtime_affinity_and_help_without_platform_imports(self):
        self.call([],probe='affinity')
        for script in (self.copy/'property_diff.py',self.copy/'examples/generate.py'):
            before=self.snapshot();done=self.run_child([script,'--help']);self.assertEqual((done.returncode,done.stderr),(0,b''));self.assertIn(b'--output',done.stdout);self.assertEqual(self.snapshot(),before)
    def test_generator_examples_and_exclusive_output(self):
        target=self.work/'generated';before=self.snapshot();done=self.run_child([self.copy/'examples/generate.py','--output',target])
        self.assertEqual((done.returncode,done.stderr,done.stdout),(0,b'',json.dumps(dict(status='FICTIONAL_EXAMPLES_CREATED',files=4),sort_keys=True).encode()+NEWLINE));self.assertEqual({p.name for p in target.iterdir()},{'before.prop','same.prop','changed.prop','review.prop'});self.assertEqual({k:self.snapshot().get(k) for k in before},before)
        for name,changes,held in (('same',0,0),('changed',2,0),('review',0,1)):
            self.sides={'before':[target/'before.prop'],'after':[target/(name+'.prop')]};self.inputs=[*self.sides['before'],*self.sides['after']];self.new_output(name);report=self.report(details=True);self.assertEqual((len(report['changes']),len(report['held_identities'])),(changes,held))
        before=self.snapshot();done=self.run_child([self.copy/'examples/generate.py','--output',target]);self.assertEqual((done.returncode,done.stderr),(2,b''));self.assertEqual(json.loads(done.stdout),dict(status='INCOMPLETE',error='OUTPUT_EXISTS'));self.assertEqual(self.snapshot(),before)
    def test_first_equals_ascii_trim_and_empty_literal_values(self):
        self.fixture(' \tdemo.a \t= \tfirst=second#literal \t\ndemo.empty=\t ','demo.empty=\ndemo.a=first=second#literal');report=self.report(details=True)
        self.assertEqual(report['comparison_counts'],dict(unique_compared=2,unchanged=2,held=0));self.assertEqual([r['fields']['value'] for r in report['records']],['first=second#literal','','','first=second#literal'])
    def test_comments_reordering_and_line_positions_do_not_change_values(self):
        self.fixture('# before\ndemo.a=one\n\ndemo.b=two\n','demo.b = two\n# after\ndemo.a=one');report=self.report()
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertEqual(report['comparison_counts'],dict(unique_compared=2,unchanged=2,held=0));self.assertEqual([r['line'] for r in report['records']],[2,4,1,3])
    def test_case_sensitive_keys_and_non_ascii_space_value_are_literal(self):
        self.fixture('demo.A=one\ndemo.b=one','demo.a=one\ndemo.b=one\u00a0');report=self.report(details=True)
        self.assertEqual([r['kind'] for r in report['changes']],['removed','changed','added']);self.assertEqual(report['records'][-1]['fields']['value'],'one\u00a0')
    def test_changed_added_removed_and_rename_do_not_infer_identity(self):
        self.fixture('demo.removed=old\ndemo.changed=one\ndemo.before=same','demo.added=new\ndemo.changed=two\ndemo.after=same');report=self.report()
        self.assertEqual([r['kind'] for r in report['changes']],['removed','changed','removed','added','added']);self.assertEqual(report['changes'][1],dict(kind='changed',before_id='record-0002',after_id='record-0005',fields_changed=['value']));self.assertEqual(report['comparison_counts'],dict(unique_compared=5,unchanged=0,held=0))
    def test_multiple_fragment_roles_preserve_source_and_record_order(self):
        self.fixture(['demo.a=one\n','demo.b=two'],['demo.b=two','demo.a=changed\ndemo.c=three']);report=self.report()
        self.assertEqual([r['id'] for r in report['inputs']],['before-0001','before-0002','after-0001','after-0002']);self.assertEqual([r['source'] for r in report['records']],['before-0001','before-0002','after-0001','after-0002','after-0002']);self.assertEqual(report['changes'],[dict(kind='changed',before_id='record-0001',after_id='record-0004',fields_changed=['value']),dict(kind='added',before_id=None,after_id='record-0005',fields_changed=['value'])])
        self.new_output('local-ids');self.check_report_local_ids_follow_selected_file_order_not_persistent_identity()
    def test_before_duplicate_equal_values_are_held_without_removal(self):
        self.fixture('demo.a=one\ndemo.a=one','');report=self.report()
        self.assertEqual(report['changes'],[]);self.assertEqual(report['held_identities'],[dict(reason='duplicate_declarations',before_ids=['record-0001','record-0002'],after_ids=[])]);self.assertEqual(self.codes(report),{'AMBIGUOUS_DUPLICATE_DECLARATION'})
    def test_after_duplicates_equal_or_conflicting_never_choose_winner(self):
        for i,value in enumerate(('one','two')):
            self.fixture('demo.a=one','demo.a=one\ndemo.a='+value);self.new_output(i);report=self.report(details=True);self.assertEqual(report['changes'],[]);self.assertEqual(report['held_identities'],[dict(reason='duplicate_declarations',before_ids=['record-0001'],after_ids=['record-0002','record-0003'])]);self.assertEqual(report['comparison_counts']['unique_compared'],0)
    def test_duplicates_across_fragments_and_both_sides_remain_ambiguous(self):
        self.fixture(['demo.a=one','demo.a=two'],['demo.a=one','demo.a=two']);report=self.report()
        self.assertEqual(report['held_identities'],[dict(reason='duplicate_declarations',before_ids=['record-0001','record-0002'],after_ids=['record-0003','record-0004'])]);self.assertEqual(len(report['findings']),4);self.assertEqual(report['changes'],[])
    def test_unknown_before_holds_addition_but_keeps_matched_change(self):
        self.fixture('demo.a=old\nunsupported row','demo.a=new\ndemo.added=value');report=self.report()
        self.assertEqual(report['changes'],[dict(kind='changed',before_id='record-0001',after_id='record-0002',fields_changed=['value'])]);self.assertEqual(report['held_identities'],[dict(reason='uninspected_identity_on_opposite_side',before_ids=[],after_ids=['record-0003'])]);self.assertEqual(report['unidentified_rows'],[dict(side='before',source='before-0001',line=2)])
    def test_unknown_after_holds_removal_and_malformed_keys_are_coverage(self):
        self.fixture('demo.a=old\ndemo.removed=value','demo.a=new\nbad/key=value');report=self.report()
        self.assertEqual([r['kind'] for r in report['changes']],['changed']);self.assertEqual(report['held_identities'],[dict(reason='uninspected_identity_on_opposite_side',before_ids=['record-0002'],after_ids=[])]);self.assertEqual(self.codes(report,True),{'UNSUPPORTED_PROPERTY_KEY'})
    def test_import_directives_are_unopened_and_hold_uncertain_absence(self):
        external=self.work/'declared import.prop';external.write_text('FICTIONAL_PRIVATE_KEY=FICTIONAL_PRIVATE_VALUE\n')
        self.fixture('demo.a=old\nimport '+str(external)+'\n','demo.a=new\ndemo.added=value');report=self.report(probe='audit')
        self.assertEqual(self.codes(report,True),{'PROPERTY_IMPORT_NOT_FOLLOWED'});self.assertEqual([r['kind'] for r in report['changes']],['changed']);self.assertEqual(report['held_identities'][0]['reason'],'uninspected_identity_on_opposite_side');self.assertEqual(external.read_text(),'FICTIONAL_PRIVATE_KEY=FICTIONAL_PRIVATE_VALUE\n')
        self.fixture('demo.removed=value','import '+str(external));self.new_output('after');report=self.report(probe='audit');self.assertEqual(report['changes'],[]);self.assertEqual(report['held_identities'][0]['before_ids'],['record-0001'])
    def test_quotes_backslashes_dollars_hashes_and_no_continuation(self):
        text='demo.quote="fictional value"\ndemo.single=\'quoted\'\ndemo.expand=${FICTIONAL_ENV}\ndemo.slash=trailing\\\ndemo.hash=one#two\n'
        self.fixture(text,text);report=self.report(details=True);self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertEqual([r['fields']['value'] for r in report['records'][:5]],['"fictional value"',"'quoted'",'${FICTIONAL_ENV}','trailing\\','one#two'])
        self.fixture('demo.a=one\\\ncontinued','demo.a=one\\\ncontinued');self.new_output('continued');report=self.report(details=True);self.assertEqual(self.codes(report,True),{'UNSUPPORTED_PROPERTY_LINE'});self.assertEqual(report['comparison_counts']['unchanged'],1)
    def test_key_length_bound_reserved_looking_keys_and_no_runtime_semantics(self):
        key='a'*128;text=key+'=value\nro.demo=one\nctl.demo=two\npersist.demo=three'
        self.fixture(text,text);report=self.report();self.assertEqual(report['comparison_counts']['unchanged'],4);self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        self.fixture('','a'*129+'=value');self.new_output('too-long');report=self.report();self.assertEqual(self.codes(report,True),{'UNSUPPORTED_PROPERTY_KEY'});self.assertEqual(report['records'],[])
    def test_default_details_preserve_observations_and_escape_html(self):
        self.fixture('private.fiction=old','private.fiction=</pre><script>fictional</script> & "quoted"');basic=self.report();self.new_output('details');detailed=self.report(details=True)
        for key in set(basic)-{'records','details_included'}:self.assertEqual(basic[key],detailed[key])
        self.assertEqual(basic['records'],[{k:v for k,v in r.items() if k not in ('declared_identity','fields')} for r in detailed['records']]);self.assertNotIn('private.fiction',json.dumps(basic));markup=(self.output/'report.html').read_text();self.assertNotIn('<script>',markup);self.assertIn('&lt;script&gt;',markup)
        self.new_output('scope');report=self.report(probe='scope_escape');self.assertIn('never_execute',report['scope']);self.assertNotIn('<script>',(self.output/'report.html').read_text())
    def test_empty_comment_only_and_uncertain_empty_scope_remain_distinct(self):
        self.fixture('','# comment\n');report=self.report();self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertEqual(report['comparison_counts'],dict(unique_compared=0,unchanged=0,held=0))
        self.fixture('unsupported row','');self.new_output('uncertain');report=self.report();self.assertEqual(report['status'],'REVIEW_REQUIRED');self.assertEqual(report['records'],[]);self.assertTrue(report['unidentified_rows'])
    def test_utf8_bom_crlf_controls_and_invalid_encoding(self):
        self.fixture(b'\xef\xbb\xbfdemo.a=one\r\n',b'demo.a=one');self.assertEqual(self.report()['status'],'NO_SCOPE_FINDINGS')
        for i,raw in enumerate((b'\xff',b'a=\0',b'a=one\rtwo','a=x\u202ey'.encode(),'a=x\u2028y'.encode())):
            self.fixture(raw,'');self.new_output(i);self.report(error='UTF8_REQUIRED' if i==0 else 'TEXT_CONTROL_UNSUPPORTED');self.assertFalse(self.output.exists())
    def test_actual_line_and_physical_count_limits_without_truncation(self):
        raw=b'a='+b'x'*8190;self.fixture(raw,raw);self.assertEqual(self.report()['comparison_counts']['unchanged'],1)
        self.fixture(raw+b'x','');self.new_output('line');self.report(error='TEXT_LINE_LIMIT')
        self.fixture(b'\n'*19999,b'');self.new_output('lines-exact');self.assertEqual(self.report()['status'],'NO_SCOPE_FINDINGS')
        self.fixture(b'\n'*20000,b'');self.new_output('lines-over');self.report(error='TEXT_LINE_LIMIT')
    def test_actual_file_count_byte_and_aggregate_limits(self):
        self.fixture(['#\n']*16,['#\n']*16);self.assertEqual(len(self.report()['inputs']),32)
        self.fixture(['#\n']*16,['#\n']*17);self.new_output('count');self.report(error='INPUT_COUNT_LIMIT')
        raw=(b'#'+b' '*8190+b'\n')*128;self.assertEqual(len(raw),1048576);self.fixture([raw,raw],[raw,raw]);self.new_output('aggregate-exact');self.assertEqual(sum(r['bytes'] for r in self.report()['inputs']),4194304)
        self.fixture([raw,raw],[raw,raw,b'#x\n']);self.new_output('aggregate-over');self.report(error='TOTAL_BYTE_LIMIT')
        self.fixture(raw+b'x',b'');self.new_output('byte-over');self.report(error='INPUT_BYTE_LIMIT')
    def test_actual_global_record_and_unidentified_collection_limits(self):
        left=''.join('demo.k'+str(i)+'=x\n' for i in range(2000));self.fixture(left,left);report=self.report();self.assertEqual(len(report['records']),4000);self.assertEqual(report['comparison_counts']['unchanged'],2000)
        self.fixture(left,left+'demo.extra=x\n');self.new_output('records-over');self.report(error='RECORD_LIMIT');self.assertFalse(self.output.exists())
        self.fixture('unsupported\n'*2000,'unsupported\n'*2001);self.new_output('unidentified-over');self.report(error='RECORD_LIMIT');self.assertFalse(self.output.exists())
    def test_report_budget_partial_manifest_and_existing_partial_refusal(self):
        self.report(probe='limit:{"MAX_REPORT":100}',error='REPORT_BYTE_LIMIT');self.assertFalse(self.output.exists())
        self.report(probe='manifest_failure',error='IO_OR_INPUT_ERROR');self.assertEqual({p.name for p in self.output.iterdir()},{'report.json','report.html'});self.report(error='OUTPUT_EXISTS')
    def test_changed_and_short_reads_are_refused_before_output(self):
        first=self.sides['before'][0];self.report(probe='changed_input',error='INPUT_CHANGED',ignore=[first]);self.assertFalse(self.output.exists())
        self.fixture('demo.a=one','demo.a=two');self.report(probe='short_read',error='INPUT_CHANGED');self.assertFalse(self.output.exists())
    def test_required_cli_arguments_and_absolute_regular_routes(self):
        for args in ([],['--before',self.sides['before'][0],'--output',self.output],self.args()+['--private-unknown=secret']):self.call(args,error='ARGUMENTS_INVALID')
        for flag in ('--before','--after'):
            for path,code in (('relative.prop','LOCAL_ABSOLUTE_PATH_REQUIRED'),(self.work/'..'/'fictional.prop','LOCAL_ABSOLUTE_PATH_REQUIRED'),('//fictional/share/file.prop','LOCAL_ABSOLUTE_PATH_REQUIRED'),(str(self.inputs[0])+'\nprivate','INVALID_LOCAL_PATH'),(self.copy,'REGULAR_FILE_REQUIRED'),(self.work/'absent.prop','IO_OR_INPUT_ERROR')):
                args=self.args();args[args.index(flag)+1]=path;self.call(args,error=code)
    def test_duplicate_path_and_mandatory_hardlink_aliases_across_roles(self):
        alias=self.work/'hardlink.prop';os.link(self.sides['before'][0],alias);self.assertTrue(alias.samefile(self.sides['before'][0]))
        self.call(self.args()+['--after',alias],error='DUPLICATE_INPUT_FILE');self.call(self.args()+['--before',self.sides['before'][0]],error='DUPLICATE_INPUT_FILE')
        args=self.args();args[args.index('--after')+1]=self.sides['before'][0];self.call(args,error='DUPLICATE_INPUT_FILE')
    def test_new_output_guards_and_hostile_python_environment_are_inert(self):
        hostile=self.work/'hostile imports';hostile.mkdir()
        for name in ('sitecustomize.py','usercustomize.py','property_diff.py','inspection_support.py'):(hostile/name).write_text("raise AssertionError('FICTIONAL_PRIVATE_IMPORT')\n")
        env=dict(self.env,PYTHONPATH=str(hostile),PYTHONHOME=str(hostile),PYTHONSTARTUP=str(hostile/'sitecustomize.py'));self.report(env=env);self.report(error='OUTPUT_EXISTS')
        for destination in (*self.inputs,self.work,self.copy):args=self.args();args[-1]=destination;self.call(args,error='OUTPUT_EXISTS')
        args=self.args();args[-1]=self.work/'missing'/'report';self.call(args,error='IO_OR_INPUT_ERROR')
    def check_report_local_ids_follow_selected_file_order_not_persistent_identity(self):
        self.fixture(['demo.a=old','demo.b=same'],['demo.b=same','demo.a=new']);report=self.report(details=True)
        self.assertEqual([(r['id'],r['declared_identity']) for r in report['records']],[('record-0001','demo.a'),('record-0002','demo.b'),('record-0003','demo.b'),('record-0004','demo.a')]);self.assertEqual(report['changes'][0]['before_id'],'record-0001')
        self.fixture(['demo.b=same','demo.a=old'],['demo.b=same','demo.a=new']);self.new_output('reorder');report=self.report(details=True);self.assertEqual(report['changes'][0]['before_id'],'record-0002');self.assertEqual([r['kind'] for r in report['changes']],['changed'])
    def test_selected_only_audit_and_controlled_scope_bounds(self):
        trap=self.work/'not-opened.prop';trap.write_text('FICTIONAL_PRIVATE_KEY=FICTIONAL_PRIVATE_VALUE\n')
        self.fixture('demo.a=one\nimport '+str(trap),'demo.a=two\nunsupported');report=self.report(probe='audit');self.assertEqual(self.codes(report,True),{'PROPERTY_IMPORT_NOT_FOLLOWED','UNSUPPORTED_PROPERTY_LINE'});self.assertEqual(report['comparison_counts'],dict(unique_compared=1,unchanged=0,held=0))
        self.new_output('bound');self.report(probe='limit:{"MAX_ITEMS":1}',error='RECORD_LIMIT');self.assertFalse(self.output.exists())
    def test_native_symlink_inputs_and_output_parents(self):
        self.fixture('demo.a=one','demo.a=two');alias=self.work/'linked.prop';self.symlink(alias,self.sides['before'][0])
        for flag in ('--before','--after'):args=self.args();args[args.index(flag)+1]=alias;self.call(args,error='LINKED_PATH_REJECTED')
        route=self.work/'linked directory';self.symlink(route,self.work,directory=True);args=self.args();args[args.index('--before')+1]=route/self.sides['before'][0].name;self.call(args,error='LINKED_PATH_REJECTED')
        args=self.args();args[-1]=route/'new-report';self.call(args,error='LINKED_PATH_REJECTED')
        dangling=self.work/'dangling report';self.symlink(dangling,self.work/'nonexistent');args=self.args();args[-1]=dangling;self.call(args,error='OUTPUT_EXISTS')
    @unittest.skipUnless(os.name=='nt',PROCESS_WINDOWS_REASON)
    def test_native_windows_junction_and_stream_routes(self):
        self.fixture('demo.a=one','demo.a=two');junction=self.work/'junction';done=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(junction),str(self.work)],capture_output=True,timeout=15)
        self.assertEqual(done.returncode,0,done.stderr.decode(errors='replace'));self.addCleanup(lambda:junction.rmdir() if junction.exists() else None)
        for flag,path in (('--before',self.sides['before'][0]),('--after',self.sides['after'][0]),('--output',self.output)):
            args=self.args();args[args.index(flag)+1]=junction/path.name;self.call(args,error='LINKED_PATH_REJECTED')
            args=self.args();args[args.index(flag)+1]=str(path)+':stream';self.call(args,error='DEVICE_OR_STREAM_PATH_REJECTED')
    @unittest.skipUnless(os.name!='nt',PROCESS_POSIX_REASON)
    def test_native_posix_special_files_and_sparse_bounds(self):
        self.fixture('demo.a=one','demo.a=two');fifo=self.work/'fictional.fifo';os.mkfifo(fifo)
        connection=socket.socket(socket.AF_UNIX);connection.bind(str(self.work/'fictional.sock'));self.addCleanup(connection.close)
        for path in (fifo,self.work/'fictional.sock'):
            for flag in ('--before','--after'):args=self.args();args[args.index(flag)+1]=path;self.call(args,error='REGULAR_FILE_REQUIRED')
        sparse=self.work/'fictional sparse.prop'
        with sparse.open('wb') as stream:stream.truncate(1<<34)
        self.assertEqual(sparse.stat().st_size,1<<34);self.assertLess(sparse.stat().st_blocks*512,1<<20)
        args=self.args();args[args.index('--before')+1]=sparse;self.call(args,error='INPUT_BYTE_LIMIT');self.assertFalse(self.output.exists())

if __name__ == '__main__':
    unittest.main()
