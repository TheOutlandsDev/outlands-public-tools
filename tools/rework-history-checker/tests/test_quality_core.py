from decimal import localcontext
from fractions import Fraction
import unittest
import toolkit as t
import quality_core as c

def rule():return dict(id='demo-window',revision=1,unit='demo-units',minimum='10',maximum='20',minimum_inclusive=True,maximum_inclusive=True)

class Common(unittest.TestCase):
    def test_exact_decimal_and_normalization(self):
        for raw,want in [('10.000000','10'),('-0.000000','0'),('0.100000','0.1'),('-12.2500','-12.25')]:
            exact,text=c.decimal(raw);self.assertEqual(text,want);self.assertEqual(exact,Fraction(raw))

    def test_decimal_precision_and_magnitude_bounds(self):
        self.assertEqual(c.decimal('1000000000000')[0],10**12)
        self.assertEqual(c.decimal('-999999999999.999999')[0],Fraction('-999999999999.999999'))
        for value in ('1000000000000.000001','-1000000000000.000001','0.1234567','10000000000000'):
            with self.assertRaises(t.Rejected):c.decimal(value)

    def test_decimal_noncanonical_forms_and_types_refused(self):
        for value in (1,True,1.0,None,{},'1e1','NaN','+1','01','1.',' 1','1_000'):
            with self.assertRaises(t.Rejected):c.decimal(value)

    def test_ambient_decimal_context_never_rounds_limits(self):
        with localcontext() as context:
            context.prec=3
            self.assertEqual(c.decimal('999999999999.999999')[0],Fraction(999999999999999999,1000000))

    def test_rule_interval_flags_and_revisions(self):
        for update in ({'revision':True},{'revision':0},{'revision':1000001},{'minimum_inclusive':1},{'maximum':'9'},{'unit':{}}):
            with self.assertRaises(t.Rejected):c.rule(dict(rule(),**update))
        for low,high in ((False,False),(True,False),(False,True)):
            with self.assertRaisesRegex(t.Rejected,'EMPTY_LIMIT_INTERVAL'):c.rule(dict(rule(),maximum='10',minimum_inclusive=low,maximum_inclusive=high))
        self.assertEqual(c.rule(dict(rule(),maximum='10'))[1]['maximum'],'10')

    def test_normalized_rule_duplicates_count_once(self):
        a=rule();b=dict(a,minimum='10.000',maximum='20.0')
        accepted,counts,issues=c.rows([a,b],c.rule,'rules')
        self.assertEqual(len(accepted),1);self.assertEqual(counts['duplicate_rows'],1);self.assertFalse(issues)

    def test_conflicting_group_withholds_every_member(self):
        accepted,counts,issues=c.rows([rule(),rule(),dict(rule(),revision=2)],c.rule,'rules')
        self.assertFalse(accepted);self.assertEqual(counts['conflict_rows'],3);self.assertEqual(counts['duplicate_rows'],0);self.assertEqual(len(issues),3)

    def test_every_row_accounted_for(self):
        values=[dict(id='unit-a'),dict(id='unit-a'),None,dict(id='unit-b'),dict(id='unit-b',extra=0)]
        _,counts,_=c.rows(values,c.entity,'units')
        self.assertEqual(counts,dict(input_rows=5,accepted_records=2,duplicate_rows=1,conflict_rows=0,rejected_rows=2))

    def test_list_limit_and_empty_list(self):
        for value in (None,{},[dict(id='unit-a')]*1001):
            with self.assertRaisesRegex(t.Rejected,'ROW_LIMIT'):c.rows(value,c.entity,'units')
        self.assertFalse(c.rows([],c.entity,'units')[0])

    def test_fixed_diagnostics_omit_rejected_values(self):
        _,_,issues=c.rows([dict(id='SYNTHETIC_SENTINEL')],c.entity,'units')
        self.assertEqual(issues,[dict(side='units',row=1,code='IDENTIFIER_INVALID')])

    def test_pin_order_invariance_and_revision_changes(self):
        a=rule();b=dict(a,id='other');x=c.rows([a,b],c.rule,'rules')[0];y=c.rows([b,a],c.rule,'rules')[0]
        self.assertEqual(c.pin(x),c.pin(y));self.assertNotEqual(c.pin(x),c.pin(c.rows([dict(a,revision=2),b],c.rule,'rules')[0]))

    def test_ratio_preserves_cohort_denominator(self):
        self.assertEqual(c.ratio(2,4),dict(numerator=2,denominator=4,exact_fraction='1/2'))
        self.assertEqual(c.ratio(0,3)['exact_fraction'],'0/1');self.assertEqual(c.ratio(3,3)['exact_fraction'],'1/1')
        for n,d in [(1,0),(-1,3),(4,3),(True,3)]:
            with self.assertRaises(t.Rejected):c.ratio(n,d)
