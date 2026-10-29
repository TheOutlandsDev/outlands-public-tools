from grids import check as OP

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

    def test_known_complete_coverage(self):
        result=run(sample()); self.assertEqual(result['coverage'],[dict(series='sample',expected_points=6,observed_unique_points=6,missing_periods=[],outside_unique_points=0)])
        self.assertTrue(result['coverage_complete']); self.assertFalse(result['observations_filled'])

    def test_missing_periods_and_duplicates_are_visible(self):
        value=sample(); value['points'][2]=dict(series='sample',period=1); result=run(value)
        self.assertEqual(result['coverage'][0]['missing_periods'],[2]); self.assertEqual(result['counts']['points']['duplicate_rows'],1)
        self.assertEqual({i['code'] for i in result['issues']},{'DUPLICATE_PERIOD','GRID_GAPS'})

    def test_offgrid_and_outside_window(self):
        value=sample(); value['grids'][0].update(start=0,end=6,step=2)
        result=run(value); self.assertEqual(result['coverage'][0]['missing_periods'],[6]); self.assertEqual(result['coverage'][0]['outside_unique_points'],3)

    def test_undeclared_series_not_silently_dropped(self):
        value=sample(); value['points'].append(dict(series='unknown',period=1))
        result=run(value); self.assertFalse(result['coverage_complete']); self.assertIn('SERIES_UNDECLARED',[i['code'] for i in result['issues']])

    def test_malformed_point_withholds_coverage(self):
        value=sample(); value['points'].append(dict(series='sample',period=True))
        result=run(value); self.assertIsNone(result['coverage']); self.assertEqual(result['counts']['points']['rejected_rows'],1)

    def test_empty_points_reports_all_gaps(self):
        value=sample(); value['points']=[]; self.assertEqual(run(value)['coverage'][0]['missing_periods'],list(range(6)))

    def test_multiple_series_and_order_invariance(self):
        value=sample(); value['grids'].append(dict(series='other',start=10,end=14,step=2))
        value['points'] += [dict(series='other',period=p) for p in (10,12,14)]; before=run(value)
        value['grids'].reverse(); value['points'].reverse(); self.assertEqual(run(value)['coverage'],before['coverage'])

    def test_policy_duplicates_and_aggregate_grid_limit(self):
        value=sample(); value['grids']*=2
        with self.assertRaises(t.Rejected): run(value)
        value=sample(); value['grids']=[dict(series=s,start=0,end=500,step=1) for s in ('a','b')]
        with self.assertRaisesRegex(t.Rejected,'TOTAL_GRID_POINT_LIMIT'): run(value)

    def test_single_point_boundary(self):
        value=sample(); value['grids']=[dict(series='sample',start=10**9,end=10**9,step=1)]; value['points']=[dict(series='sample',period=10**9)]
        self.assertEqual(run(value)['status'],'PASS')
