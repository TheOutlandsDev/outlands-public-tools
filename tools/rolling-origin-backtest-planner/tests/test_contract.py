from backtests import plan as OP

import copy
import json
from pathlib import Path
import unittest
import toolkit as t
from test_temporal_core import obs,ref

def sample(): return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value): return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_example_passes(self): self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_unknown_fields_and_wrong_format(self):
        for changes in ({'extra':0},{'format':'unsupported'}):
            with self.assertRaises(t.Rejected): run(dict(sample(),**changes))

    def test_ambiguous_json_and_outer_shapes(self):
        for raw in (b'{"format":1,"format":2}',b'NaN',b'1.0',b'"\\ud800"',b'[]',b'null',b'{}'):
            with self.assertRaises(t.Rejected): OP(raw)

    def test_raw_pin_and_input_not_mutated(self):
        value=sample(); before=copy.deepcopy(value); raw=t.encode(value); result=OP(raw)
        self.assertEqual(value,before); self.assertEqual(result['input_sha256'],t.digest(raw))
        self.assertFalse(result['model_trained']); self.assertFalse(result['target_changes_performed'])

    def test_json_round_trip(self):
        result=run(sample()); self.assertEqual(t.decode(t.encode(result)),result)

    def test_known_gapped_capped_multihorizon_folds(self):
        result=run(sample()); folds=result['plan']
        self.assertEqual([row['origin'] for row in folds],[3,4,5])
        self.assertEqual([(row['training_start'],row['training_end'],row['training_points']) for row in folds],[(0,2,3),(0,3,4),(1,4,4)])
        self.assertEqual(folds[-1]['targets'],[dict(horizon=1,period=6),dict(horizon=2,period=7)])
        self.assertEqual(result['counts']['evaluation_pairs'],6)

    def test_expanding_window_and_stride(self):
        value=sample(); value['training']['max_points']=None; value['stride']=2; folds=run(value)['plan']
        self.assertEqual([row['origin'] for row in folds],[3,5]); self.assertEqual(folds[-1]['training_points'],5)

    def test_nonunit_cadence(self):
        value=sample(); value['grid']=dict(start=10,end=24,step=2)
        self.assertEqual(run(value)['plan'][0]['targets'],[dict(horizon=1,period=18),dict(horizon=2,period=20)])

    def test_no_partial_horizon_fold(self):
        value=sample(); value['horizons']=[1,3]; result=run(value)
        self.assertEqual([r['origin'] for r in result['plan']],[3,4])
        self.assertTrue(all(len(r['targets'])==2 for r in result['plan']))

    def test_no_evaluable_fold_requires_review(self):
        value=sample(); value['grid']['end']=2; result=run(value)
        self.assertEqual(result['status'],'REVIEW_REQUIRED'); self.assertIsNone(result['plan'])

    def test_zero_gap_and_minimum_history(self):
        value=sample(); value.update(grid=dict(start=0,end=2,step=1),training=dict(min_points=1,max_points=1,gap_points=0),horizons=[1])
        folds=run(value)['plan']; self.assertEqual([r['training_points'] for r in folds],[1,1]); self.assertEqual([r['origin'] for r in folds],[0,1])

    def test_invalid_training_and_horizon_policies(self):
        for changes in ({'horizons':[1,1]},{'horizons':[True]},{'horizons':[0]},{'stride':0}):
            with self.assertRaises(t.Rejected): run(dict(sample(),**changes))
        for changes in ({'min_points':True},{'max_points':2},{'gap_points':-1}):
            value=sample(); value['training'].update(changes)
            with self.assertRaises(t.Rejected): run(value)

    def test_global_evaluation_pair_budget(self):
        value=sample(); value.update(grid=dict(start=0,end=999,step=1),training=dict(min_points=1,max_points=None,gap_points=0),horizons=list(range(1,17)))
        with self.assertRaisesRegex(t.Rejected,'EVALUATION_PAIR_LIMIT'): run(value)

    def test_horizon_order_canonicalized_and_no_training(self):
        value=sample(); before=run(value); value['horizons'].reverse(); result=run(value)
        self.assertEqual(result['plan'],before['plan']); self.assertFalse(result['forecasts_generated']); self.assertFalse(result['observations_verified'])

    def test_grid_end_and_training_exclusion_boundaries(self):
        result=run(sample())
        for fold in result['plan']:
            self.assertEqual(fold['origin']-fold['training_end'],1)
            self.assertTrue(all(t['period']<=7 and t['period']>fold['origin'] for t in fold['targets']))
