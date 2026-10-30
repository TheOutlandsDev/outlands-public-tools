import copy
import unittest
import toolkit as t
import service_core as c

def order():return dict(id='service-order-alpha',asset_id='air-handler-alpha',revision=5,state='completed')

class Common(unittest.TestCase):
    def test_order_exact_shape_types_and_states(self):
        for update in ({'revision':True},{'revision':0},{'revision':1001},{'state':'unknown'},{'asset_id':'UPPER'},{'extra':0}):
            with self.assertRaises(t.Rejected):c.order(dict(order(),**update))

    def test_tags_normalize_and_allow_empty(self):
        self.assertEqual(c.tags(['replace-filter','demo-check']),['demo-check','replace-filter']);self.assertEqual(c.tags([]),[])

    def test_tag_bounds_duplicates_and_types(self):
        for value in (None,{},['a','a'],['UPPER'],['tag-'+str(i) for i in range(33)],['valid',{}]):
            with self.assertRaises(t.Rejected):c.tags(value)

    def test_duplicate_snapshots_count_once(self):
        rows,counts,issues=c.rows([order()]*3,c.order,'orders')
        self.assertEqual(len(rows),1);self.assertFalse(issues);self.assertEqual(counts['duplicate_rows'],2)

    def test_conflicting_identity_withholds_every_member(self):
        rows,counts,issues=c.rows([order(),order(),dict(order(),revision=6)],c.order,'orders')
        self.assertFalse(rows);self.assertEqual(counts['conflict_rows'],3);self.assertEqual(counts['duplicate_rows'],0);self.assertEqual(len(issues),3)

    def test_all_rows_accounted(self):
        _,counts,_=c.rows([order(),order(),None,dict(order(),id='another'),dict(order(),id='another',revision=6)],c.order,'orders')
        self.assertEqual(counts,dict(input_rows=5,accepted_records=1,duplicate_rows=1,conflict_rows=2,rejected_rows=1))

    def test_list_limit_and_empty(self):
        for value in (None,{},[order()]*1001):
            with self.assertRaisesRegex(t.Rejected,'ROW_LIMIT'):c.rows(value,c.order,'orders')
        self.assertFalse(c.rows([],c.order,'orders')[0])

    def test_pin_key_order_invariance(self):
        a=order();b=dict(reversed(list(a.items())));self.assertEqual(c.order_pin(a),c.order_pin(b))

    def test_pin_covers_every_snapshot_field(self):
        before=c.order_pin(order())
        for change in ({'id':'another'},{'asset_id':'another'},{'revision':6},{'state':'cancelled'}):self.assertNotEqual(before,c.order_pin(dict(order(),**change)))

    def test_pin_is_exact_canonical_json_not_a_signature(self):
        self.assertEqual(c.order_pin(order()),t.digest(t.encode(order())))

    def test_fixed_diagnostics_omit_rejected_values(self):
        _,_,issues=c.rows([dict(order(),id='SYNTHETIC_SENTINEL')],c.order,'orders')
        self.assertEqual(issues,[dict(side='orders',row=1,code='IDENTIFIER_INVALID')])

    def test_record_parsers_do_not_mutate_inputs(self):
        value=order();before=copy.deepcopy(value);_,parsed=c.order(value);parsed['revision']=6;self.assertEqual(value,before)
