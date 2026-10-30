import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import unittest
import toolkit as t
import scenarios as app
import pricing_core as r
def encode(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def pin(v):return hashlib.sha256(encode(v)).hexdigest()
class Contracts(unittest.TestCase):
    def setUp(self):self.value=json.loads((Path(__file__).resolve().parents[1]/'examples/input.json').read_text(encoding='utf-8'))
    def run_value(self,v=None):return app.check(encode(self.value if v is None else v))
    def review(self,v=None):
        out=self.run_value(v);self.assertEqual(out['status'],'REVIEW_REQUIRED');self.assertTrue(out['issues']);self.assertIsNone(out['qualified_scope_sha256']);return out
    def withheld(self,v=None):
        out=self.review(v);self.assertIsNone(out['assessment']);self.assertIsNone(out['cohort_sha256']);return out
    def repin(self):
        if 'price_books' in self.value:
            b=self.value['price_books'][0];b=r.book(b)[1]
            for q in self.value.get('quotes',[]):q.update(price_book=b['id'],price_book_revision=b['revision'],price_book_sha256=pin(b))
        if 'claims' in self.value:
            q=r.arithmetic_quote(self.value['quotes'][0])[1]
            for claim in self.value['claims']:claim.update(quote=q['id'],quote_revision=q['revision'],quote_sha256=pin(q))
    def test_no_positive_execution_approval_or_tax_claims(self):
        out=self.run_value();self.assertEqual(out['status'],'PASS');self.assertIsNotNone(out['qualified_scope_sha256'])
        for key in ('execution_authorized','target_changes_performed','network_requests_performed','records_changed','currency_conversion_performed','tax_rules_verified','approval_verified','whole_catalog_compatibility_verified','content_privacy_verified'):self.assertIs(out[key],False)
    def test_outer_schema_format_duplicate_keys_float_nan_and_boolean_root_refuse(self):
        for v in ({},dict(self.value,extra=0),dict(self.value,format='other'),True):
            with self.assertRaises(t.Rejected):self.run_value(v)
        for raw in (b'{"format":0,"format":1}',b'{"x":1.2}',b'{"x":NaN}'):
            with self.assertRaises(t.Rejected):app.check(raw)
    def test_raw_input_hash_semantic_pins_and_determinism(self):
        raw=encode(self.value);out=app.check(raw);self.assertEqual(out['input_sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(out,app.check(raw));spaced=json.dumps(self.value,indent=2).encode('ascii');self.assertNotEqual(out['input_sha256'],app.check(spaced)['input_sha256']);self.assertEqual(out['qualified_scope_sha256'],app.check(spaced)['qualified_scope_sha256'])
    def test_cohort_order_is_normalized(self):
        before=self.run_value()
        for key in ['baseline_price_books', 'candidate_price_books', 'baskets']:self.value[key].reverse()
        self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
    def test_duplicate_top_level_rows_preserve_accounting(self):
        for key in ['baseline_price_books', 'candidate_price_books', 'baskets']:
            v=copy.deepcopy(self.value);v[key].append(copy.deepcopy(v[key][0]));out=self.run_value(v);self.assertEqual(out['status'],'PASS');counts=out['counts'][key];self.assertEqual(counts['duplicate_rows'],1);self.assertEqual(counts['input_rows'],sum(counts[k] for k in ('accepted_records','duplicate_rows','conflict_rows','rejected_rows')))
    def test_conflicting_identity_members_are_all_withheld(self):
        for key in ['baseline_price_books', 'candidate_price_books', 'baskets']:
            v=copy.deepcopy(self.value);row=copy.deepcopy(v[key][0]);row['revision']+=1;v[key].extend([row,copy.deepcopy(v[key][0])]);out=self.withheld(v);self.assertEqual(out['counts'][key]['conflict_rows'],3)
    def test_bad_rows_and_unknown_fields_do_not_echo_untrusted_values(self):
        for key in ['baseline_price_books', 'candidate_price_books', 'baskets']:
            for row in (None,dict(id='SYNTHETIC_SENTINEL'),dict(self.value[key][0],extra='SYNTHETIC_SENTINEL')):
                v=copy.deepcopy(self.value);v[key].append(row);self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(self.withheld(v)))
    def test_empty_cohorts_and_raw_limits_never_truncate_to_pass(self):
        for key in ['baseline_price_books', 'candidate_price_books', 'baskets']:
            v=copy.deepcopy(self.value);v[key]=[];self.withheld(v)
            for bad in (None,{},[{}]*129):
                v=copy.deepcopy(self.value);v[key]=bad
                with self.assertRaises(t.Rejected):self.run_value(v)
    def test_decimal_syntax_range_and_exact_boolean_refusal(self):
        for v in (True,1,1.5,None,{},[],'.5','01','-0','-1','1e2','NaN','Infinity','1.0000001','1000000000000000001'):
            with self.assertRaises(t.Rejected):r.number(v)
        self.assertEqual(r.number('0.000001')[0],Fraction(1,1000000));self.assertEqual(r.number('1.230000')[1],'1.23')
    def test_rounding_known_half_ties_even_up_and_down(self):
        for value,rule,want in [('1.005','half_up',101),('1.005','half_even',100),('1.015','half_even',102),('1.009','down',100),('1.004999','half_up',100),('1.005001','half_even',101)]:self.assertEqual(r.rounded(Fraction(value),2,rule),want)
        self.assertEqual(r.money(r.rounded(Fraction('2.5'),0,'half_even'),0),'2');self.assertEqual(r.money(1,4),'0.0001')
    def test_rounding_is_independent_of_decimal_context(self):
        import decimal
        with decimal.localcontext() as context:
            context.prec=2;self.assertEqual(r.rounded(Fraction('123456789.125'),2,'half_even'),12345678912)
    def test_explicit_minor_unit_precision_is_required(self):
        self.assertEqual(r.minor('1.2300',2),123)
        with self.assertRaises(t.Rejected):r.minor('1.001',2)
    def test_shared_book_nested_ids_revision_currency_and_rules_are_bounded(self):
        base=dict(id='fictional',revision=1,currency='USD',minor_digits=2,rounding='half_up',items=[dict(id='kit',unit='each',tiers=[dict(minimum_quantity='0',unit_price='1')])])
        for key,values in [('revision',[0,True,1000001]),('currency',['usd','US',True,{}]),('minor_digits',[True,-1,5]),('rounding',['automatic',None,[]])]:
            for value in values:
                row=copy.deepcopy(base);row[key]=value
                with self.assertRaises(t.Rejected):r.book(row)
        base['items']*=2
        with self.assertRaises(t.Rejected):r.book(base)

    def result(self,out=None):return (out or self.run_value())['assessment']['baskets'][0]
    def test_identical_basket_under_new_revision_has_equal_outcomes(self):self.assertTrue(self.result()['equal']);self.assertTrue(self.result()['comparable'])
    def test_changed_selected_tier_is_visible_with_both_exact_prices(self):
        self.value['candidate_price_books'][0]['items'][0]['tiers'][1]['unit_price']='11.5';out=self.result(self.review());self.assertFalse(out['equal']);self.assertTrue(out['comparable']);self.assertEqual(out['candidate'][0]['expected_unit_price'],'11.5')
    def test_same_revision_changed_definition_is_structural_conflict(self):
        book=self.value['candidate_price_books'][0];book['revision']=1;book['items'][0]['tiers'][1]['unit_price']='12';self.withheld()
    def test_currency_or_minor_unit_changes_are_incomparable(self):
        for key,value in [('currency','CAD'),('minor_digits',3)]:
            v=copy.deepcopy(self.value);v['candidate_price_books'][0][key]=value;self.withheld(v)
    def test_missing_item_and_changed_unit_never_become_equal_negatives(self):
        for change in ('item','unit'):
            v=copy.deepcopy(self.value)
            if change=='item':v['candidate_price_books'][0]['items'].pop(0)
            else:v['candidate_price_books'][0]['items'][0]['unit']='box'
            out=self.result(self.review(v));self.assertFalse(out['comparable']);self.assertFalse(out['equal'])
    def test_unselected_tier_change_only_establishes_selected_basket_equality(self):
        self.value['candidate_price_books'][0]['items'][0]['tiers'][0]['unit_price']='99';out=self.run_value();self.assertTrue(self.result(out)['equal']);self.assertFalse(out['whole_catalog_compatibility_verified'])
    def test_subminor_price_change_visible_even_when_extensions_round_equal(self):
        self.value['candidate_price_books'][0]['items'][0]['tiers'][1]['unit_price']='11.250001';out=self.result(self.review());self.assertEqual(out['baseline'][0]['rounded_extension'],out['candidate'][0]['rounded_extension']);self.assertFalse(out['equal'])
    def test_rounding_rule_change_is_evaluated_on_actual_selected_lines(self):
        v=self.value;v['baskets'][0]['lines']=[dict(id='one',item='filter-kit',unit='each',quantity='1')];v['candidate_price_books'][0]['rounding']='half_even';out=self.result(self.review());self.assertEqual(out['baseline'][0]['rounded_extension'],'12.35');self.assertEqual(out['candidate'][0]['rounded_extension'],'12.34')
    def test_only_one_book_per_side_and_nonempty_basket_required(self):
        v=copy.deepcopy(self.value);v['candidate_price_books'].append(dict(v['candidate_price_books'][0],id='other'));self.withheld(v);self.value['baskets'][0]['lines']=[];self.withheld()
    def test_basket_line_order_is_normalized_but_quantity_changes_are_pinned(self):
        before=self.run_value();self.value['baskets'][0]['lines'].reverse();self.assertEqual(before['cohort_sha256'],self.run_value()['cohort_sha256']);self.value['baskets'][0]['lines'][0]['quantity']='2';self.assertNotEqual(before['cohort_sha256'],self.run_value()['cohort_sha256'])
