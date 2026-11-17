"""Independent invented inputs and complete CLI report expectations."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

RUNTIME=('artifacts.py','run_core.py','toolkit.py','native_windows.py')
def encode(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(v):return hashlib.sha256(v).hexdigest()

class CopiedCLI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-artifact-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.app=self.root/'app';self.app.mkdir()
        origin=Path(__file__).resolve().parents[1]
        for name in RUNTIME:shutil.copyfile(origin/name,self.app/name)
        self.data={'source':b'Fictional source\n','code':b"raise RuntimeError('MUST_NOT_EXECUTE')\n",'empty':b''}
        self.roles={'source':'input','code':'code','empty':'evidence'}
        self.selection={'format':'outlands-run-artifact-selection-v1','run_id':'fictional-run','artifacts':[{'id':k,'role':self.roles[k]} for k in self.data]}
        self.paths={k:self.root/(k+'.bin') for k in self.data}
        for k,v in self.data.items():self.paths[k].write_bytes(v)
        self.sel=self.root/'selection.json';self.save()
    def save(self):self.sel.write_bytes(encode(self.selection))
    def snapshot(self):return {p.relative_to(self.root).as_posix():sha(p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
    def cli(self,code=0,error=None,items=None,extra=()):
        before=self.snapshot();args=['--selection',str(self.sel)]
        for k,p in (self.paths.items() if items is None else items):args+=['--item',k,str(p)]
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1');env.pop('PYTHONPATH',None)
        child="import pathlib,runpy,sys; p=pathlib.Path(sys.argv[1]).resolve(); sys.path.insert(0,str(p.parent)); sys.argv=sys.argv[1:]; runpy.run_path(str(p),run_name='__main__')"
        r=subprocess.run([sys.executable,'-I','-B','-c',child,str(self.app/'artifacts.py'),*args,*map(str,extra)],cwd=self.root,env=env,capture_output=True,timeout=45)
        self.assertEqual(r.returncode,code,(r.stdout,r.stderr));self.assertEqual(r.stderr,b'')
        for name,digest in before.items():self.assertEqual(sha((self.root/name).read_bytes()),digest,name)
        self.assertFalse(list(self.app.rglob('__pycache__')))
        value=json.loads(r.stdout)
        if error is not None:self.assertEqual(value,{'status':'ERROR','code':error})
        if code==0 and not extra:
            manifest={'format':'outlands-run-artifact-manifest-v1','run_id':self.selection['run_id'],'artifacts':[{'id':k,'role':self.roles[k],'bytes':len(self.data[k]),'sha256':sha(self.data[k])} for k in sorted(self.data)]}
            expected={'status':'PASS','format':'outlands-run-artifact-build-v1','selection_sha256':sha(self.sel.read_bytes()),'manifest':manifest,'manifest_sha256':sha(encode(manifest)),'source_paths_recorded':False,'content_privacy_verified':False,'target_changes_performed':False}
            self.assertEqual(value,expected);self.assertEqual(r.stdout.replace(b'\r\n',b'\n'),encode(expected))
        return value
    def test_complete_canonical_hashes(self):self.cli()
    def test_order_does_not_change_manifest(self):
        a=self.cli();self.selection['artifacts'].reverse();self.save();b=self.cli(items=list(reversed(list(self.paths.items()))));self.assertEqual(a['manifest'],b['manifest']);self.assertEqual(a['manifest_sha256'],b['manifest_sha256'])
    def test_raw_selection_pin_changes_on_reserialization(self):
        a=self.cli();self.sel.write_text(json.dumps(self.selection,indent=2),encoding='utf-8');b=self.cli();self.assertNotEqual(a['selection_sha256'],b['selection_sha256']);self.assertEqual(a['manifest_sha256'],b['manifest_sha256'])
    def test_empty_and_identical_buffers(self):
        self.data['empty']=self.data['source'];self.paths['empty'].write_bytes(self.data['empty']);self.cli()
    def test_code_not_executed_and_bodies_not_reported(self):
        value=self.cli();self.assertNotIn('MUST_NOT_EXECUTE',json.dumps(value));self.assertNotIn(str(self.root),json.dumps(value))
    def test_missing_and_extra_binding(self):
        self.cli(2,'BINDING_COVERAGE_INVALID',items=list(self.paths.items())[:-1]);self.cli(2,'BINDING_COVERAGE_INVALID',items=[*self.paths.items(),('extra',self.paths['source'])])
    def test_duplicate_binding(self):self.cli(2,'DUPLICATE_BINDING',items=[*self.paths.items(),('source',self.paths['source'])])
    def test_duplicate_selection(self):
        self.selection['artifacts'].append(copy.deepcopy(self.selection['artifacts'][0]));self.save();self.cli(2,'DUPLICATE_ARTIFACT')
    def test_invalid_role_and_unknown_field(self):
        original=copy.deepcopy(self.selection);self.selection['artifacts'][0]['role']='unknown';self.save();self.cli(2,'ROLE_INVALID')
        self.selection=original;self.selection['private_path']='fictional';self.save();self.cli(2)
    def test_strict_json(self):
        for raw in (b'{"format":1,"format":2}',b'{"value":NaN}',b'{"value":1.2}',b'[]'):
            self.sel.write_bytes(raw);self.cli(2)
    def test_sixteen_artifacts_and_seventeenth_refused(self):
        self.data={'item'+str(i):bytes([i]) for i in range(16)};self.roles={k:'input' for k in self.data};self.paths={k:self.root/(k+'.bin') for k in self.data}
        for k,v in self.data.items():self.paths[k].write_bytes(v)
        self.selection['artifacts']=[{'id':k,'role':self.roles[k]} for k in self.data];self.save();self.cli()
        self.selection['artifacts'].append({'id':'extra','role':'input'});self.save();self.cli(2,'ARTIFACT_LIMIT')
    def test_exact_individual_cap_and_one_over(self):
        self.data['source']=b'x'*(4*1024*1024);self.paths['source'].write_bytes(self.data['source']);self.cli()
        self.paths['source'].write_bytes(self.data['source']+b'x');self.cli(2)
    def test_exact_combined_cap_and_one_over(self):
        self.data={k:b'x'*(4*1024*1024) for k in ('one','two','three','four')};self.data['five']=b'';self.roles={k:'input' for k in self.data};self.paths={k:self.root/(k+'.bin') for k in self.data}
        for k,v in self.data.items():self.paths[k].write_bytes(v)
        self.selection['artifacts']=[{'id':k,'role':'input'} for k in self.data];self.save();self.cli();self.paths['five'].write_bytes(b'x');self.cli(2,'TOTAL_INPUT_LIMIT')
    def test_new_report_and_overwrite_refusal(self):
        expected=self.cli();out=self.root/'new.json';self.assertEqual(self.cli(extra=('--out',out)),{'status':'PASS','report_written':True});self.assertEqual(out.read_bytes(),encode(expected));self.cli(2,extra=('--out',out))
    def test_source_tree_destination_refused(self):
        out=self.app/'report.json';self.cli(2,extra=('--out',out));self.assertFalse(out.exists())
    def test_directory_and_missing_inputs(self):
        for path in (self.root,self.root/'missing'):self.cli(2,items=[(k,path if k=='source' else p) for k,p in self.paths.items()])
    def test_hardlinked_input_and_output_refused(self):
        link=self.root/'hardlink';os.link(self.paths['source'],link);self.cli(2)
        link.unlink();self.cli()  # Prove inputs are safe before testing output.
        target=self.root/'existing-output';target.write_bytes(b'Fictional existing report')
        os.link(target,link);self.cli(2,extra=('--out',link))
        self.assertEqual(target.read_bytes(),b'Fictional existing report')
    def test_linked_parent_input_and_output_refused(self):
        parent=self.root/'linked'
        if os.name=='nt':
            r=subprocess.run(['cmd','/c','mklink','/J',str(parent),str(self.app)],capture_output=True,timeout=15);self.assertEqual(r.returncode,0);self.assertTrue(os.path.isjunction(parent))
        else:parent.symlink_to(self.app,target_is_directory=True)
        self.cli(2,items=[(k,parent/'artifacts.py' if k=='code' else p) for k,p in self.paths.items()]);self.cli(2,extra=('--out',parent/'report.json'));self.assertFalse((self.app/'report.json').exists())
    def test_fixed_argument_error(self):self.cli(2,'ARGUMENTS_INVALID',extra=('--fictional-unknown-secret',))
    def test_all_roles_and_changed_bytes_observed(self):
        roles=['input','mapping','schema','configuration','code','result','evidence'];self.data={str('item'+str(i)):bytes([i]) for i in range(7)};self.roles=dict(zip(self.data,roles));self.paths={k:self.root/(k+'.bin') for k in self.data}
        for k,v in self.data.items():self.paths[k].write_bytes(v)
        self.selection['artifacts']=[{'id':k,'role':self.roles[k]} for k in self.data];self.save();a=self.cli();self.data['item0']=b'changed';self.paths['item0'].write_bytes(b'changed');b=self.cli();self.assertNotEqual(a['manifest_sha256'],b['manifest_sha256'])
