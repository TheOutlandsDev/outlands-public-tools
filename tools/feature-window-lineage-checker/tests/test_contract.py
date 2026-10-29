from features import check as OP

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

    def test_known_complete_windows_and_selected_revision(self):
        result=run(sample()); a,b=result['lineage']
        self.assertEqual((a['start'],a['end']),(1,2)); self.assertEqual([r['revision'] for r in a['contributors']],[2,1])
        self.assertEqual((b['start'],b['end']),(0,1)); self.assertFalse(result['feature_values_calculated'])

    def test_stale_pinned_revision_withholds_all(self):
        value=sample(); value['features'][0]['contributors'][0]=ref(value['observations'][1])
        result=run(value); self.assertIsNone(result['lineage']); self.assertIn('STALE_OBSERVATION_REVISION',[i['code'] for i in result['issues']])

    def test_source_after_origin_and_future_period_rejected(self):
        value=sample(); delayed=obs(2,available_at=4); value['observations'][2]=delayed; value['features'][0]['contributors'][1]=ref(delayed)
        self.assertIsNone(run(value)['lineage'])
        value=sample(); future=obs(4); value['observations'].append(future); value['features'][0]['contributors'][1]=ref(future)
        self.assertIn('CONTRIBUTOR_OUTSIDE_WINDOW',[i['code'] for i in run(value)['issues']])

    def test_missing_coverage_and_unknown_reference(self):
        value=sample(); value['features'][0]['contributors'].pop(); self.assertIsNone(run(value)['lineage'])
        value=sample(); value['features'][0]['contributors'][0]['id']='missing'; self.assertIsNone(run(value)['lineage'])

    def test_reference_pin_and_series_mismatch(self):
        value=sample(); value['features'][0]['contributors'][0]['sha256']='0'*64; self.assertIsNone(run(value)['lineage'])
        value=sample(); other=obs(1,series='other',id='other'); value['observations'].append(other); value['features'][0]['contributors'][0]=ref(other)
        self.assertIsNone(run(value)['lineage'])

    def test_duplicate_reference_and_conflicting_feature(self):
        value=sample(); value['features'][0]['contributors']*=2
        self.assertEqual(run(value)['counts']['features']['rejected_rows'],1)
        value=sample(); value['features'].append(dict(value['features'][0],target=5)); self.assertEqual(run(value)['counts']['features']['conflict_rows'],2)

    def test_identical_features_and_reordered_refs_count_once(self):
        value=sample(); before=run(value); changed=copy.deepcopy(value['features'][0]); changed['contributors'].reverse(); value['features'].append(changed)
        result=run(value); self.assertEqual(result['lineage'],before['lineage']); self.assertEqual(result['counts']['features']['duplicate_rows'],1)

    def test_invalid_target_window_and_types(self):
        for changes in ({'target':3},{'step':True},{'window_points':0},{'lag_points':4},{'target':999999999}):
            value=sample(); value['features'][0].update(changes); self.assertIsNone(run(value)['lineage'])

    def test_zero_lag_inclusive_origin_requires_known_observation(self):
        source=obs(3); value=sample(); value['observations']=[source]; value['features']=[dict(id='current',series='sample',origin=3,target=4,step=1,lag_points=0,window_points=1,contributors=[ref(source)])]
        self.assertEqual(run(value)['status'],'PASS')
        source=obs(3,available_at=4); value['observations']=[source]; value['features'][0]['contributors']=[ref(source)]
        self.assertIsNone(run(value)['lineage'])

    def test_empty_features_and_bad_observation_withhold(self):
        value=sample(); value['features']=[]; self.assertIsNone(run(value)['lineage'])
        value=sample(); value['observations'].append(None); self.assertIsNone(run(value)['lineage'])

    def test_total_window_budget(self):
        value=sample(); value['features']=[dict(id='window-'+str(i),series='sample',origin=2000,target=2001,step=1,lag_points=1,window_points=1000,contributors=[]) for i in range(5)]
        with self.assertRaisesRegex(t.Rejected,'TOTAL_FEATURE_WINDOW_LIMIT'): run(value)

    def test_order_invariance_and_value_omission(self):
        value=sample(); before=run(value); value['observations'].reverse(); value['features'].reverse(); result=run(value)
        self.assertEqual(result['lineage'],before['lineage']); self.assertTrue(all('value' not in s for row in result['lineage'] for s in row['contributors']))
