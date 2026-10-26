"""Generated observations, actual subprocess bounds and privacy contracts."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import usb_core as core
import usb_windows as native
from inspection_support import TextError

DEVICE = 'USB\\FICTIONAL_DEVICE\\DEMO_ONLY'


class ClockStop:
    def __init__(self):
        self.time = 0
        self.stopped = False
    def is_set(self):
        return self.stopped
    def wait(self, seconds):
        self.time += seconds
        return self.stopped


class CoreTests(unittest.TestCase):
    def session(self):
        return core.Session('demo')

    def test_reconnect_demo_counts_and_observed_changes(self):
        result = core.demo('reconnect')
        self.assertEqual(result['sample_counts'], {'present': 4, 'absent': 2, 'unknown': 0})
        self.assertEqual([row['kind'] for row in result['events']],
                         ['initial_present', 'disconnected_observed', 'reconnected_observed'])
        self.assertEqual(core.validate_report(result), result)

    def test_unknown_resumption_does_not_invent_a_disconnect(self):
        result = core.demo('query-gap')
        kinds = [row['kind'] for row in result['events']]
        self.assertNotIn('disconnected_observed', kinds)
        self.assertIn('observation_resumed_absent', kinds)
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')

    def test_initial_absence_is_not_a_disconnect(self):
        session = self.session();session.observe(0, False)
        self.assertEqual(session.report()['events'][0]['kind'], 'initial_absent')

    def test_repeated_states_do_not_add_transition_events(self):
        session = self.session()
        for index in range(6):session.observe(index, True)
        self.assertEqual(len(session.report()['events']), 1)
        self.assertEqual(session.report()['sample_counts']['present'], 6)

    def test_empty_session_requires_review(self):
        self.assertEqual(self.session().report()['status'], 'REVIEW_REQUIRED')

    def test_invalid_observation_types_and_codes_refused(self):
        for elapsed, present, code in [(True, True, None), (-1, True, None), (0, 1, None),
                                       (0, None, None), (0, True, 'QUERY_FAILED'),
                                       (0, None, 'private exception text')]:
            with self.subTest(values=(elapsed, present, code)):
                with self.assertRaises(TextError):self.session().observe(elapsed, present, code)

    def test_time_must_be_ordered_and_bounded(self):
        session = self.session();session.observe(100, True)
        with self.assertRaises(TextError):session.observe(99, False)
        with self.assertRaises(TextError):session.observe(core.MAX_ELAPSED_MS + 1, True)
        self.assertEqual(len(session.samples), 1)

    def test_sample_limit_does_not_truncate_silently(self):
        session = self.session()
        with patch.object(core, 'MAX_SAMPLES', 1):
            session.observe(0, True)
            with self.assertRaises(TextError):session.observe(1, False)
        self.assertEqual(len(session.samples), 1)

    def test_settings_refuse_nonfinite_and_out_of_range(self):
        for seconds, interval in [(float('nan'), 1), (1, float('inf')), (True, 1),
                                  (0, 1), (3601, 1), (1, .49), (1, 61)]:
            with self.assertRaises(TextError):core.Settings(seconds, interval).validate()

    def test_report_copies_cannot_modify_session(self):
        session = self.session();session.observe(0, True)
        result = session.report();result['samples'][0]['state'] = 'absent'
        result['sample_counts']['present'] = 999
        self.assertEqual(session.report()['samples'][0]['state'], 'present')
        self.assertEqual(session.report()['sample_counts']['present'], 1)

    def test_replay_schema_and_extra_identity_fields_refused(self):
        value = {'schema': 'outlands-usb-samples/1', 'samples': [
            {'elapsed_ms': 0, 'present': True, 'code': None}]}
        self.assertEqual(core.replay(value)['mode'], 'replay')
        for changed in [dict(value, name='private'), dict(value, samples=[]), dict(value, schema=2)]:
            with self.assertRaises(TextError):core.replay(changed)
        value['samples'][0]['id'] = DEVICE
        with self.assertRaises(TextError):core.replay(value)

    def test_replay_rejects_duplicate_keys_and_float_times(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'samples.json'
            for data in [b'{"schema":1,"schema":2}', b'{"schema":"outlands-usb-samples/1","samples":[{"elapsed_ms":0.0,"present":true,"code":null}]}']:
                target.write_bytes(data)
                with self.assertRaises(TextError):core.replay_file(target)

    def test_export_is_fresh_and_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'report.json'
            result = core.demo();core.export_report(target, result)
            self.assertEqual(json.loads(target.read_text()), result)
            before = target.read_bytes()
            with self.assertRaises(TextError):core.export_report(target, core.demo('stable'))
            self.assertEqual(target.read_bytes(), before)

    def test_export_refuses_extra_metadata_and_changed_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'report.json'
            for field, value in [('name', 'fictional private device'), ('status', 'invented'),
                                 ('events', []), ('privacy', {})]:
                report = core.demo();report[field] = value
                with self.assertRaises(TextError):core.export_report(target, report)
                self.assertFalse(target.exists())

    def test_reports_contain_no_selected_identity_or_clock_dates(self):
        clock = ClockStop()
        def query(stop):
            clock.time += .1
            return [{'id': DEVICE, 'name': 'Fictional private label'}]
        result = core.monitor(DEVICE, core.Settings(1, .5), query, stop=clock, clock=lambda: clock.time)
        text = json.dumps(result)
        self.assertNotIn(DEVICE, text);self.assertNotIn('Fictional private label', text)
        self.assertTrue(all(value is False for value in result['privacy'].values()))
        self.assertEqual(result['status'], 'OK')

    def test_export_schema_distinguishes_boolean_and_integer_fields(self):
        report = core.demo('stable')
        report['privacy']['instance_ids'] = 0
        with self.assertRaises(TextError):core.validate_report(report)

    def test_monitor_failure_is_unknown_not_absence(self):
        clock = ClockStop()
        def query(stop):
            clock.time += .1
            raise TextError('raw fictional private exception')
        result = core.monitor(DEVICE, core.Settings(1, .5), query, stop=clock, clock=lambda: clock.time)
        self.assertGreater(result['sample_counts']['unknown'], 0)
        self.assertEqual(result['sample_counts']['absent'], 0)
        self.assertNotIn('raw fictional', json.dumps(result))
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')

    def test_monitor_cancel_before_query_is_inert(self):
        stop = threading.Event();stop.set()
        with patch('usb_windows.query_devices') as query:
            report = core.monitor(DEVICE, core.Settings(1, .5), query, stop=stop)
        query.assert_not_called();self.assertEqual(report['outcome'], 'cancelled')

    def test_monitor_casefolds_exact_ids_without_prefix_matching(self):
        clock = ClockStop()
        def query(stop):
            clock.time += .1
            return [{'id': DEVICE+'OTHER', 'name': 'another'}]
        report = core.monitor(DEVICE.lower(), core.Settings(1, .5), query, stop=clock, clock=lambda: clock.time)
        self.assertGreater(report['sample_counts']['absent'], 0)
        self.assertEqual(report['sample_counts']['present'], 0)

    def test_unexpected_worker_error_returns_failed_review(self):
        def query(stop):raise RuntimeError('private implementation detail')
        report = core.monitor(DEVICE, core.Settings(1, .5), query)
        self.assertEqual(report['outcome'], 'failed')
        self.assertNotIn('private implementation detail', json.dumps(report))


class AdapterTests(unittest.TestCase):
    def test_parse_snapshot_empty_single_and_sorted(self):
        self.assertEqual(native.parse_snapshot(b'[]'), [])
        rows = [{'id': DEVICE, 'name': 'Zebra'}, {'id': DEVICE+'2', 'name': 'Apple'}]
        self.assertEqual(native.parse_snapshot(json.dumps(rows).encode())[0]['name'], 'Apple')
        self.assertEqual(len(native.parse_snapshot(json.dumps(rows[:1]).encode())), 1)

    def test_parse_refuses_duplicate_ids_and_unknown_fields(self):
        row = {'id': DEVICE, 'name': 'demo'}
        for data in [[row, dict(row, id=DEVICE.lower())], [dict(row, private='field')], row,
                     [{'id': 'PCI\\FICTIONAL', 'name': 'demo'}]]:
            with self.assertRaises(TextError):native.parse_snapshot(json.dumps(data).encode())

    def test_parse_refuses_bad_json_controls_and_sizes(self):
        for data in [b'{', b'[{"id":"one","id":"two","name":"demo"}]',
                     json.dumps([{'id': DEVICE, 'name': 'x\nprivate'}]).encode(),
                     json.dumps([{'id': DEVICE, 'name': 'x'*257}]).encode()]:
            with self.assertRaises(TextError):native.parse_snapshot(data)
        with self.assertRaises(TextError):native.parse_snapshot(b'x'*(native.MAX_OUTPUT+1))

    def test_parse_refuses_device_count_overflow(self):
        rows = [{'id': DEVICE+str(i), 'name': 'demo'} for i in range(513)]
        with self.assertRaises(TextError):native.parse_snapshot(json.dumps(rows).encode())

    def test_fixed_query_contains_no_selection_or_mutation_commands(self):
        self.assertIn('-PresentOnly', native.SCRIPT)
        self.assertNotIn(DEVICE, native.SCRIPT)
        for action in ['Disable-PnpDevice', 'Enable-PnpDevice', 'pnputil', 'logman', 'Set-ExecutionPolicy']:
            self.assertNotIn(action, native.SCRIPT)

    def test_real_child_output_is_bounded(self):
        command = [sys.executable, '-B', '-c', 'import sys;sys.stdout.buffer.write(b"x"*200000);sys.stdout.flush()']
        with self.assertRaises(TextError) as error:native.bounded_process(command, maximum=4096)
        self.assertEqual(str(error.exception), 'QUERY_OUTPUT_LIMIT')

    def test_real_child_timeout_is_terminated(self):
        started = time.monotonic()
        with self.assertRaises(TextError) as error:
            native.bounded_process([sys.executable, '-B', '-c', 'import time;time.sleep(30)'], timeout=.2)
        self.assertEqual(str(error.exception), 'QUERY_TIMEOUT')
        self.assertLess(time.monotonic()-started, 4)

    def test_real_child_cancellation_is_terminated(self):
        stop = threading.Event();timer = threading.Timer(.15, stop.set);timer.start()
        try:
            with self.assertRaises(TextError) as error:
                native.bounded_process([sys.executable, '-B', '-c', 'import time;time.sleep(30)'], stop=stop)
        finally:timer.join()
        self.assertEqual(str(error.exception), 'CANCELLED')

    def test_real_child_failure_does_not_forward_stderr(self):
        with self.assertRaises(TextError) as error:
            native.bounded_process([sys.executable, '-B', '-c', 'import sys;sys.stderr.write("private text");sys.exit(7)'])
        self.assertEqual(str(error.exception), 'QUERY_FAILED')

    def test_real_child_success_and_unicode_bytes(self):
        result = native.bounded_process([sys.executable, '-B', '-c', 'import sys;sys.stdout.buffer.write("fictional ü".encode())'])
        self.assertEqual(result.decode(), 'fictional ü')

    @unittest.skipUnless(os.name == 'nt', 'Windows adapter location only')
    def test_windows_executable_uses_absolute_system_path(self):
        path = native.powershell_path()
        self.assertTrue(path.is_absolute());self.assertTrue(path.is_file())
        self.assertEqual(path.name.lower(), 'powershell.exe')

    @unittest.skipUnless(os.name == 'nt' and os.environ.get('USB_MONITOR_REQUIRE_NATIVE_QUERY') == '1',
                         'Explicit native read-only query qualification only')
    def test_actual_windows_readonly_pnp_query(self):
        result = native.query_devices()
        self.assertIsInstance(result, list);self.assertLessEqual(len(result), native.MAX_DEVICES)

    @unittest.skipIf(os.name == 'nt', 'Non-Windows refusal')
    def test_live_platform_refuses_without_launching_child(self):
        with patch.object(subprocess, 'Popen') as child:
            with self.assertRaises(TextError) as error:native.query_devices()
        self.assertEqual(str(error.exception), 'WINDOWS_REQUIRED');child.assert_not_called()


if __name__ == '__main__':unittest.main()
