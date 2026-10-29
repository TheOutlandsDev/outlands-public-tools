"""Actual independent CLIs and connected synthetic provenance/plan acceptance."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
TOOLS={'run-artifact-manifest-builder':'artifacts.py','ingestion-receipt-reconciler':'receipts.py',
       'run-provenance-checker':'provenance.py','publication-plan-checker':'publication.py'}


def enc(value):
    return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode('ascii')+b'\n'


def pin(raw): return hashlib.sha256(raw).hexdigest()


class Walkthrough(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='fictional-provenance-tools-')
        self.addCleanup(temp.cleanup); self.private=Path(temp.name)

    def call(self,root,script,args,code=0):
        result=subprocess.run([sys.executable,'-B',str(root/script),*map(str,args)],cwd=self.private,
                              capture_output=True,timeout=30)
        self.assertEqual(result.returncode,code,result.stdout.decode('utf-8',errors='replace'))
        self.assertEqual(result.stderr,b''); return json.loads(result.stdout)

    def args(self,name,root):
        examples=root/'examples'
        if name=='ingestion-receipt-reconciler':
            return ['--receipt',examples/'receipt.json','--source',examples/'source.txt',
                    '--mapping',examples/'mapping.json','--preview',examples/'preview.json']
        if name=='publication-plan-checker':
            args=['--plan',examples/'plan.json','--manifest',examples/'manifest.json','--review',examples/'review.json']
            keys=['reconciliation','result']
        else:
            if name=='run-artifact-manifest-builder':
                args=['--selection',examples/'selection.json']
            else:
                args=['--contract',examples/'provenance.json','--manifest',examples/'manifest.json',
                      '--snapshot',examples/'snapshot.json','--policy',examples/'snapshot-policy.json']
            keys=['code','configuration','mapping','preview','receipt','reconciliation','result','schema','source']
        for key in keys:
            args+=['--item',key,examples/(key+('.txt' if key in ('source','code') else '.json'))]
        return args

    def test_all_fictional_cli_examples(self):
        for name,script in TOOLS.items():
            root=ROOT/'tools'/name
            with self.subTest(tool=name): self.assertEqual(self.call(root,script,self.args(name,root))['status'],'PASS')

    def test_each_copied_tool_is_independent_and_source_pinned(self):
        for name,script in TOOLS.items():
            root=self.private/name
            shutil.copytree(ROOT/'tools'/name,root,ignore=shutil.ignore_patterns('__pycache__'))
            with self.subTest(tool=name):
                self.assertEqual(self.call(root,script,self.args(name,root))['status'],'PASS')
                self.assertEqual(self.call(root,'source_check.py',[])['status'],'SOURCE_MATCH')

    def test_each_new_report_and_overwrite_refusal(self):
        for name,script in TOOLS.items():
            root=ROOT/'tools'/name; target=self.private/(name+'.json')
            args=self.args(name,root)+['--out',target]
            self.assertTrue(self.call(root,script,args)['report_written']); original=target.read_bytes()
            self.assertEqual(self.call(root,script,args,2)['status'],'ERROR'); self.assertEqual(target.read_bytes(),original)

    def test_argument_errors_do_not_echo_supplied_values(self):
        for name,script in TOOLS.items():
            self.assertEqual(self.call(ROOT/'tools'/name,script,['--unknown','FICTIONAL_SENTINEL'],2),
                             dict(status='ERROR',code='ARGUMENTS_INVALID'))

    def test_connected_four_tool_flow_and_exact_pins(self):
        builder=ROOT/'tools/run-artifact-manifest-builder'; intake=ROOT/'tools/ingestion-receipt-reconciler'
        lineage=ROOT/'tools/run-provenance-checker'; publication=ROOT/'tools/publication-plan-checker'
        built=self.call(builder,'artifacts.py',self.args('run-artifact-manifest-builder',builder))
        raw=enc(built['manifest']); self.assertEqual(built['manifest_sha256'],pin(raw))
        manifest=self.private/'manifest.json'; manifest.write_bytes(raw)
        reconciled=self.call(intake,'receipts.py',self.args('ingestion-receipt-reconciler',intake))
        self.assertTrue(reconciled['row_counts_recomputed']); self.assertTrue(reconciled['ready_for_explicit_review'])
        report=self.private/'reconciliation.json'; report.write_bytes(enc(reconciled))
        args=self.args('run-provenance-checker',lineage)
        args[args.index('--manifest')+1]=manifest
        for index,item in enumerate(args):
            if item=='reconciliation': args[index+1]=report
        result=self.call(lineage,'provenance.py',args)
        self.assertEqual(result['manifest_sha256'],built['manifest_sha256'])
        self.assertFalse(result['execution_verified']); self.assertFalse(result['record_counts_independently_verified'])
        args=self.args('publication-plan-checker',publication); args[args.index('--manifest')+1]=manifest
        for index,item in enumerate(args):
            if item=='reconciliation': args[index+1]=report
        before={p.name:pin(p.read_bytes()) for p in self.private.iterdir() if p.is_file()}
        result=self.call(publication,'publication.py',args)
        self.assertFalse(result['publication_authorized']); self.assertFalse(result['target_changes_performed'])
        self.assertEqual(before,{p.name:pin(p.read_bytes()) for p in self.private.iterdir() if p.is_file()})
        self.assertFalse((self.private/'sample-result.json').exists())

    def test_changed_source_withholds_receipt_readiness(self):
        root=ROOT/'tools/ingestion-receipt-reconciler'; args=self.args('ingestion-receipt-reconciler',root)
        source=self.private/'changed-source.txt'; source.write_bytes((root/'examples/source.txt').read_bytes()+b'sample-gamma,1\n')
        args[args.index('--source')+1]=source; result=self.call(root,'receipts.py',args,1)
        self.assertFalse(result['ready_for_explicit_review']); self.assertIn('RECEIPT_COUNT_MISMATCH',result['issues'])

    def test_held_review_is_retained_even_with_fresh_pin(self):
        root=ROOT/'tools/publication-plan-checker'; value=json.loads((root/'examples/review.json').read_text(encoding='utf-8'))
        value['items'][0]['decision']='hold'; review=self.private/'held-review.json'; review.write_bytes(enc(value))
        value=json.loads((root/'examples/plan.json').read_text(encoding='utf-8')); value['review_sha256']=pin(review.read_bytes())
        plan=self.private/'plan.json'; plan.write_bytes(enc(value)); args=self.args('publication-plan-checker',root)
        args[args.index('--plan')+1]=plan; args[args.index('--review')+1]=review
        result=self.call(root,'publication.py',args,1)
        self.assertIn('REVIEW_HELD',{r['code'] for r in result['issues']}); self.assertFalse(result['publication_authorized'])

    def test_unselected_file_binding_refused_before_read(self):
        root=ROOT/'tools/publication-plan-checker'; args=self.args('publication-plan-checker',root)
        args+=['--item','source',self.private/'must-not-be-read.txt']
        self.assertEqual(self.call(root,'publication.py',args,2),dict(status='ERROR',code='BINDING_COVERAGE_INVALID'))

    def test_actual_generated_xlsx_receipt_cli(self):
        root=ROOT/'tools/ingestion-receipt-reconciler'; source=self.private/'fictional.xlsx'
        self.call(root,'fictional_workbook.py',['--out',source])
        mapping=json.loads((root/'examples/mapping.json').read_text(encoding='utf-8'))
        mapping['fields'] += [dict(source='Due',target='due',type='date',required=True),
                              dict(source='Active',target='active',type='boolean',required=True)]
        selected_map=self.private/'mapping.json'; selected_map.write_bytes(enc(mapping))
        preview=self.call(root,'intake.py',['--input',source,'--mapping',selected_map,'--format','xlsx','--sheet','Records'])
        selected_preview=self.private/'preview.json'; selected_preview.write_bytes(enc(preview))
        receipt=dict(format='outlands-ingestion-receipt-v1',receipt_id='fictional-xlsx',source_format='xlsx',sheet='Records',
                     source_sha256=pin(source.read_bytes()),mapping_sha256=pin(selected_map.read_bytes()),
                     preview_sha256=pin(selected_preview.read_bytes()),counts=preview['counts'])
        selected_receipt=self.private/'receipt.json'; selected_receipt.write_bytes(enc(receipt))
        result=self.call(root,'receipts.py',['--receipt',selected_receipt,'--source',source,'--mapping',selected_map,'--preview',selected_preview])
        self.assertEqual(result['observed_counts']['duplicate_rows'],1); self.assertTrue(result['row_counts_recomputed'])

    def test_source_tree_reports_refused_without_creation(self):
        for name,script in TOOLS.items():
            root=ROOT/'tools'/name; target=root/'FICTIONAL-MUST-NOT-BE-CREATED.json'
            self.assertFalse(target.exists())
            self.assertEqual(self.call(root,script,self.args(name,root)+['--out',target],2)['status'],'ERROR')
            self.assertFalse(target.exists())
