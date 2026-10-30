import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import acks as app
import worker_core as r

def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(value):return hashlib.sha256(encode(value)).hexdigest()
def at(value,path):
    for key in path:value=value[key]
    return value

class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,value=None):return app.check(encode(self.value if value is None else value))
    def review(self,value=None):
        out=self.run_value(value);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertTrue(out['issues']);self.assertIsNone(out['qualified_scope_sha256']);return out
    def withheld(self,value=None):
        out=self.review(value);self.assertIsNone(out['assessment'])
        for key in ['items_sha256', 'lease_events_sha256', 'deliveries_sha256', 'acknowledgements_sha256', 'as_of_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('payloads_opened','handler_executed','artifact_bytes_verified','worker_contacted','ownership_enforced','jobs_executed','queue_changed','records_changed','results_committed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['items'], ['lease_events'], ['deliveries'], ['acknowledgements']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['items_sha256', 'lease_events_sha256', 'deliveries_sha256', 'acknowledgements_sha256', 'as_of_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['items'], ['lease_events'], ['deliveries'], ['acknowledgements']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['items'], ['lease_events'], ['deliveries'], ['acknowledgements']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['items'], ['lease_events'], ['deliveries'], ['acknowledgements']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['items'], ['lease_events'], ['deliveries'], ['acknowledgements']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['items'], ['lease_events'], ['deliveries'], ['acknowledgements']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['items'], ['lease_events'], ['deliveries'], ['acknowledgements']][0]).clear();self.withheld(value)

    def repin(self):self.value['acknowledgements'][0]['delivery_sha256']=pin(self.value['deliveries'][0])
    def test_known_selected_delivery_and_acknowledgement(self):
        out=self.run_value();self.assertEqual(out['assessment']['items'][0]['single_consistent_acknowledged_delivery'],'delivery-current');self.assertTrue(out['assessment']['items'][0]['all_deliveries_accounted']);self.assertFalse(out['assessment']['broker_delivery_verified'])
    def test_missing_ack_and_missing_delivery_are_not_success(self):
        self.value['acknowledgements']=[];out=self.review();self.assertIn('ACK_MISSING',out['assessment']['deliveries'][0]['failed_criteria']);self.assertIsNone(out['assessment']['items'][0]['single_consistent_acknowledged_delivery'])
        self.value['deliveries']=[];self.assertEqual(self.review()['assessment']['items'][0]['delivery_count'],0)
    def test_requeued_and_dead_lettered_are_distinct_from_acknowledged(self):
        for state in ('requeued','dead_lettered'):
            self.value['acknowledgements'][0]['state']=state;row=self.review()['assessment']['deliveries'][0];self.assertTrue(row['acknowledgement_consistent']);self.assertEqual(row['declared_state'],state)
    def test_delivery_and_acknowledgement_use_exclusive_lease_end(self):
        self.value['acknowledgements'][0]['at']=50;out=self.review();self.assertIn('ACK_OWNER_NOT_ACTIVE',out['assessment']['deliveries'][0]['failed_criteria'])
        self.value['deliveries'][0]['at']=50;self.repin();out=self.review();self.assertIn('DELIVERY_OWNER_NOT_ACTIVE',out['assessment']['deliveries'][0]['failed_criteria'])
    def test_late_old_owner_ack_is_rejected_after_expiry_and_takeover(self):
        self.value['deliveries'][0].update(at=12,worker='worker-alpha',token=1);self.repin();self.value['acknowledgements'][0].update(at=25,worker='worker-alpha',token=1);out=self.review();self.assertTrue(out['assessment']['deliveries'][0]['delivery_consistent']);self.assertFalse(out['assessment']['deliveries'][0]['acknowledgement_consistent'])
    def test_redelivery_after_expiry_can_be_current_without_erasing_old_gap(self):
        current=self.value['deliveries'][0];current['ordinal']=2;self.repin();old=dict(current,id='delivery-old',ordinal=1,at=12,worker='worker-alpha',token=1);self.value['deliveries'].append(old);out=self.review();self.assertEqual(out['assessment']['items'][0]['single_consistent_acknowledged_delivery'],'delivery-current');self.assertFalse(out['assessment']['items'][0]['all_deliveries_accounted'])
    def test_unresolved_active_delivery_and_delivery_after_terminal_are_findings(self):
        old=self.value['deliveries'][0];self.value['deliveries'].append(dict(old,id='next-delivery',ordinal=2,at=25));out=self.review();self.assertIn('PRIOR_DELIVERY_UNRESOLVED',out['assessment']['deliveries'][1]['failed_criteria'])
        self.value['deliveries'][1]['at']=37;out=self.review();self.assertIn('DELIVERY_AFTER_TERMINAL_OUTCOME',out['assessment']['deliveries'][1]['failed_criteria'])
    def test_explicit_requeue_before_next_delivery_is_supported(self):
        first=self.value['deliveries'][0];first['at']=22;self.value['acknowledgements'][0].update(at=24,state='requeued');second=dict(first,id='second-delivery',ordinal=2,at=25);self.value['deliveries'].append(second);self.value['acknowledgements'].append(dict(self.value['acknowledgements'][0],id='second-ack',delivery=second['id'],delivery_sha256=pin(second),at=26,state='acknowledged'));self.assertEqual(self.run_value()['status'],'PASS')
    def test_unknown_stale_or_aliased_ack_binding_withholds(self):
        for change in ({'delivery':'other'},{'delivery_sha256':'0'*64},{'at':21}):
            value=copy.deepcopy(self.value);value['acknowledgements'][0].update(change);self.withheld(value)
        self.value['acknowledgements'].append(dict(self.value['acknowledgements'][0],id='alias'));self.withheld()
    def test_ack_cannot_switch_worker_or_token_even_when_other_owner_is_live(self):
        self.value['deliveries'][0].update(at=12,worker='worker-alpha',token=1);self.repin();out=self.review();self.assertIn('ACK_DELIVERY_OWNER_MISMATCH',out['assessment']['deliveries'][0]['failed_criteria'])
    def test_future_claims_are_not_counted_as_acknowledged(self):
        self.value['deliveries'][0]['at']=41;self.repin();self.value['acknowledgements'][0]['at']=42;out=self.review();self.assertIsNone(out['assessment']['items'][0]['single_consistent_acknowledged_delivery']);self.assertIn('DELIVERY_AFTER_AS_OF',out['assessment']['deliveries'][0]['failed_criteria'])
    def test_invalid_or_incomplete_lease_scope_withholds_all_ack_assessment(self):
        for events in ([],[dict(self.value['lease_events'][0],until=15),dict(self.value['lease_events'][1],at=14)]):
            value=copy.deepcopy(self.value);value['lease_events']=events;self.withheld(value)
