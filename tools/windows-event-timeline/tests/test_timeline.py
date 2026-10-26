from pathlib import Path
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'examples'))
import generate as fixtures
from event_timeline import inspect,main,timestamp,NAMESPACE
from inspection_support import TextError


def record(**changes):
    return {'provider':'Example.Demo','event_id':100,'time_created':'2026-01-01T00:00:00Z',
            'computer':'FictionalComputer','channel':'Example/Diagnostic','record_id':1,**changes}


def run(events,gap=300,details=False):
    return inspect([('input-0001',json.dumps({'schema_version':1,'events':events}).encode())],'json',gap,details)


def xml(body):return '<Events><Event xmlns="'+NAMESPACE+'"><System>'+body+'</System></Event></Events>'
SYSTEM='<Provider Name="Example.Demo"/><EventID>100</EventID><TimeCreated SystemTime="2026-01-01T00:00:00Z"/>'


class TimelineTests(unittest.TestCase):
    def codes(self,report,coverage=False):return {r['code'] for r in report['coverage_issues' if coverage else 'findings']}

    def test_clean_grouped_metadata_and_private_default(self):
        report=run([record(),record(record_id=2,time_created='2026-01-01T00:00:30Z')])
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertEqual(report['repeated_groups'],1)
        self.assertEqual(report['groups'][0]['count'],2)
        text=json.dumps(report)
        for value in ('FictionalComputer','Example.Demo','Example/Diagnostic','2026-01-01'):self.assertNotIn(value,text)

    def test_details_include_selected_fields_but_never_computer(self):
        report=run([record()],details=True);text=json.dumps(report)
        self.assertIn('Example.Demo',text);self.assertIn('2026-01-01',text);self.assertNotIn('FictionalComputer',text)

    def test_timestamp_offsets_and_fraction_precision(self):
        left=timestamp('2026-01-01T01:00:00.1234567+01:00');right=timestamp('2026-01-01T00:00:00.1234567Z')
        self.assertEqual(left,right);self.assertTrue(left[1].endswith('.1234567Z'))
        report=run([record(time_created='2026-01-01T00:00:00.0000002Z'),record(record_id=2,time_created='2026-01-01T00:00:00.0000001Z')])
        self.assertEqual(report['timeline'][1]['delta_100ns'],'1');self.assertFalse(report['input_order_was_chronological'])

    def test_timestamp_rejections_no_local_zone_guess(self):
        for value in ('2026-01-01T00:00:00','2026-01-01T00:00:00-00:00','2026-01-01T00:00:00+14:01','2026-02-30T00:00:00Z','2026-01-01T00:00:60Z','2026-01-01T00:00:00.12345678Z','0000-01-01T00:00:00Z','2026-01-01t00:00:00z'):
            with self.assertRaises(TextError,msg=value):timestamp(value)

    def test_pre_epoch_and_minimum_year_formatting(self):
        self.assertEqual(timestamp('1969-12-31T23:59:59.9999999Z')[0],-1)
        self.assertTrue(timestamp('0001-01-01T00:00:00Z')[1].startswith('0001-'))

    def test_wide_intervals_and_record_ids_are_exact_decimal_strings(self):
        report=run([record(time_created='1900-01-01T00:00:00Z',record_id=2**64-1),record(record_id=2)],gap=0,details=True)
        self.assertEqual(report['timeline'][0]['record_id'],'18446744073709551615')
        self.assertEqual(int(report['timeline'][1]['elapsed_100ns']),timestamp('2026-01-01T00:00:00Z')[0]-timestamp('1900-01-01T00:00:00Z')[0])

    def test_stable_timestamp_ties(self):
        report=run([record(event_id=102,record_id=2),record(event_id=101,record_id=3)])
        self.assertEqual([r['event_id'] for r in report['timeline']],[102,101]);self.assertFalse(report['findings'])

    def test_gap_threshold_strict_and_disabled(self):
        self.assertFalse(run([record(),record(record_id=2,time_created='2026-01-01T00:05:00Z')])['gaps'])
        report=run([record(),record(record_id=2,time_created='2026-01-01T00:05:00.0000001Z')])
        self.assertEqual(len(report['gaps']),1);self.assertIn('DECLARED_TIME_GAP_EXCEEDS_THRESHOLD',self.codes(report))
        self.assertFalse(run([record(),record(record_id=2,time_created='2026-01-02T00:00:00Z')],gap=0)['gaps'])

    def test_duplicate_and_conflicting_declared_record_id(self):
        self.assertIn('DUPLICATE_EXPORTED_RECORD',self.codes(run([record(),record()])))
        self.assertIn('CONFLICTING_EXPORTED_RECORD_ID',self.codes(run([record(),record(event_id=101)])))

    def test_record_identity_does_not_merge_computers_channels_or_files(self):
        self.assertFalse(run([record(),record(computer='OtherFictionalComputer'),record(channel='Other/Channel')])['findings'])
        data=json.dumps({'schema_version':1,'events':[record()]}).encode()
        report=inspect([('input-0001',data),('input-0002',data)],'json')
        self.assertFalse(report['findings'])

    def test_missing_computer_or_channel_prevents_duplicate_inference(self):
        for changes in ({'computer':None},{'channel':None},{'record_id':None}):
            self.assertFalse(run([record(**changes),record(**changes)])['findings'])

    def test_version_guid_and_qualifiers_keep_groups_separate(self):
        events=[record(record_id=i+1,**changes) for i,changes in enumerate(({}, {'version':0},{'version':1},{'qualifiers':0},{'provider_guid':'00000000-0000-4000-8000-000000000001'}))]
        self.assertEqual(len(run(events)['groups']),5)

    def test_guid_normalization(self):
        report=run([record(provider_guid='{A0000000-0000-4000-8000-000000000001}'),record(record_id=2,provider_guid='a0000000-0000-4000-8000-000000000001')])
        self.assertEqual(len(report['groups']),1)

    def test_bad_record_is_coverage_not_silent_clean(self):
        for changes in ({'event_id':True},{'event_id':65536},{'record_id':-1},{'level':256},{'version':True},{'provider':''},{'provider_guid':'not-guid'},{'time_created':'naive'}):
            report=run([record(**changes)])
            self.assertTrue(report['coverage_issues']);self.assertEqual(report['status'],'REVIEW_REQUIRED');self.assertFalse(report['timeline'])

    def test_unknown_json_fields_are_not_embedded(self):
        report=run([record(message='fictional_payload_marker')],details=True)
        self.assertIn('UNINSPECTED_EVENT_FIELDS',self.codes(report,True));self.assertNotIn('fictional_payload_marker',json.dumps(report))

    def test_json_schema_duplicate_keys_and_limits(self):
        for data in (b'{}',b'{"schema_version":true,"events":[]}',b'{"schema_version":1,"events":[],"events":[]}',b'{"schema_version":1,"events":[NaN]}'):
            with self.assertRaises(TextError):inspect([('input-0001',data)],'json')
        with self.assertRaisesRegex(TextError,'EVENT_COUNT_LIMIT'):run([record()]*4001)

    def test_json_bom_and_empty_supported_export(self):
        report=inspect([('input-0001',b'\xef\xbb\xbf{"schema_version":1,"events":[]}')],'json')
        self.assertEqual(report['status'],'NO_SCOPE_FINDINGS');self.assertFalse(report['timeline'])

    def test_json_xml_fixture_equivalence_and_payload_omission(self):
        left=inspect([('input-0001',fixtures.FILES['clean.json'].encode())],'json',details=True)
        right=inspect([('input-0001',fixtures.FILES['clean.xml'].encode())],'xml',details=True)
        self.assertEqual(left['timeline'],right['timeline']);self.assertEqual(left['groups'],right['groups'])
        self.assertNotIn('fictional_payload_marker',json.dumps(right));self.assertEqual(right['status'],'NO_SCOPE_FINDINGS')

    def test_single_event_and_unnamespaced_xml(self):
        text=xml(SYSTEM).replace('<Events>','').replace('</Events>','')
        self.assertEqual(len(inspect([('input-0001',text.encode())],'xml')['timeline']),1)
        text=xml(SYSTEM).replace(' xmlns="'+NAMESPACE+'"','')
        self.assertEqual(inspect([('input-0001',text.encode())],'xml')['status'],'NO_SCOPE_FINDINGS')

    def test_unknown_namespace_prefix_and_namespace_reset_not_guessed(self):
        for text in (xml(SYSTEM).replace(NAMESPACE,'urn:fictional'),xml(SYSTEM).replace('<Provider ','<Provider xmlns="" '),'<e:Event xmlns:e="'+NAMESPACE+'"/>'):
            report=inspect([('input-0001',text.encode())],'xml')
            self.assertEqual(report['status'],'REVIEW_REQUIRED');self.assertFalse(report['timeline'])

    def test_missing_repeated_or_nested_system_fields(self):
        for body in ('<EventID>100</EventID>',SYSTEM+'<EventID>101</EventID>',SYSTEM.replace('<EventID>100</EventID>','<EventID><Nested/></EventID>')):
            self.assertTrue(inspect([('input-0001',xml(body).encode())],'xml')['coverage_issues'])

    def test_xml_unknown_fields_mixed_text_and_processing_instructions(self):
        for text in (xml(SYSTEM+'<Unknown/>'),xml('mixed'+SYSTEM),xml(SYSTEM).replace('<Events>','<Events>mixed'),xml(SYSTEM).replace('<Provider ','<Provider Extra="fictional" '),'<?fiction note?>'+xml(SYSTEM)):
            self.assertTrue(inspect([('input-0001',text.encode())],'xml')['coverage_issues'])

    def test_xml_encoded_control_in_identity_rejected_without_leaking(self):
        text=xml(SYSTEM.replace('Example.Demo','Example&#13;Demo'))
        report=inspect([('input-0001',text.encode())],'xml')
        self.assertTrue(report['coverage_issues']);self.assertFalse(report['timeline'])

    def test_xml_declarations_and_malformed_syntax_fail_closed(self):
        for text in ('<!DOCTYPE Events SYSTEM "file:///fictional/not-opened">'+xml(SYSTEM),'<Events>','<?xml version="1.0" encoding="UTF-16"?>'+xml(SYSTEM)):
            with self.assertRaises(TextError):inspect([('input-0001',text.encode())],'xml')

    def test_no_log_or_network_or_native_xml_import(self):
        import builtins
        original=builtins.__import__
        def guard(name,*args,**kwargs):
            if name.split('.')[0] in {'xml','pyexpat','win32evtlog','subprocess','socket','urllib'}:raise AssertionError('Unexpected runtime dependency')
            return original(name,*args,**kwargs)
        with patch.object(builtins,'__import__',side_effect=guard):self.assertEqual(inspect([('input-0001',xml(SYSTEM).encode())],'xml')['status'],'NO_SCOPE_FINDINGS')

    def test_actual_cli_examples_report_manifest_and_input_immutability(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve()
            subprocess.run([sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(base/'fixtures')],check=True,capture_output=True)
            for name,kind,expected in [('clean','json',0),('review','json',1),('clean','xml',0),('review','xml',1)]:
                source=base/f'fixtures/{name}.{kind}';before=source.read_bytes();out=base/f'{name}-{kind}'
                result=subprocess.run([sys.executable,'-B',str(ROOT/'event_timeline.py'),'--file',str(source),'--format',kind,'--output',str(out)],capture_output=True,text=True)
                self.assertEqual(result.returncode,expected,result.stdout+result.stderr);self.assertNotIn(str(base),result.stdout);self.assertEqual(source.read_bytes(),before)
                for row in json.loads((out/'MANIFEST.json').read_text())['files']:
                    self.assertEqual(hashlib.sha256((out/row['path']).read_bytes()).hexdigest(),row['sha256'])

    def test_error_output_is_fixed_and_detailed_html_is_escaped(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve();source=base/'events.json';source.write_text(json.dumps({'schema_version':1,'events':[record(provider='<script>fictional</script>')]}),encoding='utf-8')
            capture=io.StringIO();args=['--file',str(source),'--format','json','--output',str(base/'out'),'--include-details']
            with contextlib.redirect_stdout(capture):self.assertEqual(main(args),0)
            self.assertNotIn('<script>',(base/'out/report.html').read_text());self.assertIn('&lt;script&gt;',(base/'out/report.html').read_text())
            with contextlib.redirect_stdout(capture):self.assertEqual(main(args),2)
            self.assertNotIn(str(base),capture.getvalue())


if __name__=='__main__':unittest.main()
