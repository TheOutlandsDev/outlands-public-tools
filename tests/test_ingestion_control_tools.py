"""Actual standalone/public-intake CLI interoperability on fictional records."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
TOOLS={'intake-mapping-diff':'mapping_diff.py','batch-replay-planner':'replay.py',
       'checkpoint-progression-checker':'checkpoints.py','ingestion-run-coverage-checker':'coverage.py'}

def encode(value): return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-ingestion-control-')
        self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)

    def invoke(self,script,args):
        result=subprocess.run([sys.executable,'-B',str(script),*map(str,args)],capture_output=True,
                              env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.stderr,b''); return result.returncode,json.loads(result.stdout)

    def cli(self,name,file=None,extra=(),folder=None):
        folder=folder or ROOT/'tools'/name
        return self.invoke(folder/TOOLS[name],['--input',file or folder/'examples/input.json',*extra])

    def test_valid_examples(self):
        for name in TOOLS:
            code,result=self.cli(name); self.assertEqual(code,0); self.assertEqual(result['status'],'PASS')

    def test_copied_standalone_sources(self):
        for name in TOOLS:
            folder=self.root/name; shutil.copytree(ROOT/'tools'/name,folder,ignore=shutil.ignore_patterns('__pycache__'))
            code,result=self.invoke(folder/'source_check.py',[]); self.assertEqual(code,0); self.assertEqual(result['status'],'SOURCE_MATCH')
            self.assertEqual(self.cli(name,folder=folder)[0],0)

    def test_new_reports_and_overwrite_prevention(self):
        for name in TOOLS:
            path=self.root/(name+'.json'); code,result=self.cli(name,extra=('--out',path))
            self.assertEqual(code,0); self.assertEqual(result,dict(status='PASS',report_written=True))
            raw=path.read_bytes(); self.assertEqual(json.loads(raw),self.cli(name)[1])
            self.assertEqual(self.cli(name,extra=('--out',path))[0],2); self.assertEqual(path.read_bytes(),raw)

    def test_source_tree_output_refusal(self):
        for name in TOOLS:
            path=ROOT/'tools'/name/'fictional-never-created.json'
            self.assertEqual(self.cli(name,extra=('--out',path))[0],2); self.assertFalse(path.exists())

    def test_fixed_argument_and_path_errors(self):
        for name in TOOLS:
            code,result=self.cli(name,extra=('--SYNTHETIC_SENTINEL',))
            self.assertEqual(code,2); self.assertEqual(result,dict(status='ERROR',code='ARGUMENTS_INVALID'))
            code,result=self.cli(name,file=self.root/'SYNTHETIC_SENTINEL.json')
            self.assertEqual(code,2); self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))

    def test_review_examples(self):
        for name,derived in zip(TOOLS,['changes','plan','suggested_checkpoint','declared_totals']):
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1); self.assertEqual(result['status'],'REVIEW_REQUIRED')
            if name=='intake-mapping-diff': self.assertEqual(len(result[derived]),3)
            else: self.assertIsNone(result[derived])

    def test_input_pins_and_unchanged_bytes(self):
        for name in TOOLS:
            path=ROOT/'tools'/name/'examples/input.json'; raw=path.read_bytes()
            _,result=self.cli(name); self.assertEqual(path.read_bytes(),raw); self.assertEqual(result['input_sha256'],sha(raw))

    def test_actual_public_intake_receipts_and_four_tools(self):
        fixture=ROOT/'tools/intake-mapping-diff/examples/input.json'
        mapping=json.loads(fixture.read_text(encoding='utf-8'))['before']; mapping_raw=encode(mapping)
        mapping_path=self.root/'mapping.json'; mapping_path.write_bytes(mapping_raw)
        batches=[]; receipts=[]
        for sequence in (1,2):
            source_raw=f'Record,Units\nitem-{sequence}-a,3\nitem-{sequence}-b,4\n'.encode()
            source=self.root/f'source-{sequence}.csv'; source.write_bytes(source_raw)
            code,preview=self.invoke(ROOT/'tools/workbook-intake-checker/intake.py',
                                    ['--input',source,'--mapping',mapping_path,'--format','csv'])
            self.assertEqual(code,0); self.assertEqual(preview['counts']['accepted_records'],2)
            preview_raw=encode(preview); preview_path=self.root/f'preview-{sequence}.json'; preview_path.write_bytes(preview_raw)
            declaration=dict(format='outlands-ingestion-receipt-v1',receipt_id=f'receipt-{sequence}',
                 source_sha256=sha(source_raw),mapping_sha256=sha(mapping_raw),preview_sha256=sha(preview_raw),
                 source_format='csv',sheet=None,counts=preview['counts'])
            receipt_raw=encode(declaration); receipt_path=self.root/f'receipt-{sequence}.json'; receipt_path.write_bytes(receipt_raw)
            code,review=self.invoke(ROOT/'tools/ingestion-receipt-reconciler/receipts.py',
                 ['--receipt',receipt_path,'--source',source,'--mapping',mapping_path,'--preview',preview_path])
            self.assertEqual(code,0); self.assertTrue(review['row_counts_recomputed'])
            batch=dict(id=f'batch-{sequence}',sequence=sequence,source_sha256=sha(source_raw),mapping_sha256=sha(mapping_raw),
                       preview_sha256=sha(preview_raw),counts=preview['counts'])
            batches.append(batch); receipts.append(dict(receipt_id=f'receipt-{sequence}',stream='sample-stream',batch=batch,
                       status='committed',receipt_sha256=sha(receipt_raw)))
        inputs={
         'intake-mapping-diff':dict(format='outlands-intake-mapping-diff-v1',before=mapping,after=mapping),
         'batch-replay-planner':dict(format='outlands-batch-replay-v1',stream='sample-stream',expected=batches,receipts=receipts[:1]),
         'checkpoint-progression-checker':dict(format='outlands-checkpoint-progression-v1',stream='sample-stream',previous=0,proposed=2,expected=batches,receipts=receipts),
         'ingestion-run-coverage-checker':dict(format='outlands-ingestion-run-coverage-v1',stream='sample-stream',expected=batches,receipts=receipts)}
        results={}
        for name,value in inputs.items():
            path=self.root/(name+'.json'); path.write_bytes(encode(value)); code,result=self.cli(name,file=path)
            self.assertEqual(code,0); self.assertFalse(result['target_changes_performed']); results[name]=result
        self.assertEqual(results['intake-mapping-diff']['before_mapping_sha256'],sha(mapping_raw))
        self.assertEqual([r['decision'] for r in results['batch-replay-planner']['plan']],['SKIP_ALREADY_COMMITTED','MANUAL_REVIEW_NEW_BATCH'])
        self.assertEqual(results['checkpoint-progression-checker']['suggested_checkpoint'],2)
        self.assertEqual(results['ingestion-run-coverage-checker']['declared_totals']['accepted_records'],4)
        self.assertFalse(results['ingestion-run-coverage-checker']['row_counts_recomputed'])

    def test_mapping_header_values_not_emitted(self):
        value=json.loads((ROOT/'tools/intake-mapping-diff/examples/input.json').read_text(encoding='utf-8'))
        value['after']['fields'][1]['source']='SYNTHETIC_SENTINEL'; path=self.root/'map.json'; path.write_bytes(encode(value))
        code,result=self.cli('intake-mapping-diff',file=path); self.assertEqual(code,1); self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))

    def test_no_execution_or_checkpoint_writes(self):
        for name in TOOLS:
            _,result=self.cli(name); self.assertFalse(result['target_changes_performed']); self.assertFalse(result['exactly_once_verified'])
            if name=='batch-replay-planner': self.assertFalse(result['retry_performed']); self.assertFalse(result['execution_authorized'])
            if name=='checkpoint-progression-checker': self.assertFalse(result['checkpoint_written'])
