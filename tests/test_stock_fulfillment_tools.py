"""Actual independent CLI and connected fictional HVAC stock/fulfillment acceptance."""
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
TOOLS={'stock-movement-ledger-checker':'movements.py','inventory-position-calculator':'position.py',
       'replenishment-proposal-planner':'replenish.py','shipment-coverage-reconciler':'shipments.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-stock-fulfillment-'); self.addCleanup(self.temp.cleanup)
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

    def test_review_examples_retain_diagnostics_without_qualified_scope(self):
        for name in TOOLS:
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json');self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);self.assertIsNone(result['qualified_scope_sha256']);self.assertIsNotNone(result['assessment'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_stock_position_proposal_and_shipment_review(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        ledger_input=example('stock-movement-ledger-checker');ledger=self.run_value('stock-movement-ledger-checker',ledger_input);self.assertEqual(ledger['assessment']['stocks'][0]['closing_quantity'],10)
        position_input=example('inventory-position-calculator');stock=position_input['stocks'][0]
        # Explicit fictional operator adapter: a new selected stock revision, never a stock update.
        stock.update(on_hand=ledger['assessment']['stocks'][0]['closing_quantity'],at=ledger['as_of'])
        for side in ('inbound','reservations'):
            for row in position_input[side]:row['stock_sha256']=sha(encode(stock))
        position=self.run_value('inventory-position-calculator',position_input);self.assertEqual(position['assessment']['stocks'][0]['inventory_position'],8)
        proposal_input=example('replenishment-proposal-planner');selected=proposal_input['positions'][0];selected.update(inventory_position=position['assessment']['stocks'][0]['inventory_position'],as_of=position['as_of']);proposal_input['policies'][0]['position_sha256']=sha(encode(selected))
        proposal=self.run_value('replenishment-proposal-planner',proposal_input);self.assertEqual(proposal['assessment']['positions'][0]['proposed_quantity'],12)
        shipment_input=example('shipment-coverage-reconciler');self.assertEqual(shipment_input['orders'][0]['quantity'],position_input['reservations'][0]['quantity']);shipment=self.run_value('shipment-coverage-reconciler',shipment_input);self.assertEqual(shipment['assessment']['orders'][0]['declared_received_quantity'],4)
        for report in (ledger,position,proposal,shipment):
            for key in ('physical_stock_verified','inbound_eligibility_verified','delivery_verified','stock_updated','purchase_order_created','reservations_changed','shipment_executed','procurement_authorized','target_changes_performed'):self.assertFalse(report[key])

    def test_overdue_inbound_capped_proposal_and_short_receipt_remain_review_required(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/needs-review.json').read_text(encoding='utf-8'))
        position=self.run_value('inventory-position-calculator',example('inventory-position-calculator'),1);self.assertEqual(position['assessment']['stocks'][0]['inventory_position'],6);self.assertFalse(position['assessment']['inbound'][0]['included'])
        proposal_input=example('replenishment-proposal-planner');proposal_input['positions'][0]['inventory_position']=6;proposal_input['policies'][0]['position_sha256']=sha(encode(proposal_input['positions'][0]));proposal=self.run_value('replenishment-proposal-planner',proposal_input,1);self.assertEqual(proposal['assessment']['positions'][0]['required_order_quantity'],18);self.assertIsNone(proposal['assessment']['positions'][0]['proposed_quantity'])
        shipment=self.run_value('shipment-coverage-reconciler',example('shipment-coverage-reconciler'),1);self.assertEqual(shipment['assessment']['orders'][0]['receipt_shortage'],1)
        for report in (position,proposal,shipment):self.assertIsNone(report['qualified_scope_sha256']);self.assertFalse(report['target_changes_performed'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_stock_cli(self):
        name='stock-movement-ledger-checker';code,out=self.cli(name,file=ROOT/'tools'/name/'examples/game-stock.json');self.assertEqual(code,0);self.assertEqual(out['assessment']['stocks'][0]['closing_quantity'],10);self.assertFalse(out['physical_stock_verified'])


    def test_existing_public_material_checker_reviews_the_declared_order_reservation(self):
        position=json.loads((ROOT/'tools/inventory-position-calculator/examples/input.json').read_text(encoding='utf-8'));stock=position['stocks'][0];reserved=position['reservations'][0]
        value=dict(format='outlands-material-allocations-v1',lots=[dict(id='hvac-filter-lot',item_id=stock['item'],unit=stock['unit'],quantity=stock['on_hand'])],aliases=[],demands=[dict(id='hvac-filter-demand',item_id=stock['item'],unit=stock['unit'],quantity=reserved['quantity'])],allocations=[dict(id='hvac-filter-allocation',demand_id='hvac-filter-demand',lot_id='hvac-filter-lot',quantity=reserved['quantity'])])
        file=self.root/'declared-materials.json';file.write_bytes(encode(value));script=ROOT/'tools/material-allocation-checker/allocations.py'
        code,out=self.invoke(script,['--input',file]);self.assertEqual(code,0);self.assertEqual(out['lots'][0]['unreserved'],6);self.assertFalse(out['reservations_changed'])
        value['allocations'][0]['quantity']=11;file.write_bytes(encode(value));code,out=self.invoke(script,['--input',file]);self.assertEqual(code,1);self.assertEqual(out['lots'][0]['excess'],1);self.assertFalse(out['physical_stock_verified'])
