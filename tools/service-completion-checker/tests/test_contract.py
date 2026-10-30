from completion import check as OP

import copy
import json
from pathlib import Path
import unittest
import toolkit as t
import service_core as c

def sample():return json.loads((Path(__file__).parent.parent/'examples/input.json').read_text(encoding='utf-8'))
def run(value):return OP(t.encode(value))

class Contracts(unittest.TestCase):
    def test_hvac_example_passes(self):self.assertEqual(run(sample())['status'],'PASS')

    def test_review_example(self):
        value=json.loads((Path(__file__).parent.parent/'examples/needs-review.json').read_text(encoding='utf-8'))
        self.assertEqual(run(value)['status'],'REVIEW_REQUIRED')

    def test_wrong_format_and_unknown_fields(self):
        for change in ({'format':'unsupported'},{'extra':0}):
            with self.assertRaises(t.Rejected):run(dict(sample(),**change))

    def test_strict_json_and_outer_shapes(self):
        for raw in (b'null',b'[]',b'{}',b'NaN',b'1.0',b'"\\ud800"',b'{"format":1,"format":2}'):
            with self.assertRaises(t.Rejected):OP(raw)

    def test_input_pin_no_mutation_or_authorization(self):
        value=sample();before=copy.deepcopy(value);raw=t.encode(value);result=OP(raw)
        self.assertEqual(value,before);self.assertEqual(result['input_sha256'],t.digest(raw));self.assertFalse(result['execution_authorized']);self.assertFalse(result['target_changes_performed'])

    def test_report_round_trip(self):
        result=run(sample());self.assertEqual(t.decode(t.encode(result)),result)

    def test_known_completed_contract_and_balanced_filter_return(self):
        result=run(sample());row=result['assessments'][0]
        self.assertTrue(row['completed_under_contract']);self.assertFalse(row['reasons']);self.assertFalse(result['physical_service_verified']);self.assertFalse(result['evidence_bytes_verified']);self.assertFalse(result['lifecycle_recomputed'])

    def test_missing_tasks_evidence_and_part_records_retain_diagnostics(self):
        for key,field in [('tasks','missing_tasks'),('evidence','missing_evidence'),('parts','missing_parts')]:
            value=sample();value[key]=[];result=run(value)
            self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['assessments'][0][field])

    def test_unfinished_tasks_or_open_order_are_not_completion(self):
        value=sample();value['tasks'][0]['outcome']='blocked';self.assertTrue(run(value)['assessments'][0]['unfinished_tasks'])
        value=sample();value['orders'][0]['state']='open';value['contracts'][0]['order_sha256']=c.order_pin(value['orders'][0])
        self.assertIn('ORDER_NOT_COMPLETED',run(value)['assessments'][0]['reasons'])

    def test_parts_conservation_and_installed_quantity_are_distinct_checks(self):
        value=sample();value['parts'][0]['returned']=0;codes=[r['code'] for r in run(value)['assessments'][0]['parts_findings']]
        self.assertEqual(codes,['PARTS_NOT_BALANCED'])
        value=sample();value['parts'][0].update(installed=0,returned=2);codes=[r['code'] for r in run(value)['assessments'][0]['parts_findings']]
        self.assertEqual(codes,['INSTALLED_QUANTITY_MISMATCH'])

    def test_exact_revision_and_snapshot_pin_are_both_required(self):
        for change in ({'order_revision':4},{'order_sha256':'0'*64}):
            value=sample();value['contracts'][0].update(change);self.assertIsNone(run(value)['assessments'])
        value=sample();value['orders'][0]['asset_id']='different-asset';self.assertIsNone(run(value)['assessments'])

    def test_other_records_must_match_revision_and_declared_requirements(self):
        for key in ('tasks','parts','evidence'):
            value=sample();value[key][0]['order_revision']=4;self.assertIsNone(run(value)['assessments'])
        for key,field in [('tasks','task_id'),('parts','item_id'),('evidence','kind')]:
            value=sample();value[key][0][field]='undeclared';self.assertIsNone(run(value)['assessments'])

    def test_extra_ids_for_one_requirement_are_ambiguous(self):
        for key in ('contracts','tasks','parts','evidence'):
            value=sample();value[key].append(dict(value[key][0],id='another-id'));self.assertIsNone(run(value)['assessments'])

    def test_exact_duplicates_count_once_conflicts_withhold(self):
        value=sample();before=run(value)
        for key in ('orders','contracts','tasks','parts','evidence'):value[key]*=2
        self.assertEqual(run(value)['assessments'],before['assessments'])
        value['tasks'].append(dict(value['tasks'][0],outcome='not_done'));self.assertIsNone(run(value)['assessments'])

    def test_contract_list_order_normalization(self):
        value=sample();before=run(value);value['contracts'][0]['required_tasks'].reverse()
        value['contracts'].append(dict(sample()['contracts'][0]));self.assertEqual(run(value)['assessments'],before['assessments'])

    def test_missing_contract_or_orphans_never_qualify_partial_subset(self):
        value=sample();value['contracts']=[];self.assertIsNone(run(value)['assessments'])
        value=sample();value['evidence'][0]['order_id']='missing';self.assertIsNone(run(value)['assessments'])
        value=sample();value['orders'].append(dict(value['orders'][0],id='uncovered'));self.assertIsNone(run(value)['assessments'])

    def test_invalid_quantities_unit_and_declared_hash(self):
        for change in ({'issued':True},{'returned':-1},{'unit':'other'}):
            value=sample();value['parts'][0].update(change);self.assertIsNone(run(value)['assessments'])
        value=sample();value['evidence'][0]['sha256']='invalid';self.assertIsNone(run(value)['assessments'])

    def test_empty_declared_requirements_do_not_imply_physical_work(self):
        value=sample();value['contracts'][0].update(required_tasks=[],required_evidence=[],expected_parts=[]);value.update(tasks=[],parts=[],evidence=[])
        result=run(value);self.assertEqual(result['status'],'PASS');self.assertFalse(result['physical_service_verified'])

    def test_duplicate_expected_item_or_tag_is_invalid(self):
        for key in ('required_tasks','required_evidence','expected_parts'):
            value=sample();value['contracts'][0][key]*=2;self.assertIsNone(run(value)['assessments'])

    def test_large_exact_balanced_quantities(self):
        value=sample();value['contracts'][0]['expected_parts'][0]['installed_quantity']=10**12
        value['parts'][0].update(issued=10**12,installed=10**12,returned=0,scrapped=0)
        self.assertEqual(run(value)['status'],'PASS')

    def test_total_requirement_budget_refuses_before_output(self):
        value=sample();template=value['contracts'][0]
        template.update(required_tasks=['task-'+str(i) for i in range(32)],required_evidence=['kind-'+str(i) for i in range(32)],expected_parts=[dict(item_id='item-'+str(i),unit='pieces',installed_quantity=0) for i in range(32)])
        value['contracts']=[dict(template,id='contract-'+str(i)) for i in range(105)]
        with self.assertRaisesRegex(t.Rejected,'COMPLETION_REQUIREMENT_LIMIT'):run(value)
