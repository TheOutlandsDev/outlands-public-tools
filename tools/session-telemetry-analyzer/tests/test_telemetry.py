"""Original synthetic telemetry and actual CLI checks; no game or real logs. MIT."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import telemetry_analyzer as tool
from inspection_support import TextError


def event(kind='snapshot', **payload): return {'type': kind, 'payload': payload}


def records(*rows):
    return ('\n'.join(json.dumps(row, ensure_ascii=True) for row in rows)+'\n').encode('utf-8')


def inspect(data): return tool.summarize([('input-0001', data)])


def codes(report): return {row['code'] for row in report['coverage_issues']+report['findings']}


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve(); self.input = self.base/'fictional.jsonl'

    def test_independent_valid_sample_denominators(self):
        report = inspect(records(event(player_count=2, bot_count=4, tracking={'active_count':3}),
                                 event(player_count=4), event(bot_count=8, tracking={'active_count':1})))
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        capture = report['captures'][0]
        self.assertEqual(capture['event_counts']['snapshot'], 3)
        self.assertEqual(capture['populations']['players'], {'samples':2,'missing_samples':1,'invalid_samples':0,
                         'sum':'6','maximum':4,'sample_mean':{'numerator':'6','denominator':2}})
        self.assertEqual(capture['populations']['bots']['sample_mean'], {'numerator':'12','denominator':2})
        self.assertEqual(capture['populations']['tracked_active']['sample_mean'], {'numerator':'4','denominator':2})

    def test_zero_is_a_valid_observation_but_absence_is_not(self):
        capture = inspect(records(event(player_count=0), event()))['captures'][0]
        self.assertEqual(capture['populations']['players']['samples'],1)
        self.assertEqual(capture['populations']['players']['maximum'],0)
        self.assertEqual(capture['populations']['players']['sample_mean'], {'numerator':'0','denominator':1})
        self.assertIsNone(capture['populations']['bots']['maximum'])
        self.assertIsNone(capture['populations']['bots']['sample_mean'])

    def test_invalid_population_types_are_excluded(self):
        rows = [event(player_count=x) for x in (True,False,None,'5',1.0,-1,1000000001)]
        report = inspect(records(*rows, event(player_count=5)))
        row = report['captures'][0]['populations']['players']
        self.assertEqual((row['samples'],row['invalid_samples'],row['sum']), (1,7,'5'))
        self.assertIn('POPULATION_VALUE_INVALID',codes(report))
        self.assertEqual(report['status'],'REVIEW_REQUIRED')

    def test_missing_and_invalid_tracking_container(self):
        report = inspect(records(event(),event(tracking={}),event(tracking=None),event(tracking=[]),event(tracking={'active_count':2})))
        row = report['captures'][0]['populations']['tracked_active']
        self.assertEqual((row['samples'],row['missing_samples'],row['invalid_samples']), (1,2,2))
        self.assertIn('POPULATION_CONTAINER_INVALID',codes(report))

    def test_line_of_sight_boolean_denominators(self):
        report = inspect(records(event(line_of_sight=[{'main_can_see_bot':True},{'main_can_see_bot':False},
                                                      {},{'main_can_see_bot':1},None]),event(),event(line_of_sight=[])))
        row = report['captures'][0]['line_of_sight']
        self.assertEqual((row['present_collections'],row['missing_collections'],row['declared_entries']), (2,1,5))
        self.assertEqual((row['valid_boolean_samples'],row['visible_samples'],row['missing_entry_values'],row['invalid_entry_values']), (2,1,1,2))
        self.assertEqual(row['visible_fraction'], {'numerator':'1','denominator':2})
        self.assertIn('LOS_VALUE_INVALID',codes(report)); self.assertIn('LOS_ENTRY_INVALID',codes(report))

    def test_invalid_los_container_not_coerced(self):
        report = inspect(records(event(line_of_sight=None),event(line_of_sight={'main_can_see_bot':True})))
        row = report['captures'][0]['line_of_sight']
        self.assertEqual(row['invalid_collections'],2)
        self.assertIsNone(row['visible_fraction'])
        self.assertIn('LOS_COLLECTION_INVALID',codes(report))

    def test_los_entry_limit_before_processing_collection(self):
        data=records(event(line_of_sight=[{}]*257))
        with self.assertRaisesRegex(TextError,'^LOS_ENTRY_LIMIT$'): inspect(data)

    def test_single_end_declared_zero_is_not_missing(self):
        report=inspect(records(event('raid_start'), event(), event('raid_end',dropped_lines=0)))
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
        row=report['captures'][0]['dropped_data']
        self.assertEqual(row['state'],'declared'); self.assertEqual(row['declared_dropped_lines'],'0')

    def test_dropped_data_requires_review(self):
        report=inspect(records(event('raid_end',dropped_lines=7)))
        self.assertEqual(report['captures'][0]['dropped_data']['declared_dropped_lines'],'7')
        self.assertIn('DECLARED_DROPPED_LINES',codes(report))
        self.assertEqual(report['status'],'REVIEW_REQUIRED')

    def test_multiple_end_rows_do_not_sum_or_pick_a_winner(self):
        for final in (event('raid_end',dropped_lines=7),event('raid_end')):
            with self.subTest(final=final):
                report=inspect(records(event('raid_end',dropped_lines=7),final))
                row=report['captures'][0]['dropped_data']
                self.assertEqual(row['state'],'ambiguous_multiple_end_rows')
                self.assertIsNone(row['declared_dropped_lines'])
                self.assertIn('MULTIPLE_END_MARKERS',codes(report))

    def test_invalid_drop_declarations_exact_types_bounds(self):
        for value in (True,None,'3',1.0,-1,1000000000001):
            with self.subTest(value=value):
                report=inspect(records(event('raid_end',dropped_lines=value)))
                row=report['captures'][0]['dropped_data']
                self.assertEqual(row['state'],'invalid'); self.assertEqual(row['invalid_declarations'],1)
                self.assertIsNone(row['declared_dropped_lines'])

    def test_unobserved_end_and_drop_fields_remain_unspecified(self):
        for data in (records(event()), records(event('raid_end'))):
            report=inspect(data)
            self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')
            self.assertEqual(report['captures'][0]['dropped_data']['state'],'unspecified')
            self.assertIsNone(report['captures'][0]['dropped_data']['declared_dropped_lines'])

    def test_multiple_start_markers_explicit(self):
        report=inspect(records(event('raid_start'),event('raid_start')))
        self.assertIn('MULTIPLE_START_MARKERS',codes(report))

    def test_decimal_seconds_exact_no_binary_float_conversion(self):
        data=b'{"type":"snapshot","payload":{"raid_seconds":0.1000000000000000000000000001}}\n'
        report=inspect(data)
        self.assertEqual(report['captures'][0]['declared_time']['last_in_file_seconds'],'0.1000000000000000000000000001')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')

    def test_decimal_exponent_seconds_and_decrease_are_declarations(self):
        data=(b'{"type":"snapshot","payload":{"raid_seconds":1e2}}\n'
              b'{"type":"snapshot","payload":{"raid_seconds":99.9}}\n')
        report=inspect(data)
        self.assertEqual(report['captures'][0]['declared_time']['last_in_file_seconds'],'99.9')
        self.assertIn('DECLARED_TIME_DECREASE',codes(report))

    def test_invalid_seconds_do_not_reset_last_valid_declaration(self):
        rows=[event(raid_seconds=5)]+[event(raid_seconds=x) for x in (True,None,'6',-1,315360001)]
        report=inspect(records(*rows))
        self.assertEqual(report['captures'][0]['declared_time'], {'valid_declarations':1,'invalid_declarations':5,'last_in_file_seconds':'5'})
        self.assertIn('DECLARED_SECONDS_INVALID',codes(report))

    def test_duplicate_keys_nonfinite_and_json_syntax_reported(self):
        values=[b'{"type":"snapshot","type":"raid_end","payload":{}}',
                b'{"type":"snapshot","payload":{"player_count":1,"player_count":2}}',
                b'{"type":"snapshot","payload":{"raid_seconds":NaN}}',
                b'{"type":"snapshot","payload":{"raid_seconds":Infinity}}',b'{unfinished']
        report=inspect(b'\n'.join(values)+b'\n'+records(event(player_count=3)))
        self.assertEqual(report['captures'][0]['malformed_json_rows'],5)
        self.assertEqual(report['captures'][0]['populations']['players']['sum'],'3')
        self.assertTrue({'DUPLICATE_JSON_KEY','JSON_NONFINITE_UNSUPPORTED','INVALID_JSON'} <= codes(report))

    def test_scalar_root_and_missing_payload_are_invalid_envelopes(self):
        data=records(None,[],3,{}, {'type':3,'payload':{}},{'type':'snapshot'}, {'type':'snapshot','payload':None})
        report=inspect(data)
        self.assertEqual(report['captures'][0]['invalid_envelope_rows'],7)
        self.assertEqual(report['captures'][0]['accepted_events'],0)
        self.assertIn('NO_SUPPORTED_EVENTS',codes(report))

    def test_unknown_types_and_fields_are_coverage_with_supported_metrics(self):
        row=event(player_count=4, private_unknown='PRIVATE_PAYLOAD', tracking={'active_count':2,'secret':'PRIVATE_TRACK'},
                  line_of_sight=[{'main_can_see_bot':True,'secret':'PRIVATE_LOS'}])
        row['secret_root']='PRIVATE_ROOT'
        report=inspect(records(row,event('PRIVATE_TYPE')))
        self.assertEqual(report['captures'][0]['populations']['players']['sum'],'4')
        self.assertEqual(report['captures'][0]['unsupported_event_rows'],1)
        self.assertTrue({'ENVELOPE_FIELDS_UNSUPPORTED','PAYLOAD_FIELDS_UNSUPPORTED','TRACKING_FIELDS_UNSUPPORTED','LOS_FIELDS_UNSUPPORTED','EVENT_TYPE_UNSUPPORTED'} <= codes(report))
        self.assertNotIn('PRIVATE',json.dumps(report))

    def test_map_and_payload_identifiers_not_emitted(self):
        report=inspect(records(event(map='PRIVATE_MAP',player_count=1),event('tracking_assigned')))
        self.assertNotIn('PRIVATE_MAP',json.dumps(report))
        self.assertEqual(report['captures'][0]['event_counts']['tracking_assigned'],1)
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS')

    def test_no_cross_file_pooling_or_deduplication(self):
        data=records(event(player_count=2))
        report=tool.summarize([('input-0001',data),('input-0002',data)])
        self.assertEqual(len(report['captures']),2)
        self.assertEqual(report['nonblank_records_observed'],2)
        self.assertEqual([row['populations']['players']['sum'] for row in report['captures']],['2','2'])
        self.assertEqual(report['sources'][0]['sha256'],report['sources'][1]['sha256'])

    def test_repeated_records_are_observations_not_unique_entities(self):
        row=event(player_count=5)
        report=inspect(records(row,row))
        self.assertEqual(report['captures'][0]['populations']['players']['samples'],2)
        self.assertEqual(report['captures'][0]['populations']['players']['sum'],'10')

    def test_terminal_newline_and_crlf_no_extra_json_row(self):
        row=records(event())
        for data in (row,row.rstrip(b'\n'),row.replace(b'\n',b'\r\n')):
            capture=inspect(data)['captures'][0]
            self.assertEqual((capture['physical_lines'],capture['nonblank_rows'],capture['blank_rows']), (1,1,0))

    def test_blank_rows_and_bom_extensions_explicit(self):
        report=inspect(b'\xef\xbb\xbf'+records(event())+b' \t\n')
        self.assertEqual(report['captures'][0]['blank_rows'],1)
        self.assertTrue({'UTF8_BOM_EXTENSION','BLANK_RECORD_LINE'} <= codes(report))

    def test_empty_capture_requires_review(self):
        report=inspect(b'')
        self.assertIn('NO_SUPPORTED_EVENTS',codes(report))
        self.assertEqual(report['status'],'REVIEW_REQUIRED')
        self.assertEqual(report['captures'][0]['physical_lines'],0)
        self.assertEqual(report['captures'][0]['blank_rows'],0)

    def test_decoded_controls_not_output_or_silently_accepted(self):
        data=b'{"type":"snapshot","payload":{"map":"\\u202eprivate"}}\n'
        report=inspect(data)
        self.assertIn('JSON_TEXT_UNSUPPORTED',codes(report))
        self.assertEqual(report['captures'][0]['malformed_json_rows'],1)
        self.assertNotIn('private',json.dumps(report))

    def test_decoded_key_line_separators_are_not_accepted(self):
        for value in (b'\\u2028',b'\\u2029',b'\\u202e'):
            with self.subTest(value=value):
                report=inspect(b'{"type":"snapshot","payload":{"'+value+b'private":1}}\n')
                self.assertIn('JSON_TEXT_UNSUPPORTED',codes(report))
                self.assertEqual(report['captures'][0]['malformed_json_rows'],1)
                self.assertNotIn('private',json.dumps(report))

    def test_encoding_and_physical_limits_incomplete(self):
        for data,code in ((b'\xff','UTF8_REQUIRED'),(b'\0','TEXT_CONTROL_UNSUPPORTED'),(b'a\rb','TEXT_CONTROL_UNSUPPORTED'),
                          (b'a'*8193,'TEXT_LINE_LIMIT'),(b'\n'*20000,'TEXT_LINE_LIMIT')):
            with self.subTest(code=code):
                with self.assertRaisesRegex(TextError,'^'+code+'$'): inspect(data)

    def test_structure_string_and_numeric_resource_limits(self):
        for data,code in ((b'['*10+b'0'+b']'*10,'JSON_STRUCTURE_LIMIT'),
                          (json.dumps(['a']*1001).encode(),'JSON_STRUCTURE_LIMIT'),
                          (json.dumps({'map':'x'*1025}).encode(),'JSON_STRING_LIMIT'),
                          (b'1234567890123456789012345','JSON_NUMBER_LIMIT'),
                          (b'1e1001','JSON_NUMBER_LIMIT'),
                          (b'0.'+b'1'*65,'JSON_NUMBER_LIMIT')):
            with self.subTest(code=code):
                with self.assertRaisesRegex(TextError,'^'+code+'$'): inspect(data)

    def test_global_record_and_coverage_collection_caps(self):
        with patch.object(tool,'MAX_RECORDS',1):
            with self.assertRaisesRegex(TextError,'^TELEMETRY_RECORD_LIMIT$'): inspect(records(event(),event()))
        data=records(event('unknown'))*4000
        with self.assertRaisesRegex(TextError,'^RECORD_LIMIT$'): inspect(data)

    def test_invalid_input_count(self):
        for value in ([],[('id',b'')]*33):
            with self.assertRaisesRegex(TextError,'^INPUT_COUNT_LIMIT$'): tool.summarize(value)

    def cli(self, data, name='report', more=()):
        self.input.write_bytes(data)
        return subprocess.run([sys.executable,'-B',str(ROOT/'telemetry_analyzer.py'),'--file',str(self.input),
                               '--output',str(self.base/name),*more],capture_output=True,text=True,check=False)

    def test_cli_clean_private_reports_and_hashes(self):
        data=records(event(player_count=3,map='PRIVATE_MAP'))
        result=self.cli(data)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'NO_SCOPE_FINDINGS')
        self.assertNotIn(str(self.input),result.stdout+result.stderr)
        self.assertEqual(self.input.read_bytes(),data)
        directory=self.base/'report'
        self.assertEqual(set(p.name for p in directory.iterdir()),{'report.json','report.html','MANIFEST.json'})
        self.assertNotIn('PRIVATE_MAP',(directory/'report.json').read_text())
        for row in json.loads((directory/'MANIFEST.json').read_text())['files']:
            raw=(directory/row['path']).read_bytes()
            self.assertEqual(row['bytes'],len(raw));self.assertEqual(row['sha256'],hashlib.sha256(raw).hexdigest())

    def test_cli_review_and_incomplete_status(self):
        result=self.cli(records(event('raid_end',dropped_lines=2)))
        self.assertEqual(result.returncode,1)
        self.assertEqual(json.loads(result.stdout)['status'],'REVIEW_REQUIRED')
        result=self.cli(b'\xff','invalid')
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['error'],'UTF8_REQUIRED')
        self.assertFalse((self.base/'invalid').exists())

    def test_cli_existing_output_and_input_alias_refused(self):
        data=records(event())
        self.assertEqual(self.cli(data).returncode,0)
        again=self.cli(data)
        self.assertEqual(again.returncode,2);self.assertEqual(json.loads(again.stdout)['error'],'OUTPUT_EXISTS')
        alias=self.cli(data,'alias',['--file',str(self.input)])
        self.assertEqual(alias.returncode,2);self.assertEqual(json.loads(alias.stdout)['error'],'DUPLICATE_INPUT_FILE')
        self.assertEqual(self.input.read_bytes(),data)

    def test_cli_arguments_fixed_and_relative_path_refused(self):
        result=self.cli(records(event()),more=['--unknown-private-argument'])
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['error'],'ARGUMENTS_INVALID')
        self.assertNotIn('unknown-private',result.stdout+result.stderr)
        result=subprocess.run([sys.executable,'-B',str(ROOT/'telemetry_analyzer.py'),'--file','relative.jsonl','--output',str(self.base/'out')],capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['error'],'LOCAL_ABSOLUTE_PATH_REQUIRED')

    def test_generated_examples_actual_cli_and_fresh_generator(self):
        demo=self.base/'demo'
        command=[sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(demo)]
        result=subprocess.run(command,capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(set(p.name for p in demo.iterdir()),{'clean.jsonl','review.jsonl','missing-fields.jsonl'})
        for name,code in [('clean',0),('review',1),('missing-fields',0)]:
            result=subprocess.run([sys.executable,'-B',str(ROOT/'telemetry_analyzer.py'),'--file',str(demo/(name+'.jsonl')),
                                   '--output',str(self.base/('example-'+name))],capture_output=True,text=True,check=False)
            self.assertEqual(result.returncode,code,result.stderr)
        clean=json.loads((self.base/'example-clean/report.json').read_text())['captures'][0]
        self.assertEqual(clean['accepted_events'],6)
        self.assertEqual(clean['populations']['players']['sample_mean'],{'numerator':'6','denominator':2})
        self.assertEqual(clean['populations']['bots']['sample_mean'],{'numerator':'12','denominator':2})
        self.assertEqual(clean['populations']['tracked_active']['sample_mean'],{'numerator':'4','denominator':2})
        again=subprocess.run(command,capture_output=True,text=True,check=False)
        self.assertEqual(again.returncode,2);self.assertEqual(json.loads(again.stdout)['error'],'OUTPUT_EXISTS')


if __name__=='__main__': unittest.main()
