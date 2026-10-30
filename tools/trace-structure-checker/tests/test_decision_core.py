from decimal import localcontext
from fractions import Fraction
import unittest
import toolkit as t
import decision_core as c

def tax():return dict(id='demo-labels',revision=1,labels=['noise','filter'])

class Common(unittest.TestCase):
    def test_taxonomy_normalizes_order_but_not_revision(self):
        self.assertEqual(c.taxonomy(tax())['labels'],['filter','noise'])
        for change in ({'revision':True},{'revision':0},{'revision':1000001},{'extra':0}):
            with self.assertRaises(t.Rejected):c.taxonomy(dict(tax(),**change))

    def test_tag_limits_exact_ids_and_duplicates(self):
        for value in (None,{},['a','a'],['UPPER'],['tag-'+str(i) for i in range(33)],['valid',{}]):
            with self.assertRaises(t.Rejected):c.tags(value)
        with self.assertRaises(t.Rejected):c.taxonomy(dict(tax(),labels=[]))

    def test_decimal_unit_interval_exact_normalization(self):
        for value,want in [('0.600000','0.6'),('-0.0','0'),('1.000','1'),('0.000001','0.000001')]:
            exact,text=c.decimal(value);self.assertEqual(exact,Fraction(value));self.assertEqual(text,want)

    def test_decimal_rejects_coercion_nonfinite_and_unbounded_values(self):
        for value in (True,0.5,None,{},'NaN','1e-1','+0.1','00.1','0.',' 0.1','0.0000001','1.000001','-0.1'):
            with self.assertRaises(t.Rejected):c.decimal(value)

    def test_fractional_differences_ignore_ambient_decimal_context(self):
        with localcontext() as ctx:
            ctx.prec=2
            difference=c.decimal('0.700001')[0]-c.decimal('0.6')[0]
            self.assertEqual(c.decimal_text(difference),'0.100001')

    def test_exact_signed_ratios_preserve_denominator(self):
        self.assertEqual(c.ratio(-2,4),dict(numerator=-2,denominator=4,exact_fraction='-1/2'))
        self.assertEqual(c.ratio(0,3)['exact_fraction'],'0/1')
        for n,d in [(1,0),(4,3),(True,3)]:
            with self.assertRaises(t.Rejected):c.ratio(n,d)

    def test_normalized_duplicate_snapshots_count_once(self):
        def parser(row):v=c.taxonomy(row);return v['id'],v
        a=tax();b=dict(a,labels=list(reversed(a['labels'])))
        rows,counts,issues=c.rows([a,b],parser,'labels');self.assertEqual(len(rows),1);self.assertEqual(counts['duplicate_rows'],1);self.assertFalse(issues)

    def test_conflicting_identity_withholds_every_member(self):
        parser=lambda row:c.record(row,{'id','value'},('id',))
        a=dict(id='sample',value=1);rows,counts,issues=c.rows([a,a,dict(a,value=2)],parser,'cases')
        self.assertFalse(rows);self.assertEqual(counts['conflict_rows'],3);self.assertEqual(counts['duplicate_rows'],0);self.assertEqual(len(issues),3)

    def test_every_row_accounted(self):
        parser=lambda row:c.record(row,{'id'},('id',))
        _,counts,_=c.rows([dict(id='sample'),dict(id='sample'),None,dict(id='other')],parser,'cases')
        self.assertEqual(counts,dict(input_rows=4,accepted_records=2,duplicate_rows=1,conflict_rows=0,rejected_rows=1))

    def test_list_limit_and_empty_list(self):
        parser=lambda row:c.record(row,{'id'},('id',))
        for value in (None,{},[dict(id='sample')]*1001):
            with self.assertRaisesRegex(t.Rejected,'ROW_LIMIT'):c.rows(value,parser,'cases')
        self.assertFalse(c.rows([],parser,'cases')[0])

    def test_fixed_diagnostics_omit_rejected_values(self):
        parser=lambda row:c.record(row,{'id'},('id',))
        _,_,issues=c.rows([dict(id='SYNTHETIC_SENTINEL')],parser,'cases')
        self.assertEqual(issues,[dict(side='cases',row=1,code='IDENTIFIER_INVALID')])

    def test_cohort_pin_is_order_invariant(self):
        parser=lambda row:c.record(row,{'id'},('id',));a=dict(id='alpha');b=dict(id='bravo')
        self.assertEqual(c.cohort_pin(c.rows([a,b],parser,'cases')[0]),c.cohort_pin(c.rows([b,a],parser,'cases')[0]))
