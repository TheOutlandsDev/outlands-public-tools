import copy
import json
import io
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import zipfile
import zlib
import receipts
import intake
import fictional_workbook
import toolkit as t

EXAMPLES=Path(__file__).absolute().parents[1]/'examples'


class Receipts(unittest.TestCase):
    def setUp(self):
        self.source=(EXAMPLES/'source.txt').read_bytes(); self.mapping=(EXAMPLES/'mapping.json').read_bytes()
        self.receipt=json.loads((EXAMPLES/'receipt.json').read_text(encoding='utf-8'))
        self.preview=(EXAMPLES/'preview.json').read_bytes()

    def call(self): return receipts.reconcile(t.encode(self.receipt),self.source,self.mapping,self.preview)
    def reset_claims(self,kind='csv',sheet=None):
        observed=intake.preview(self.source,self.mapping,kind,sheet)
        self.preview=t.encode(observed)
        self.receipt.update(source_format=kind,sheet=sheet,source_sha256=t.digest(self.source),
            mapping_sha256=t.digest(self.mapping),preview_sha256=t.digest(self.preview),counts=observed['counts'])

    def test_fictional_counts_actually_recomputed(self):
        result=self.call(); self.assertEqual(result['observed_counts'],dict(input_rows=3,accepted_records=2,
            duplicate_rows=1,rejected_rows=0,conflict_rows=0))
        self.assertTrue(result['row_counts_recomputed']); self.assertTrue(result['ready_for_explicit_review'])
        self.assertFalse(result['source_authority_verified']); self.assertFalse(result['imported'])

    def test_accepted_values_and_source_rows_not_exposed(self):
        result=self.call(); self.assertNotIn('sample-alpha',t.encode(result).decode())
        self.assertNotIn('accepted',result); self.assertNotIn('source_rows',result)

    def test_forged_same_total_counts_detected(self):
        self.receipt['counts'].update(accepted_records=1,duplicate_rows=2)
        self.assertIn('RECEIPT_COUNT_MISMATCH',self.call()['issues'])

    def test_declared_accounting_disagreement(self):
        self.receipt['counts']['input_rows']=4
        self.assertIn('DECLARED_ACCOUNTING_MISMATCH',self.call()['issues'])

    def test_each_raw_pin_independently_checked(self):
        for key in ('source_sha256','mapping_sha256','preview_sha256'):
            saved=self.receipt[key]; self.receipt[key]='0'*64
            with self.subTest(key=key): self.assertIn(key.upper()+'_MISMATCH',self.call()['issues'])
            self.receipt[key]=saved

    def test_forged_accepted_values_cannot_match(self):
        value=t.decode(self.preview); value['accepted'][0]['record']['units']=999
        self.preview=t.encode(value); self.receipt['preview_sha256']=t.digest(self.preview)
        self.assertIn('PREVIEW_CONTENT_MISMATCH',self.call()['issues'])

    def test_forged_source_row_provenance_cannot_match(self):
        value=t.decode(self.preview); value['accepted'][0]['source_rows']=[999]
        self.preview=t.encode(value); self.receipt['preview_sha256']=t.digest(self.preview)
        self.assertIn('PREVIEW_CONTENT_MISMATCH',self.call()['issues'])

    def test_bool_and_integer_are_not_treated_as_equal(self):
        value=t.decode(self.preview); value['imported']=0
        self.preview=t.encode(value); self.receipt['preview_sha256']=t.digest(self.preview)
        self.assertIn('PREVIEW_CONTENT_MISMATCH',self.call()['issues'])

    def test_whitespace_only_preview_reencoding_can_match_with_fresh_pin(self):
        self.preview=json.dumps(t.decode(self.preview),indent=2).encode()
        self.receipt['preview_sha256']=t.digest(self.preview)
        result=self.call(); self.assertEqual(result['status'],'PASS')
        self.assertNotEqual(result['supplied_preview_sha256'],result['recomputed_preview_sha256'])

    def test_conflicts_rejections_and_all_rows_accounted(self):
        self.source+=b'sample-alpha,8\nsample-gamma,bad\n'; self.reset_claims()
        result=self.call(); self.assertEqual(result['status'],'REVIEW_REQUIRED')
        self.assertEqual(result['observed_counts']['conflict_rows'],3)
        self.assertEqual(result['observed_counts']['rejected_rows'],1)
        self.assertIn('INTAKE_REQUIRES_REVIEW',result['issues']); self.assertFalse(result['ready_for_explicit_review'])

    def test_header_only_withholds_readiness(self):
        self.source=b'Record,Units\n'; self.reset_claims()
        self.assertFalse(self.call()['ready_for_explicit_review'])

    def test_boolean_counts_and_unknown_receipt_fields_refused(self):
        self.receipt['counts']['accepted_records']=True
        with self.assertRaises(t.Rejected): self.call()
        self.receipt['counts']['accepted_records']=2; self.receipt['path']='invented'
        with self.assertRaises(t.Rejected): self.call()

    def test_unknown_preview_fields_and_array_reordering_detected(self):
        value=t.decode(self.preview); value['extra']='invented'
        self.preview=t.encode(value); self.receipt['preview_sha256']=t.digest(self.preview)
        self.assertIn('PREVIEW_CONTENT_MISMATCH',self.call()['issues'])

    def test_wrong_source_format_and_sheet_selection_refused(self):
        for kind,sheet in (('xml',None),('csv','Records'),('xlsx',None)):
            self.receipt.update(source_format=kind,sheet=sheet)
            with self.assertRaises(t.Rejected): self.call()

    def test_actual_inline_and_shared_xlsx_recompute(self):
        rows=[['Record','Units'],['sample-alpha','7'],['sample-beta','9'],['sample-alpha','7']]
        for shared in (False,True):
            self.source=fictional_workbook.workbook(rows,shared=shared); self.reset_claims('xlsx','Records')
            self.assertEqual(self.call()['status'],'PASS'); self.assertEqual(self.call()['observed_counts']['duplicate_rows'],1)

    def test_xlsx_external_relationship_and_formula_refused(self):
        raw=fictional_workbook.workbook([['Record','Units'],['sample-alpha','7']])
        for path,old,new in (('xl/_rels/workbook.xml.rels',b'Target=',b'TargetMode="External" Target='),
                             ('xl/worksheets/sheet1.xml',b'<is><t>7</t></is>',b'<f>1+6</f>')):
            out=io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(raw)) as source,zipfile.ZipFile(out,'w') as target:
                for name in source.namelist():
                    value=source.read(name); target.writestr(name,value.replace(old,new) if name==path else value)
            self.source=out.getvalue(); self.receipt.update(source_format='xlsx',sheet='Records')
            with self.assertRaises(t.Rejected): self.call()

    def test_parser_failures_are_fixed_refusals(self):
        for error in (zlib.error('FICTIONAL_SENTINEL'),struct.error('FICTIONAL_SENTINEL'),EOFError('FICTIONAL_SENTINEL')):
            with patch.object(intake,'preview',side_effect=error),self.assertRaisesRegex(t.Rejected,'^INTAKE_REFUSED$'):
                self.call()

    def test_malformed_source_or_mapping_refused(self):
        self.source=b'Record,Record\nx,y\n'
        with self.assertRaises(t.Rejected): self.call()

    def test_duplicate_json_keys_refused(self):
        self.preview=b'{"status":"PASS","status":"PASS"}'
        with self.assertRaisesRegex(t.Rejected,'JSON_DUPLICATE_KEY'): self.call()

    def test_immutable_inputs_and_exact_receipt_pin(self):
        before=copy.deepcopy(self.receipt); result=self.call()
        self.assertEqual(result,self.call()); self.assertEqual(self.receipt,before)
        self.assertEqual(result['receipt_sha256'],t.digest(t.encode(self.receipt)))
