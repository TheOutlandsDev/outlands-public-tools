from fractions import Fraction
import unittest
import metrics_core as c
import toolkit as t


class Shared(unittest.TestCase):
    def test_decimal_strict_types_not_coerced(self):
        for value in (1,True,None,[],{},'NaN','Infinity','1e2','+1',' 1','01','1.0000001'):
            with self.subTest(value=value),self.assertRaises(t.Rejected): c.number(value)

    def test_exact_decimal_and_canonical_negative_zero(self):
        self.assertEqual(c.number('0.1')+c.number('0.2'),Fraction(3,10))
        self.assertEqual(c.canonical('-0.000000'),'0'); self.assertEqual(c.canonical('10.5000'),'10.5')

    def test_numeric_boundaries(self):
        self.assertEqual(c.number('-1000000000000'),-10**12)
        for value in ('1000000000000.000001','-1000000000000.000001'):
            with self.assertRaises(t.Rejected): c.number(value)

    def test_exact_ratios_are_decimal_integer_strings(self):
        self.assertEqual(c.ratio(Fraction(-2,6)),dict(numerator='-1',denominator='3'))
        large=c.ratio(Fraction(4*10**24,3)); self.assertEqual(t.decode(t.encode(large)),large)

    def test_square_root_rounding_and_exact_zero(self):
        self.assertEqual(c.root_mean_square(Fraction(3)),'1.732050807569')
        self.assertEqual(c.root_mean_square(Fraction()),'0.000000000000')

    def test_row_limit(self):
        with self.assertRaises(t.Rejected): c.rows([{}]*1001,lambda row:('id',row),'sample')

    def test_all_conflicting_members_are_withheld(self):
        actual,counts,issues=c.rows([dict(id='a',value=1),dict(id='a',value=1),dict(id='a',value=2)],lambda row:(row['id'],row),'sample')
        self.assertFalse(actual); self.assertEqual(counts['conflict_rows'],3); self.assertEqual(len(issues),3)

    def test_duplicate_normalized_rows_count_once(self):
        actual,counts,issues=c.rows([dict(id='a')]*3,lambda row:(row['id'],row),'sample')
        self.assertEqual(len(actual),1); self.assertEqual(counts['duplicate_rows'],2); self.assertFalse(issues)

    def test_rejected_rows_accounted_with_fixed_codes(self):
        def parse(row): t.fields(row,{'id'}); return t.identifier(row['id']),row
        actual,counts,issues=c.rows([dict(id='a'),dict(private='FICTIONAL_SENTINEL')],parse,'sample')
        self.assertEqual(counts['rejected_rows'],1); self.assertNotIn('FICTIONAL_SENTINEL',t.encode(issues).decode())

    def test_json_duplicate_keys_and_nonfinite_refused(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":0.5}'):
            with self.assertRaises(t.Rejected): t.decode(raw)
