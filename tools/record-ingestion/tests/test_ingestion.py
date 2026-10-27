"""Invented in-memory records only; no operational inputs or integrations."""
from dataclasses import FrozenInstanceError
import hashlib
import io
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ingestion import Point, ReferenceError, ingest_csv, ingest_jsonl
from demo import run_demo


def rows(*values):
    return "\n".join(json.dumps(dict(series="sample",period=index,value=value)) for index,value in enumerate(values))


def points(*values):
    return tuple(Point("sample",index,value) for index,value in enumerate(values))


class IngestionTests(unittest.TestCase):
    def test_exact_byte_limit_is_accepted_and_one_extra_byte_refused(self):
        source=rows(1)
        source+=' '*(65536-len(source.encode()))
        self.assertEqual(ingest_jsonl(source).require_clean(),points(1))
        with self.assertRaisesRegex(ReferenceError,'INPUT_BYTE_LIMIT'):ingest_jsonl(source+' ')

    def test_maximum_unique_records_are_accepted_without_truncation(self):
        batch=ingest_jsonl(rows(*range(256)))
        self.assertEqual(len(batch.require_clean()),256)
        self.assertEqual(batch.records[-1].period,255)
        with self.assertRaisesRegex(ReferenceError,'INPUT_RECORD_LIMIT'):ingest_jsonl(rows(*range(257)))

    def test_csv_positions_count_records_not_multiline_source_lines(self):
        batch=ingest_csv('series,period,value\n"bad\nseries",0,1\nsample,1,2\n')
        self.assertEqual(batch.issues[0].record,2)
        self.assertEqual(batch.issues[0].code,'SERIES_INVALID')
        self.assertEqual(batch.records,(Point('sample',1,2),))
        with self.assertRaises(ReferenceError):batch.require_clean()

    def test_deeply_nested_json_produces_fixed_review_code(self):
        batch=ingest_jsonl('['*2000+'1'+']'*2000)
        self.assertIn(batch.issues[0].code,('JSON_RECORD_INVALID','ROW_SCHEMA_INVALID'))
        self.assertFalse(batch.ok)
        with mock.patch('ingestion.json.loads',side_effect=RecursionError):
            refused=ingest_jsonl(rows(1))
        self.assertEqual(refused.issues[0].code,'JSON_RECORD_INVALID')

    def test_script_like_payload_is_never_opened_imported_or_executed(self):
        with mock.patch('builtins.open',side_effect=AssertionError('FILE_OPENED')),mock.patch.object(os,'system',side_effect=AssertionError('SHELL')),mock.patch.object(subprocess,'run',side_effect=AssertionError('PROCESS')),mock.patch.object(socket,'socket',side_effect=AssertionError('NETWORK')):
            batch=ingest_jsonl("raise RuntimeError('FICTIONAL_DO_NOT_ECHO')")
        self.assertEqual(batch.issues[0].code,'JSON_RECORD_INVALID')
        self.assertNotIn('FICTIONAL_DO_NOT_ECHO',repr(batch))

    def test_jsonl_normalizes_orders_and_deduplicates(self):
        source='{"series":" SAMPLE ","period":1,"value":2}\n{"series":"sample","period":0,"value":1}\n{"series":"sample","period":1,"value":2}\n'
        before=source
        batch=ingest_jsonl(source)
        self.assertTrue(batch.ok)
        self.assertEqual(batch.require_clean(),points(1,2))
        self.assertEqual(batch.duplicates,1)
        self.assertEqual(source,before)

    def test_csv_and_jsonl_have_the_same_typed_results(self):
        batch=ingest_csv('series,period,value\r\n SAMPLE ,000,1.5\r\nsample,1,2\r\n')
        self.assertEqual(batch.require_clean(),ingest_jsonl(rows(1.5,2)).require_clean())

    def test_initial_bom_is_supported_but_midstream_bom_is_not(self):
        self.assertEqual(ingest_jsonl('\ufeff'+rows(1)).require_clean(),points(1))
        self.assertEqual(ingest_csv('\ufeffseries,period,value\nsample,0,1').require_clean(),points(1))
        self.assertFalse(ingest_jsonl(rows(1)+'\n\ufeff'+rows(2)).ok)

    def test_conflicting_duplicates_block_clean_consumption(self):
        batch=ingest_jsonl(rows(1)+'\n'+rows(2))
        self.assertEqual(batch.records,points(1))
        self.assertEqual(batch.issues[0].code,'RECORD_CONFLICT')
        with self.assertRaisesRegex(ReferenceError,'BATCH_REVIEW_REQUIRED'):batch.require_clean()

    def test_unknown_fields_and_json_duplicate_keys_are_not_retained(self):
        value=dict(series='sample',period=0,value=1,private_field='FICTIONAL_DO_NOT_ECHO')
        batch=ingest_jsonl(json.dumps(value)+'\n'+ '{"series":"sample","period":0,"value":1,"value":2}')
        self.assertFalse(batch.ok)
        self.assertEqual([issue.code for issue in batch.issues],['ROW_SCHEMA_INVALID','JSON_DUPLICATE_KEY'])
        self.assertNotIn('FICTIONAL_DO_NOT_ECHO',repr(batch))
        self.assertNotIn('private_field',repr(batch))

    def test_numbers_are_finite_bounded_and_not_boolean(self):
        for value in (True,None,'1',float('nan'),float('inf'),10**1000):
            with self.subTest(kind=type(value).__name__):
                batch=ingest_jsonl(json.dumps(dict(series='sample',period=0,value=value)))
                self.assertFalse(batch.ok)
        for token in ('NaN','Infinity','-Infinity','1e999'):
            self.assertFalse(ingest_jsonl('{"series":"sample","period":0,"value":'+token+'}').ok)

    def test_period_and_identifier_domains_are_explicit(self):
        for changes in (dict(period=True),dict(period=-1),dict(period='1'),dict(period=1000001),dict(series='\u212a'),dict(series='bad/name'),dict(series='')):
            self.assertFalse(ingest_jsonl(json.dumps(dict(series='sample',period=0,value=1)|changes)).ok)

    def test_empty_blank_and_malformed_records_are_review_items(self):
        for text in ('','\n','{FICTIONAL_DO_NOT_ECHO','[]','null'):
            batch=ingest_jsonl(text)
            self.assertFalse(batch.ok)
            self.assertNotIn('FICTIONAL_DO_NOT_ECHO',repr(batch))
        self.assertEqual(ingest_jsonl(rows(1)+'\n\n').issues[0].record,2)

    def test_text_byte_and_row_limits_fail_with_fixed_codes(self):
        for value in (None,b'fictional','\x00','\ud800'):
            with self.assertRaises(ReferenceError):ingest_jsonl(value)
        with self.assertRaisesRegex(ReferenceError,'INPUT_BYTE_LIMIT'):ingest_jsonl(' '*65537)
        with self.assertRaisesRegex(ReferenceError,'INPUT_BYTE_LIMIT'):ingest_jsonl('\u03bb'*32769)
        with self.assertRaisesRegex(ReferenceError,'INPUT_RECORD_LIMIT'):ingest_jsonl('\n'.join(rows(1) for _ in range(257)))

    def test_series_count_limit_does_not_silently_select_a_subset(self):
        text='\n'.join(json.dumps(dict(series='s'+str(index),period=0,value=1)) for index in range(33))
        batch=ingest_jsonl(text)
        self.assertEqual(len(batch.records),32)
        self.assertEqual(batch.issues[0].code,'SERIES_COUNT_LIMIT')
        with self.assertRaises(ReferenceError):batch.require_clean()

    def test_csv_header_width_and_syntax_are_strict(self):
        for text in ('','value,period,series\n1,0,sample','series,series,value\na,b,1','series,period,value\n"unterminated'):
            with self.assertRaises(ReferenceError):ingest_csv(text)
        self.assertFalse(ingest_csv('series,period,value\nsample,0,1,extra').ok)
        self.assertFalse(ingest_csv('series,period,value\nsample,,1').ok)
        self.assertFalse(ingest_csv('series,period,value\nsample,0,NaN').ok)

    def test_records_and_batch_are_immutable_and_negative_zero_is_canonical(self):
        point=Point('sample',0,-0.0)
        self.assertEqual(math.copysign(1,point.value),1)
        with self.assertRaises(FrozenInstanceError):point.value=2
        batch=ingest_jsonl(rows(1))
        with self.assertRaises(FrozenInstanceError):batch.duplicates=3


class DemoTests(unittest.TestCase):
    def test_demo_is_deterministic_and_only_uses_fictional_records(self):
        with mock.patch('builtins.open',side_effect=AssertionError('FILE_OPENED')),mock.patch.object(socket,'socket',side_effect=AssertionError('NETWORK')),mock.patch.object(subprocess,'run',side_effect=AssertionError('PROCESS')):
            first=run_demo();second=run_demo()
        self.assertEqual(first,second)
        self.assertEqual(first['mode'],'FICTIONAL_INGESTION_DEMO')
        self.assertTrue(first['format_results_equal'])
        self.assertEqual(first['clean'],dict(accepted=6,duplicates=1,issues=0,ready=True))
        self.assertEqual(first['review'],dict(accepted=6,duplicates=1,issues=[dict(record=8,code='RECORD_CONFLICT')],ready=False))
        self.assertEqual(first['downstream_gate'],'BATCH_REVIEW_REQUIRED')
        self.assertEqual(first['application_files_written'],0)

    def test_actual_cli_writes_no_files_and_preserves_source(self):
        def hashes():return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*.py')}
        before=hashes()
        with tempfile.TemporaryDirectory(prefix='fictional-ingestion-',dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            result=subprocess.run([sys.executable,'-B',str(ROOT/'demo.py'),'--demo'],cwd=folder,capture_output=True,text=True,timeout=15)
            self.assertEqual((result.returncode,result.stderr),(0,''))
            self.assertEqual(json.loads(result.stdout),run_demo())
            self.assertEqual(list(Path(folder).iterdir()),[])
        self.assertEqual(hashes(),before)

    def test_cli_invalid_arguments_do_not_echo_supplied_values(self):
        result=subprocess.run([sys.executable,'-B',str(ROOT/'demo.py'),'--unknown','FICTIONAL_DO_NOT_ECHO'],capture_output=True,text=True,timeout=15)
        self.assertEqual((result.returncode,result.stderr),(2,''))
        self.assertEqual(json.loads(result.stdout),dict(status='ERROR',code='ARGUMENTS_INVALID'))
        self.assertNotIn('FICTIONAL_DO_NOT_ECHO',result.stdout)

    def test_static_help_has_no_source_or_workstation_path(self):
        for args in ([],['--help']):
            result=subprocess.run([sys.executable,'-B',str(ROOT/'demo.py'),*args],capture_output=True,text=True,timeout=15)
            self.assertEqual((result.returncode,result.stderr),(0,''))
            self.assertIn('record-ingestion',result.stdout)
            self.assertNotIn(str(ROOT),result.stdout)


if __name__=='__main__':unittest.main()
