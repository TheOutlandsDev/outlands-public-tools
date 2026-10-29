"""Independent known-result contracts for supplied synthetic documents."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
import toolkit as t
import knowledge_core as c


def doc(id='sample',body='Invented text.',revision=1):
    return dict(id=id,revision=revision,text=body,sha256=hashlib.sha256(body.encode('utf-8')).hexdigest())


def ref(d): return {k:d[k] for k in ('id','revision','sha256')}


class Common(unittest.TestCase):
    def test_exact_unicode_pin(self):
        value=doc(body='A\U0001f331e\u0301\r\nB')
        self.assertEqual(c.document(value)[1],value)
        self.assertEqual(len(value['text']),7)
        self.assertEqual(len(value['text'].encode('utf-8')),11)

    def test_no_newline_or_unicode_normalization(self):
        for first,second in [('a\r\nb','a\nb'),('e\u0301','\u00e9')]:
            value=doc(body=first); value['text']=second
            with self.assertRaisesRegex(t.Rejected,'DOCUMENT_PIN_MISMATCH'): c.document(value)

    def test_document_pin_required(self):
        value=doc(); value['sha256']='0'*64
        with self.assertRaisesRegex(t.Rejected,'DOCUMENT_PIN_MISMATCH'): c.document(value)

    def test_document_shape_and_pin_syntax(self):
        for changes in ({'revision':True},{'revision':0},{'revision':1000001},{'id':'UPPER'},
                        {'sha256':'A'*64},{'text':''},{'text':None},{'text':'x'*4097}):
            with self.subTest(changes=changes),self.assertRaises(t.Rejected): c.document(dict(doc(),**changes))

    def test_unknown_document_fields(self):
        with self.assertRaises(t.Rejected): c.document(dict(doc(),extra='invented'))

    def test_text_control_refusal(self):
        for body in ('x\x00','x\x1b','x\x7f','x\x85'):
            with self.assertRaisesRegex(t.Rejected,'TEXT_CONTROL_INVALID'): c.document(doc(body=body))
        self.assertEqual(c.document(doc(body='a\t b\r\nc'))[1]['text'],'a\t b\r\nc')

    def test_duplicate_documents_count_once(self):
        d=doc(); accepted,counts,issues=c.documents([d,d,d])
        self.assertEqual(len(accepted),1); self.assertFalse(issues)
        self.assertEqual(counts,dict(input_rows=3,accepted_records=1,duplicate_rows=2,conflict_rows=0,rejected_rows=0))

    def test_conflict_withholds_entire_group(self):
        a=doc(); b=doc(body='Other invented body.')
        accepted,counts,issues=c.documents([a,a,b,doc('other')])
        self.assertEqual(set(accepted),{'other'})
        self.assertEqual((counts['conflict_rows'],counts['duplicate_rows'],len(issues)),(3,0,3))

    def test_multiple_revisions_are_conflicting(self):
        _,counts,issues=c.documents([doc(),doc(revision=2)])
        self.assertEqual(counts['conflict_rows'],2); self.assertEqual(len(issues),2)

    def test_all_rows_accounted(self):
        a=doc(); accepted,counts,issues=c.documents([a,a,{},None,doc('other'),doc('other',revision=2)])
        self.assertEqual(counts,dict(input_rows=6,accepted_records=1,duplicate_rows=1,conflict_rows=2,rejected_rows=2))
        self.assertEqual(len(issues),4)

    def test_document_limit(self):
        with self.assertRaisesRegex(t.Rejected,'ROW_LIMIT'): c.documents([doc()]*101)
        with self.assertRaises(t.Rejected): c.documents({})

    def test_reference_missing_stale_and_wrong_pin(self):
        docs=c.documents([doc()])[0]
        for changes,code in [({'id':'missing'},'REFERENCE_MISSING'),({'revision':2},'REFERENCE_REVISION_MISMATCH'),
                             ({'sha256':'0'*64},'REFERENCE_PIN_MISMATCH')]:
            with self.assertRaisesRegex(t.Rejected,code): c.resolve(dict(ref(doc()),**changes),docs)

    def test_reference_list_ambiguity(self):
        for refs in ([ref(doc()),ref(doc())],[ref(doc()),ref(doc(revision=2))]):
            with self.assertRaisesRegex(t.Rejected,'DUPLICATE_REFERENCE'): c.references(refs)
        for value in (None,{},[ref(doc())]*101):
            with self.assertRaises(t.Rejected): c.references(value)

    def test_fraction_serialization(self):
        from fractions import Fraction
        self.assertEqual(c.ratio(Fraction(2,6)),dict(numerator='1',denominator='3'))

    def test_issue_omits_supplied_values(self):
        _,counts,issues=c.documents([dict(doc(),id='SYNTHETIC_SENTINEL')])
        self.assertEqual(issues,[dict(side='documents',row=1,code='IDENTIFIER_INVALID')])
        self.assertNotIn('SYNTHETIC_SENTINEL',t.encode(issues).decode())
