"""Actual independent CLI and connected fictional HVAC material/lot acceptance."""
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
TOOLS={'bom-contract-checker':'bom.py','lot-identity-checker':'identities.py',
       'material-allocation-checker':'allocations.py','handoff-lifecycle-checker':'handoffs.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-hvac-materials-'); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def invoke(self,script,args):
        q=subprocess.run([sys.executable,'-B',str(script),*map(str,args)],capture_output=True,
                         env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(q.stderr,b''); return q.returncode,json.loads(q.stdout)

    def cli(self,name,file=None,extra=(),folder=None):
        folder=folder or ROOT/'tools'/name
        return self.invoke(folder/TOOLS[name],['--input',file or folder/'examples/input.json',*extra])

    def run_value(self,name,value,code=0):
        file=self.root/(name+'.json'); file.write_bytes(encode(value)); actual,result=self.cli(name,file=file)
        self.assertEqual(actual,code); return result

    def test_valid_examples(self):
        for name in TOOLS:
            code,result=self.cli(name); self.assertEqual(code,0); self.assertEqual(result['status'],'PASS')

    def test_independent_source_copies(self):
        for name in TOOLS:
            folder=self.root/name; shutil.copytree(ROOT/'tools'/name,folder,ignore=shutil.ignore_patterns('__pycache__'))
            code,result=self.invoke(folder/'source_check.py',[]); self.assertEqual(code,0); self.assertEqual(result['status'],'SOURCE_MATCH')
            self.assertEqual(self.cli(name,folder=folder)[0],0)

    def test_new_reports_and_overwrite_prevention(self):
        for name in TOOLS:
            out=self.root/(name+'.json'); code,result=self.cli(name,extra=('--out',out))
            self.assertEqual(code,0); self.assertEqual(result,dict(status='PASS',report_written=True))
            raw=out.read_bytes(); self.assertEqual(json.loads(raw),self.cli(name)[1])
            self.assertEqual(self.cli(name,extra=('--out',out))[0],2); self.assertEqual(out.read_bytes(),raw)

    def test_source_tree_output_refusal(self):
        for name in TOOLS:
            out=ROOT/'tools'/name/'fictional-never-created.json'
            self.assertEqual(self.cli(name,extra=('--out',out))[0],2); self.assertFalse(out.exists())

    def test_fixed_argument_and_path_errors(self):
        for name in TOOLS:
            code,result=self.cli(name,extra=('--SYNTHETIC_SENTINEL',)); self.assertEqual(code,2)
            self.assertEqual(result,dict(status='ERROR',code='ARGUMENTS_INVALID'))
            code,result=self.cli(name,file=self.root/'SYNTHETIC_SENTINEL.json')
            self.assertEqual(code,2); self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))

    def test_review_examples_withhold_invalid_cohorts_or_retain_allocation_diagnostics(self):
        for name,key in zip(TOOLS,['requirements','identities','demands','handoffs']):
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues'])
            if name=='material-allocation-checker':self.assertIsNotNone(result[key])
            else:self.assertIsNone(result[key])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_service_kit_cohort(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        bom=self.run_value('bom-contract-checker',example('bom-contract-checker'))
        leaves={r['component_id']:r for r in bom['requirements'] if r['is_leaf']}
        self.assertEqual({k:r['quantity'] for k,r in leaves.items()},{'blower-motor':2,'panel-filter':4})
        inventory=example('lot-identity-checker');identity=self.run_value('lot-identity-checker',inventory)
        resolved={r['id']:r['canonical_lot_id'] for r in identity['identities']}
        self.assertEqual(resolved['service-motor-label'],'motor-lot-a')
        selected=example('material-allocation-checker')
        selected['lots']=inventory['lots'];selected['aliases']=inventory['aliases']
        selected['demands']=[dict(id='demand-'+key,item_id=key,unit=row['unit'],quantity=row['quantity']) for key,row in sorted(leaves.items())]
        selected['allocations']=[dict(id='reserve-'+key,demand_id='demand-'+key,lot_id='service-motor-label' if key=='blower-motor' else 'filter-lot-a',quantity=row['quantity']) for key,row in sorted(leaves.items())]
        allocation=self.run_value('material-allocation-checker',selected)
        self.assertEqual(allocation['lot_contract_sha256'],identity['lot_contract_sha256'])
        self.assertEqual({r['id']:r['unreserved'] for r in allocation['lots']},{'motor-lot-a':2,'filter-lot-a':4})
        # The exercise explicitly chooses a motor reservation and invents receipt assertions.
        reservation=next(r for r in selected['allocations'] if r['id']=='reserve-blower-motor')
        transfer=example('handoff-lifecycle-checker')
        transfer['handoffs'][0].update(lot_id=resolved[reservation['lot_id']],quantity=reservation['quantity'])
        transfer['receipts'][0]['quantity']=reservation['quantity']
        handoff=self.run_value('handoff-lifecycle-checker',transfer)
        self.assertEqual(handoff['accepted_quantity'],2);self.assertEqual(handoff['handoffs'][0]['lot_id'],'motor-lot-a')
        self.assertFalse(handoff['delivery_independently_verified']);self.assertFalse(handoff['inventory_coverage_checked'])

    def test_accepted_receipt_does_not_override_reservation_shortfall(self):
        value=json.loads((ROOT/'tools/material-allocation-checker/examples/input.json').read_text(encoding='utf-8'))
        value['lots'][0]['quantity']=1
        allocation=self.run_value('material-allocation-checker',value,1)
        self.assertIn('LOT_OVERRESERVED',[i['code'] for i in allocation['issues']])
        code,handoff=self.cli('handoff-lifecycle-checker');self.assertEqual(code,0)
        self.assertEqual(handoff['accepted_quantity'],2);self.assertFalse(handoff['inventory_coverage_checked'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])
