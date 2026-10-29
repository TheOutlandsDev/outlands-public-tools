"""Synthetic accounting and identity-boundary tests independent of target systems."""
import copy
import hashlib
import unittest
import control_core as c
import toolkit as t

def pin(s): return hashlib.sha256(s.encode()).hexdigest()
def batch(id='batch-a',sequence=1):
    return dict(id=id,sequence=sequence,source_sha256=pin('fictional source '+id),mapping_sha256=pin('fictional map'),
                preview_sha256=pin('fictional preview '+id),counts=dict(input_rows=3,accepted_records=2,duplicate_rows=1,rejected_rows=0,conflict_rows=0))
def receipt(b=None,status='committed'):
    b=b or batch()
    return dict(receipt_id='receipt-'+b['id'],stream='sample-stream',batch=copy.deepcopy(b),status=status,receipt_sha256=pin('fictional receipt '+b['id']))

class Common(unittest.TestCase):
    def test_counts_exact_known_result(self):
        self.assertEqual(c.accounting(batch()['counts'])['input_rows'],3)

    def test_count_invalid_shape_types_and_arithmetic(self):
        for changes in ({'accepted_records':True},{'input_rows':-1},{'input_rows':1001},{'accepted_records':3},{'duplicate_rows':'1'}):
            with self.assertRaises(t.Rejected): c.accounting(dict(batch()['counts'],**changes))
        with self.assertRaises(t.Rejected): c.accounting({})

    def test_batch_shape_bounds_and_pin(self):
        for changes in ({'id':'UPPER'},{'sequence':True},{'sequence':0},{'sequence':10**9+1},
                        {'source_sha256':'A'*64},{'counts':None},{'extra':'invented'}):
            with self.assertRaises(t.Rejected): c.batch(dict(batch(),**changes))

    def test_receipt_shape_status_and_stream(self):
        for changes in ({'stream':'UPPER'},{'status':'pending'},{'status':[]},{'receipt_sha256':'0'},
                        {'receipt_id':False},{'batch':{}},{'extra':0}):
            with self.assertRaises(t.Rejected): c.receipt(dict(receipt(),**changes))

    def test_identical_rows_count_once(self):
        a=batch(); accepted,counts,issues=c.rows([a,a,a],c.batch,'expected')
        self.assertEqual(len(accepted),1); self.assertFalse(issues)
        self.assertEqual(counts,dict(input_rows=3,accepted_records=1,duplicate_rows=2,conflict_rows=0,rejected_rows=0))

    def test_conflicting_group_includes_identical_repeats(self):
        a=batch(); b=dict(a,sequence=2)
        accepted,counts,issues=c.rows([a,a,b,batch('other',3)],c.batch,'expected')
        self.assertEqual(set(accepted),{'other'}); self.assertEqual(counts['conflict_rows'],3); self.assertEqual(counts['duplicate_rows'],0)
        self.assertEqual(len(issues),3)

    def test_complete_row_accounting(self):
        a=batch(); _,counts,issues=c.rows([a,a,{},None,batch('other',2),batch('other',3)],c.batch,'expected')
        self.assertEqual(counts,dict(input_rows=6,accepted_records=1,duplicate_rows=1,rejected_rows=2,conflict_rows=2))
        self.assertEqual(len(issues),4)

    def test_list_limit_and_shape(self):
        for value in ([batch()]*1001,{},None):
            with self.assertRaises(t.Rejected): c.rows(value,c.batch,'expected')

    def test_status_snapshots_conflict_never_replay(self):
        a=receipt(); b=dict(a,status='uncertain')
        accepted,counts,_=c.rows([a,b],c.receipt,'receipts')
        self.assertFalse(accepted); self.assertEqual(counts['conflict_rows'],2)

    def test_stream_mismatch(self):
        value=dict(stream='other-stream',expected=[batch()],receipts=[receipt()])
        issues=c.prepare(value)[3]; self.assertIn('STREAM_MISMATCH',[i['code'] for i in issues])

    def test_sequence_alias_across_lists(self):
        value=dict(stream='sample-stream',expected=[batch('other')],receipts=[receipt()])
        self.assertEqual([i['code'] for i in c.prepare(value)[3]].count('SEQUENCE_ALIAS'),2)

    def test_content_identity_alias(self):
        a=batch(); b=dict(a,id='other',sequence=2)
        issues=c.prepare(dict(stream='sample-stream',expected=[a,b],receipts=[]))[3]
        self.assertEqual([i['code'] for i in issues].count('CONTENT_ID_ALIAS'),2)

    def test_receipt_id_alias(self):
        a=receipt(); b=receipt(batch('other',2)); b['receipt_id']=a['receipt_id']
        issues=c.prepare(dict(stream='sample-stream',expected=[],receipts=[a,b]))[3]
        self.assertEqual([i['code'] for i in issues].count('RECEIPT_ID_ALIAS'),2)

    def test_clean_requires_accepted_nonempty_unconflicted_rows(self):
        self.assertTrue(c.clean(batch()))
        for counts in (dict(input_rows=0,accepted_records=0,duplicate_rows=0,rejected_rows=0,conflict_rows=0),
                       dict(input_rows=1,accepted_records=0,duplicate_rows=1,rejected_rows=0,conflict_rows=0),
                       dict(input_rows=3,accepted_records=2,duplicate_rows=0,rejected_rows=1,conflict_rows=0)):
            self.assertFalse(c.clean(dict(batch(),counts=counts)))

    def test_fixed_diagnostics_do_not_echo_values(self):
        _,_,issues=c.rows([dict(batch(),id='SYNTHETIC_SENTINEL')],c.batch,'expected')
        self.assertEqual(issues,[dict(side='expected',row=1,code='IDENTIFIER_INVALID')])

    def test_report_sorts_and_deduplicates_issues_only(self):
        issues=[dict(side='expected',row=2,code='TEST'),dict(side='expected',row=1,code='TEST')]*2
        report=c.report(b'{}','fictional',{},issues)
        self.assertEqual([r['row'] for r in report['issues']],[1,2]); self.assertFalse(report['row_counts_recomputed'])
