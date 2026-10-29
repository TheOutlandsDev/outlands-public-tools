"""Actual standalone CLI acceptance with fictional documents; no original systems."""
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
TOOLS={'context-manifest-checker':'context_manifest.py','document-chunk-planner':'chunks.py',
       'retrieval-evaluation-calculator':'retrieval.py','answer-evidence-checker':'evidence.py'}


class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-context-')
        self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)

    def cli(self,name,file='examples/input.json',extra=(),folder=None):
        folder=folder or ROOT/'tools'/name
        result=subprocess.run([sys.executable,'-B',str(folder/TOOLS[name]),'--input',str(folder/file),*map(str,extra)],
                              capture_output=True,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.stderr,b'')
        return result.returncode,json.loads(result.stdout)

    def test_valid_cli_examples(self):
        for name in TOOLS:
            with self.subTest(name=name):
                code,result=self.cli(name); self.assertEqual(code,0); self.assertEqual(result['status'],'PASS')

    def test_independent_copies_and_source_pins(self):
        for name in TOOLS:
            folder=self.root/name; shutil.copytree(ROOT/'tools'/name,folder,ignore=shutil.ignore_patterns('__pycache__'))
            result=subprocess.run([sys.executable,'-B',str(folder/'source_check.py')],capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'],'SOURCE_MATCH')
            self.assertEqual(self.cli(name,folder=folder)[0],0)

    def test_new_reports_and_overwrite_refusal(self):
        for name in TOOLS:
            out=self.root/(name+'.json')
            code,result=self.cli(name,extra=('--out',out)); self.assertEqual(code,0)
            self.assertEqual(result,dict(status='PASS',report_written=True))
            raw=out.read_bytes(); self.assertEqual(json.loads(raw),self.cli(name)[1])
            code,result=self.cli(name,extra=('--out',out)); self.assertEqual(code,2)
            self.assertEqual(out.read_bytes(),raw)

    def test_source_tree_output_refusal(self):
        for name in TOOLS:
            out=ROOT/'tools'/name/'fictional-report-never-created.json'
            code,_=self.cli(name,extra=('--out',out)); self.assertEqual(code,2); self.assertFalse(out.exists())

    def test_fixed_argument_errors(self):
        for name in TOOLS:
            code,result=self.cli(name,extra=('--SYNTHETIC_SENTINEL',))
            self.assertEqual(code,2); self.assertEqual(result,dict(status='ERROR',code='ARGUMENTS_INVALID'))

    def test_review_examples_withhold_derived_results(self):
        for name,key in zip(TOOLS,['manifest','chunks','metrics','evidence']):
            code,result=self.cli(name,'examples/needs-review.json')
            self.assertEqual(code,1); self.assertEqual(result['status'],'REVIEW_REQUIRED'); self.assertIsNone(result[key])

    def test_input_bytes_remain_unchanged(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes()
            _,result=self.cli(name); self.assertEqual(file.read_bytes(),raw)
            self.assertEqual(result['input_sha256'],hashlib.sha256(raw).hexdigest())

    def test_connected_four_tool_cohort(self):
        body='ABCDEFGHIJK'; d=dict(id='sample',revision=3,text=body,sha256=hashlib.sha256(body.encode()).hexdigest())
        ref={k:d[k] for k in ('id','revision','sha256')}
        inputs={
          'context-manifest-checker':dict(format='outlands-context-manifest-v1',documents=[d],relationships=[]),
          'document-chunk-planner':dict(format='outlands-document-chunks-v1',documents=[d],policy=dict(max_chars=5,overlap_chars=2)),
          'retrieval-evaluation-calculator':dict(format='outlands-retrieval-evaluation-v1',documents=[d],k=2,
             queries=[dict(id='query-a',ranked=[ref],relevant=[ref])]),
        }
        results={}
        for name,value in inputs.items():
            folder=self.root/name; folder.mkdir(); file=folder/'input.json'; file.write_text(json.dumps(value),encoding='utf-8')
            code,result=self.cli(name,file=file); self.assertEqual(code,0); results[name]=result
        chunks=results['document-chunk-planner']['chunks']; self.assertEqual(len(chunks),3)
        selected=chunks[1]; self.assertEqual((selected['start'],selected['end']),(3,8))
        evidence=dict(format='outlands-answer-evidence-v1',documents=[d],answers=[dict(id='answer-a',text='An invented answer.',
             citations=[dict(source=ref,start=selected['start'],end=selected['end'],quote=body[selected['start']:selected['end']])])])
        file=self.root/'answer.json'; file.write_text(json.dumps(evidence),encoding='utf-8')
        code,result=self.cli('answer-evidence-checker',file=file); self.assertEqual(code,0)
        self.assertEqual(result['evidence'][0]['checked_citations'][0]['quote_sha256'],selected['sha256'])
        self.assertEqual(results['context-manifest-checker']['manifest']['documents'][0]['sha256'],selected['source_sha256'])
        self.assertEqual(results['retrieval-evaluation-calculator']['metrics']['macro_precision_at_k'],dict(numerator='1',denominator='2'))
        self.assertFalse(result['factual_truth_verified'])

    def test_input_failure_omits_path(self):
        for name in TOOLS:
            code,result=self.cli(name,file=self.root/'SYNTHETIC_SENTINEL.json')
            self.assertEqual(code,2); self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))

    def test_reports_omit_document_answer_and_quote_bodies(self):
        for name in TOOLS:
            folder=ROOT/'tools'/name; value=json.loads((folder/'examples/input.json').read_text(encoding='utf-8'))
            _,result=self.cli(name); raw=json.dumps(result)
            for row in value['documents']: self.assertNotIn(row['text'],raw)
            for row in value.get('answers',[]):
                self.assertNotIn(row['text'],raw)
                for citation in row['citations']: self.assertNotIn(citation['quote'],raw)
