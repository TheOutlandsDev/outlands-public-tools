import ast,csv,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));import kit

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='seed-release-');self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
    def cli(self,*args):
        return subprocess.run([sys.executable,'-I','-B',str(ROOT/'kit.py'),*map(str,args)],cwd=self.base,env=kit.child_environment(),capture_output=True,text=True,timeout=120)
    def test_original_pins_and_declared_tests_are_preserved(self):
        v=kit.inspect();self.assertEqual((v['original_files'],v['example_tests'],v['evaluation_test_definitions'],v['source_links']),(63,8,18,39))
        counts=[]
        for base in (ROOT/'original/04_examples/good/tests',ROOT/'original/05_evals'):
            counts.append(sum(sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_') for n in ast.walk(ast.parse(p.read_bytes()))) for p in base.rglob('test_*.py')))
        self.assertEqual(counts,[8,18])
    def test_prepare_exclusive_copy_and_original_independence(self):
        out=self.base/'exercise';report=kit.prepare(kit.TASKS[3],out)
        self.assertFalse(report['executed_code']);self.assertEqual(report['files'],5)
        rows=json.loads((out/'COPY-MANIFEST.json').read_bytes())['files']
        for row in rows:self.assertEqual(hashlib.sha256((out/row['path']).read_bytes()).hexdigest(),row['sha256'])
        (out/'starter/tagger.py').write_text('student-owned changed copy\n')
        kit.verify_original()
        with self.assertRaisesRegex(ValueError,'OUTPUT_EXISTS'):kit.prepare(kit.TASKS[3],out)
    def test_prepare_unknown_and_package_output_refused(self):
        with self.assertRaisesRegex(ValueError,'UNKNOWN_EVALUATION'):kit.prepare('../outside',self.base/'exercise')
        with self.assertRaisesRegex(ValueError,'OUTPUT_MUST_BE_OUTSIDE_PACKAGE'):kit.prepare(kit.TASKS[0],ROOT/'must-not-create')
        self.assertFalse((ROOT/'must-not-create').exists())
    def test_prepare_reparse_and_native_link_refused(self):
        p=self.base/'exercise';original=Path.lstat
        def fake(item,*a,**k):
            if item==p:
                class Reparse:st_mode=0o40755;st_file_attributes=0x400
                return Reparse()
            return original(item,*a,**k)
        with patch.object(Path,'lstat',fake),self.assertRaisesRegex(ValueError,'LINK_PATH_REFUSED'):kit.prepare(kit.TASKS[0],p)
        target=self.base/'target';target.mkdir();link=self.base/'linked'
        try:link.symlink_to(target,target_is_directory=True)
        except OSError:return
        with self.assertRaisesRegex(ValueError,'LINK_PATH_REFUSED'):kit.prepare(kit.TASKS[0],link/'exercise')
    def test_copied_cli_inspect_from_unrelated_directory(self):
        r=self.cli('inspect');self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stderr,'');self.assertEqual(json.loads(r.stdout)['original_files'],63)
        r=self.cli('--help');self.assertEqual(r.returncode,0);self.assertIn('prepare',r.stdout)
    def test_cli_prepare_and_fixed_error_without_private_paths(self):
        out=self.base/'exercise';r=self.cli('prepare','--task',kit.TASKS[0],'--out',out);self.assertEqual(r.returncode,0,r.stderr)
        r=self.cli('prepare','--task',kit.TASKS[0],'--out',out);self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout),{'status':'ERROR','code':'OUTPUT_EXISTS'});self.assertNotIn(str(self.base),r.stdout+r.stderr)
    def test_unexpected_starter_outcome_is_not_accepted(self):
        v=kit.observe('starter',kit.TASKS[0]);self.assertTrue(kit.starter_matches(v))
        v['passed']+=1;self.assertFalse(kit.starter_matches(v))
        with self.assertRaisesRegex(ValueError,'UNKNOWN_EVALUATION'):kit.observe('starter','../../outside')
    def test_prepared_exercise_can_use_separate_reference(self):
        task=kit.TASKS[3];out=self.base/'exercise';kit.prepare(task,out)
        shutil.copyfile(ROOT/'references'/task/'starter/tagger.py',out/'starter/tagger.py')
        r=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests'],cwd=out,env=kit.child_environment(),capture_output=True,text=True,timeout=60)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('Ran 2 tests',r.stderr);kit.verify_original()
    def test_link_catalog_is_metadata_only_and_csv_matches(self):
        p=ROOT/'original/02_source_catalog';rows=json.loads((p/'source_manifest.json').read_bytes())
        with (p/'source_manifest.csv').open(encoding='utf-8-sig',newline='') as f:tab=list(csv.DictReader(f))
        self.assertEqual(len(rows),39);self.assertEqual(len({r['id'] for r in rows}),39)
        self.assertEqual({r['id']:r['url'] for r in rows},{r['id']:r['url'] for r in tab})
        for row in rows:
            u=urlsplit(row['url']);self.assertEqual(u.scheme,'https');self.assertFalse(u.username);self.assertFalse(u.password);self.assertTrue(row['license_note']);self.assertTrue(row['retrieval_policy'])
    def test_changed_original_is_refused_before_probe_execution(self):
        fake=self.base/'package';fake.mkdir();shutil.copyfile(ROOT/'BASELINE.json',fake/'BASELINE.json');shutil.copytree(ROOT/'original',fake/'original')
        p=fake/'original/04_examples/good/src/agent_seed_examples/money.py';p.write_bytes(p.read_bytes()+b'\n# changed\n')
        with patch.object(kit,'ROOT',fake),self.assertRaisesRegex(ValueError,'ORIGINAL_BYTES_CHANGED'):kit.observe('examples')

if __name__=='__main__':unittest.main()
