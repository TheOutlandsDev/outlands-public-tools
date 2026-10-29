from observations import resolve as OP

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

    def test_known_asof_revision_selection(self):
        result=run(sample()); self.assertEqual([r['observation']['revision'] for r in result['resolutions']],[1,2])
        self.assertEqual([r['as_of'] for r in result['resolutions']],[2,3])

    def test_cutoff_inclusive(self):
        value=sample(); value['requests'][0]['as_of']=3
        self.assertTrue(all(row['observation']['revision']==2 for row in run(value)['resolutions']))

    def test_delayed_observation_missing_at_cutoff(self):
        value=sample(); value['observations']=[obs(1,available_at=3)]; value['requests']=value['requests'][:1]
        result=run(value); self.assertIsNone(result['resolutions']); self.assertIn('OBSERVATION_UNAVAILABLE_AT_CUTOFF',[i['code'] for i in result['issues']])

    def test_duplicate_snapshots_count_once(self):
        value=sample(); before=run(value); value['observations']*=2; value['requests']*=2; result=run(value)
        self.assertEqual(result['resolutions'],before['resolutions']); self.assertEqual(result['counts']['requests']['duplicate_rows'],2)

    def test_conflicting_versions_withhold_entire_cohort(self):
        value=sample(); value['observations'].append(obs(1,value='999'))
        result=run(value); self.assertIsNone(result['resolutions']); self.assertEqual(result['counts']['observations']['conflict_rows'],2)

    def test_revision_time_tie_and_reversal_block_globally(self):
        for available in (1,0):
            value=sample(); value['observations']=[obs(0,1,1),obs(0,2,available)]
            self.assertIsNone(run(value)['resolutions'])

    def test_id_alias_and_invalid_future_observation_block(self):
        value=sample(); value['observations'].append(obs(9,id=value['observations'][0]['id']))
        self.assertIsNone(run(value)['resolutions'])
        value=sample(); value['observations'].append(dict(obs(9),sha256='0'*64))
        self.assertIsNone(run(value)['resolutions'])

    def test_invalid_or_conflicting_requests(self):
        value=sample(); value['requests'].append(dict(value['requests'][0],as_of=3))
        self.assertEqual(run(value)['counts']['requests']['conflict_rows'],2)
        value=sample(); value['requests'][0]['as_of']=0; self.assertIsNone(run(value)['resolutions'])

    def test_empty_request_cohort_review(self):
        value=sample(); value['requests']=[]; self.assertIsNone(run(value)['resolutions'])

    def test_order_invariance_and_no_value_emission(self):
        value=sample(); before=run(value); value['observations'].reverse(); value['requests'].reverse(); result=run(value)
        self.assertEqual(result['resolutions'],before['resolutions'])
        self.assertNotIn('value',result['resolutions'][0]['observation']); self.assertFalse(result['observation_values_emitted'])
