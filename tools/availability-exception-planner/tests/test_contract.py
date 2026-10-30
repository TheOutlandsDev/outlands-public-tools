import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import availability as app
import schedule_core as r

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
        for key in ['calendars_sha256', 'closures_sha256']:self.assertIsNone(out[key])
        return out
    def test_positive_authority_and_execution_boundaries(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('actual_availability_verified','actual_task_durations_verified','capacity_checked','optimality_proven','calendar_updated','schedule_executed','dispatch_authorized','records_changed','content_privacy_verified','execution_authorized','target_changes_performed'):self.assertIs(out[key],False)
    def test_outer_schema_format_and_duplicate_keys_refuse(self):
        for value in ({},dict(self.value,extra=0),dict(self.value,format='other')):
            with self.assertRaises(t.Rejected):self.run_value(value)
        with self.assertRaises(t.Rejected):app.check(b'{"format":0,"format":1}')
    def test_identity_list_order_preserves_scope_pins(self):
        before=self.run_value()
        for path in [['calendars'], ['closures']]:at(self.value,path).reverse()
        after=self.run_value()
        for key in ['calendars_sha256', 'closures_sha256']:self.assertEqual(before[key],after[key])
    def test_duplicate_rows_count_once_and_keep_all_accounting(self):
        for path in [['calendars'], ['closures']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            rows.append(copy.deepcopy(rows[0]));out=self.run_value(value);self.assertEqual(out['status'],'PASS');side='_'.join(path);counts=out['counts'][side]
            self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_groups_exclude_every_member(self):
        for path in [['calendars'], ['closures']]:
            value=copy.deepcopy(self.value);rows=at(value,path)
            if not rows:continue
            row=copy.deepcopy(rows[0]);field=next(k for k,v in row.items() if k!='id' and isinstance(v,(str,int)) and v is not None)
            row[field]=row[field]+1 if type(row[field]) is int else ('0'*64 if field.endswith('sha256') else 'other-declared-id')
            rows.extend([row,copy.deepcopy(rows[0])]);out=self.withheld(value);self.assertEqual(out['counts']['_'.join(path)]['conflict_rows'],3)
    def test_bad_rows_withhold_without_echoing_values(self):
        for path in [['calendars'], ['closures']]:
            value=copy.deepcopy(self.value);at(value,path).append({'id':'SYNTHETIC_SENTINEL'});out=self.withheld(value);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(out))
    def test_nonlist_or_oversized_lists_are_fixed_refusals(self):
        for path in [['calendars'], ['closures']]:
            for bad in (None,{},[{}]*1001):
                value=copy.deepcopy(self.value);at(value,path[:-1])[path[-1]]=bad
                with self.assertRaises(t.Rejected):self.run_value(value)
    def test_unknown_row_fields_and_nonobjects_are_rejected(self):
        for path in [['calendars'], ['closures']]:
            value=copy.deepcopy(self.value);at(value,path).append(None);self.withheld(value)
            value=copy.deepcopy(self.value);at(value,path)[0]['extra']=0;self.withheld(value)
    def test_raw_input_hash_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw))
        spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_empty_required_cases_never_passes_vacuously(self):
        value=copy.deepcopy(self.value);at(value,[['calendars'], ['closures']][0]).clear();self.withheld(value)

    def test_known_subtraction_and_conservation(self):
        row=self.run_value()['assessment']['calendars'][0];self.assertEqual(row['available_windows'],[dict(start=0,end=12),dict(start=15,end=30)]);self.assertEqual((row['original_units'],row['removed_units'],row['remaining_units']),(30,3,27))
    def test_overlapping_closures_remove_union_only_once(self):
        self.value['closures'].append(dict(self.value['closures'][0],id='other-closure',start=14,end=18));out=self.run_value();row=out['assessment']['calendars'][0];self.assertEqual(row['removed_units'],6);self.assertEqual(row['remaining_units'],24);self.assertEqual(sum(row['clipped_units'] for row in out['assessment']['closures']),7)
    def test_adjacent_closures_and_full_closure_have_no_zero_width_artifacts(self):
        self.value['closures'].append(dict(self.value['closures'][0],id='second',start=15,end=30));self.assertEqual(self.run_value()['assessment']['calendars'][0]['available_windows'],[dict(start=0,end=12)])
        self.value['closures'][0].update(start=0,end=15);self.assertEqual(self.run_value()['assessment']['calendars'][0]['available_windows'],[])
    def test_partial_closure_is_clipped_and_outside_closure_requires_review(self):
        self.value['closures'][0].update(start=25,end=40);out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertEqual(out['assessment']['closures'][0]['clipped_units'],5)
        self.value['closures'][0].update(start=30,end=40);self.assertEqual(self.review()['assessment']['closures'][0]['clipped_windows'],[])
    def test_calendar_adjacent_windows_normalize_but_overlaps_reject(self):
        self.value['calendars'][0]['windows']=[dict(start=15,end=30),dict(start=0,end=15)];self.assertEqual(self.run_value()['status'],'PASS')
        self.value['calendars'][0]['windows']=[dict(start=0,end=20),dict(start=15,end=30)];self.withheld()
    def test_empty_windows_are_unavailable_and_empty_closures_are_idle(self):
        self.value['closures']=[];self.value['calendars'][0]['windows']=[];out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertEqual(out['assessment']['calendars'][0]['remaining_units'],0)
    def test_unknown_and_stale_calendar_bindings_withhold(self):
        for update in ({'calendar':'other'},{'calendar_revision':2},{'calendar_sha256':'0'*64}):
            value=copy.deepcopy(self.value);value['closures'][0].update(update);self.withheld(value)
    def test_bad_spans_bool_ordinals_and_window_bounds_refuse(self):
        for change in ({'start':True},{'end':12},{'start':-1}):
            value=copy.deepcopy(self.value);value['closures'][0].update(change);self.withheld(value)
        self.value['calendars'][0]['windows']=[dict(start=n*2,end=n*2+1) for n in range(33)];self.withheld()
    def test_total_window_expansion_boundary_and_encoded_report_size(self):
        self.value['closures']=[];windows=[dict(start=n*2,end=n*2+1) for n in range(32)];self.value['calendars']=[dict(id='calendar-'+str(n),revision=1,windows=windows) for n in range(128)]
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertLess(len(t.encode(out)),8*1024*1024)
        self.value['calendars'].append(dict(id='one-more',revision=1,windows=[dict(start=0,end=1)]))
        with self.assertRaisesRegex(t.Rejected,'^CALENDAR_SCOPE_LIMIT$'):self.run_value()
    def test_closure_intersection_expansion_is_bounded(self):
        calendar=self.value['calendars'][0];calendar['windows']=[dict(start=n*2,end=n*2+1) for n in range(32)]
        self.value['closures']=[dict(self.value['closures'][0],id='closure-'+str(n),calendar_sha256=pin(calendar),start=0,end=64) for n in range(128)]
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertLess(len(t.encode(out)),8*1024*1024)
        self.value['closures'].append(dict(self.value['closures'][0],id='one-more'))
        with self.assertRaisesRegex(t.Rejected,'^CLOSURE_INTERSECTION_LIMIT$'):self.run_value()
