import importlib.util,io,json,os,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('manufacturing_demo_builder',HERE/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class Packaging(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='manufacturing-demo-',dir=os.environ.get('OUTLANDS_TEST_TEMP'));cls.parent=Path(cls.temp.name)
  cls.output=cls.parent/'package';runtime=Path(os.environ['OUTLANDS_RUNTIME_CACHE']) if os.environ.get('OUTLANDS_RUNTIME_CACHE') else None;source=Path(os.environ['OUTLANDS_SOURCE_CACHE']) if os.environ.get('OUTLANDS_SOURCE_CACHE') else None
  b.build(cls.output,runtime,source);cls.raw=(cls.output/b.FILENAME).read_bytes();cls.manifest=b.verify(cls.raw);cls.contents=b.members(cls.raw)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_twelve_tools_and_two_unchanged_runners(self):
  files=[r['path'] for r in self.manifest['files']];tools={p.split('/')[2] for p in files if p.startswith('application/tools/')};self.assertEqual(set(b.TOOLS),tools)
  for name in files:
   if name.startswith('application/'):self.assertEqual(b.git('show',b.SOURCE+':'+name.removeprefix('application/')),self.contents[b.PREFIX+name])
  self.assertTrue(all('application/workshops/'+name in files for name in b.WORKSHOPS))
 def test_official_python_and_notices_with_isolated_local_adapter(self):
  self.assertEqual(b'python314.zip\n.\nimport site\n',self.contents[b.PREFIX+'runtime/python314._pth'])
  self.assertIn(b.PREFIX+'runtime/LICENSE.txt',self.contents);self.assertIn(b.PREFIX+'application/LICENSE',self.contents)
  self.assertEqual(b.git('show','HEAD:'+b.PACKAGE_PATH+'sitecustomize.py'),self.contents[b.PREFIX+'runtime/sitecustomize.py'])
 def test_deterministic_rebuild(self):
  second=self.parent/'second';runtime=Path(os.environ['OUTLANDS_RUNTIME_CACHE']) if os.environ.get('OUTLANDS_RUNTIME_CACHE') else None;source=Path(os.environ['OUTLANDS_SOURCE_CACHE']) if os.environ.get('OUTLANDS_SOURCE_CACHE') else None
  b.build(second,runtime,source);self.assertEqual(self.raw,(second/b.FILENAME).read_bytes())
 def changed(self,change):
  files=dict(self.contents);change(files);out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:
   for name,value in files.items():z.writestr(name,value)
  return out.getvalue()
 def test_changed_file_with_recomputed_crc_is_refused(self):
  with self.assertRaises(AssertionError):b.verify(self.changed(lambda files:files.update({b.PREFIX+'launch.py':b'changed'})))
 def test_unlisted_archive_member_is_refused(self):
  with self.assertRaises(AssertionError):b.verify(self.changed(lambda files:files.update({b.PREFIX+'unexpected.txt':b'fictional'})))
 def test_unsafe_members_and_links_are_refused(self):
  for name in ('../outside','/absolute','a\\b','a/../b','a//b'):
   raw=io.BytesIO()
   with zipfile.ZipFile(raw,'w') as z:z.writestr(name,b'fictional')
   with self.assertRaises(ValueError):b.members(raw.getvalue())
  raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as z:
   item=zipfile.ZipInfo('link');item.create_system=3;item.external_attr=0o120777<<16;z.writestr(item,b'elsewhere')
  with self.assertRaises(ValueError):b.members(raw.getvalue())
 def test_existing_output_is_refused_unchanged(self):
  before={p.name:b.sha(p.read_bytes()) for p in self.output.iterdir()}
  with self.assertRaises(AssertionError):b.build(self.output)
  self.assertEqual(before,{p.name:b.sha(p.read_bytes()) for p in self.output.iterdir()})
 def test_fresh_focused_bundle_runs_all_original_cli_checks(self):
  extracted=self.parent/'focused-extraction';extracted.mkdir()
  with zipfile.ZipFile(io.BytesIO(self.raw)) as z:z.extractall(extracted)
  package=next(extracted.iterdir());env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'}
  for script,number,reviews in [('manufacturing_review.py',12,4),('material_quality_review.py',24,13)]:
   folder=self.parent/script.removesuffix('.py')
   p=subprocess.run([sys.executable,'-B',str(package/'application/workshops'/script),'--workspace',str(folder)],capture_output=True,env=env,timeout=180)
   self.assertEqual(0,p.returncode,p.stdout+p.stderr);value=json.loads(p.stdout);self.assertEqual((number,reviews),(value['command_checks'],value['expected_review_outcomes']))
   for row in value['receipts']:
    for kind in ('input','report'):self.assertEqual(row[kind+'_sha256'],b.sha((folder/(row['case']+'-'+kind+'.json')).read_bytes()))

if __name__=='__main__':unittest.main()
