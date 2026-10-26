"""Generated review fixtures; no live packet capture or real OTX requests."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import monitor_core as core
import monitor_gui as gui


def row(**changes):
    value = {'source': '192.0.2.1', 'destination': '198.51.100.2', 'protocol': 'TCP',
             'source_port': 50000, 'destination_port': 443, 'bytes': 100}
    value.update(changes)
    return value


class FakeResponse:
    def __init__(self, value=None, status=200, raw=None):
        self.value = value if value is not None else {'pulse_info': {'count': 0}}
        self.status_code = status
        self.raw = raw
    def __enter__(self):return self
    def __exit__(self, *args):pass
    def iter_content(self, size):
        yield self.raw if self.raw is not None else json.dumps(self.value).encode()


class CoreTests(unittest.TestCase):
    def test_demo_has_separate_packet_and_rule_counts(self):
        result = core.demo().report()
        self.assertEqual(result['mode'], 'demo')
        self.assertEqual(result['packets_observed'], 3)
        self.assertEqual(result['packets_matching_local_rules'], 2)
        self.assertEqual(result['events'][0]['rules'], ['PORT_RULE'])
        self.assertNotIn('hosts', result)
        self.assertNotIn('192.0.2', json.dumps(result))

    def test_multiple_rules_count_one_matching_packet(self):
        model = core.Model('demo');model.observe(row(destination_port=23, bytes=3000))
        result = model.report()
        self.assertEqual(result['packets_matching_local_rules'], 1)
        self.assertEqual(len(result['events'][0]['rules']), 2)

    def test_private_details_are_explicit(self):
        model = core.demo()
        self.assertNotIn('source', model.report()['events'][0])
        self.assertIn('source', model.report(include_addresses=True)['events'][0])
        self.assertTrue(model.report(include_addresses=True)['addresses_included'])

    def test_ports_and_lengths_are_checked(self):
        for changes in [{'source_port': True}, {'destination_port': 65536}, {'bytes': -1},
                        {'bytes': True}, {'protocol': 'ICMP'}, {'source': 'hostname.invalid'}]:
            with self.assertRaises(core.MonitorError):core.normalize(row(**changes))

    def test_ipv6_and_extra_fields_refuse(self):
        with self.assertRaises(core.MonitorError):core.normalize(row(source='2001:db8::1'))
        with self.assertRaises(core.MonitorError):core.normalize(row(payload='not allowed'))

    def test_local_rule_ports_are_hints_not_verdicts(self):
        result = core.demo().report()
        self.assertIn('not a malware verdict', result['interpretation'])
        self.assertFalse(result['reputation_requests_automatic'])

    def test_host_and_event_bounds_are_reported(self):
        model = core.Model('demo')
        with patch.object(core, 'MAX_HOSTS', 1), patch.object(core, 'MAX_EVENTS', 1):
            model.observe(row(destination_port=23));model.observe(row(destination_port=23))
        result = model.report()
        self.assertEqual(result['tracked_unique_hosts'], 1)
        self.assertGreater(result['untracked_host_observations'], 0)
        self.assertEqual(result['omitted_rule_events'], 1)
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')

    def test_packet_limit_refuses_without_changing_counts(self):
        model = core.Model('demo')
        with patch.object(core, 'MAX_RECORDS', 1):
            model.observe(row())
            with self.assertRaises(core.MonitorError):model.observe(row())
        self.assertEqual(model.packets, 1)

    def test_replay_uses_exact_schema_and_leaves_input_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'packets.json'
            path.write_text(json.dumps({'schema': 'outlands-packet-metadata/1', 'packets': [row()]}))
            before = path.read_bytes()
            self.assertEqual(core.load_replay(path).packets, 1)
            self.assertEqual(path.read_bytes(), before)
            path.write_text('{"schema":1,"schema":2}')
            with self.assertRaises(core.MonitorError):core.load_replay(path)

    def test_export_never_overwrites_existing_report(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'report.json'
            report = core.demo().report();core.export_report(path, report)
            self.assertEqual(json.loads(path.read_text()), report)
            before = path.read_bytes()
            with self.assertRaises(core.MonitorError):core.export_report(path, {})
            self.assertEqual(path.read_bytes(), before)

    def test_rule_configuration_rejects_bad_values(self):
        for rules in [core.Rules((23, 23)), core.Rules((True,)), core.Rules(minimum_bytes=100, maximum_bytes=10)]:
            with self.assertRaises(core.MonitorError):rules.validate()

    def test_zero_pulses_is_an_observation_not_clean_verdict(self):
        result = core.pulse_observation(b'{"pulse_info":{"count":0}}')
        self.assertEqual(result['status'], 'OBSERVATION')
        self.assertEqual(result['reported_pulse_count'], 0)
        self.assertNotIn('malicious', result)

    def test_malformed_reputation_never_defaults_to_zero(self):
        for data in [b'{}', b'{"pulse_info":{}}', b'{"pulse_info":{"count":false}}',
                     b'{"pulse_info":{"count":-1}}', b'not JSON']:
            with self.assertRaises(core.MonitorError):core.pulse_observation(data)

    def test_private_and_nonpublic_addresses_never_reach_lookup(self):
        request = Mock()
        for ip in ['10.0.0.1', '172.31.0.1', '192.168.1.1', '127.0.0.1', '169.254.1.1',
                   '0.0.0.0', '224.0.0.1', '192.0.2.1', 'not-an-ip']:
            with self.assertRaises(core.MonitorError):core.lookup_otx(ip, allow_online=True, request=request, key='fictional_key_for_tests')
        request.assert_not_called()

    def test_lookup_requires_explicit_network_authorization(self):
        request = Mock()
        with self.assertRaises(core.MonitorError):core.lookup_otx('192.0.2.1', request=request)
        request.assert_not_called()

    def test_lookup_http_call_is_mocked_bounded_and_no_redirect(self):
        # Scope fixture bypasses only global-address classification so a reserved
        # documentation address can test request construction without a real IP.
        fake = SimpleNamespace(is_global=True, is_multicast=False, __str__=lambda:'192.0.2.1')
        class PublicFixture:
            is_global=True;is_multicast=False
            def __str__(self):return '192.0.2.1'
        request = Mock(return_value=FakeResponse({'pulse_info': {'count': 2}}))
        with patch.object(core, 'address', return_value=PublicFixture()):
            result = core.lookup_otx('192.0.2.1', allow_online=True, request=request, key='fictional_key_for_tests')
        self.assertEqual(result['reported_pulse_count'], 2)
        self.assertFalse(request.call_args.kwargs['allow_redirects'])
        self.assertEqual(request.call_args.kwargs['timeout'], (3, 5))
        self.assertNotIn('fictional_key_for_tests', json.dumps(result))

    def test_lookup_failure_does_not_emit_key_or_exception(self):
        class PublicFixture:
            is_global=True;is_multicast=False
            def __str__(self):return '192.0.2.1'
        with patch.object(core, 'address', return_value=PublicFixture()):
            with self.assertRaises(core.MonitorError) as error:
                core.lookup_otx('192.0.2.1', allow_online=True, request=Mock(side_effect=RuntimeError('private key text')),
                                key='fictional_key_for_tests')
        self.assertEqual(str(error.exception), 'OTX_LOOKUP_FAILED')

    def test_packet_adapter_decodes_only_selected_metadata(self):
        IP = 'IP'
        class TCP:
            sport=10;dport=23
        class UDP:pass
        class Packet:
            def haslayer(self, kind):return kind in (IP, TCP)
            def __getitem__(self, kind):
                return SimpleNamespace(src='192.0.2.1', dst='198.51.100.2', frag=0, proto=6, payload=TCP())
            def __len__(self):return 64
        result = core.packet_record(Packet(), IP, TCP, UDP)
        self.assertEqual(result['destination_port'], 23)
        self.assertNotIn('payload', result)

    def test_export_refuses_added_private_fields_or_detailed_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'report.json'
            for value in [dict(core.demo().report(), private_note='not for export'), core.demo().report(include_addresses=True)]:
                with self.assertRaises(core.MonitorError):core.export_report(path, value)
                self.assertFalse(path.exists())

    def test_duplicate_reputation_keys_refuse(self):
        with self.assertRaises(core.MonitorError):
            core.pulse_observation(b'{"pulse_info":{"count":0,"count":1}}')

    def test_capture_backend_is_injected_and_never_looks_up_addresses(self):
        clock = [0]
        calls = []
        def sniff(**kwargs):
            calls.append(kwargs);clock[0] += kwargs['timeout']
        model = core.Model('live')
        with patch.object(core, 'lookup_otx') as online:
            result = core.capture(model, 'fictional-interface', 1, threading.Event(), backend=(sniff, 'IP', 'TCP', 'UDP'), clock=lambda:clock[0])
        self.assertEqual(result['outcome'], 'completed')
        self.assertTrue(all(call['store'] is False and call['filter'] == 'ip' for call in calls))
        online.assert_not_called()

    def test_cancelled_capture_never_calls_sniff(self):
        stop = threading.Event();stop.set();sniff = Mock()
        result = core.capture(core.Model('live'), 'fictional-interface', 1, stop, backend=(sniff, 'IP', 'TCP', 'UDP'))
        sniff.assert_not_called();self.assertEqual(result['outcome'], 'cancelled')


class CliTests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(ROOT/'monitor.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, timeout=12)

    def test_actual_demo_command_is_offline_and_aggregate_only(self):
        result = self.cli('demo');self.assertEqual(result.returncode, 0)
        value = json.loads(result.stdout);self.assertEqual(value['packets_observed'], 3)
        self.assertNotIn('192.0.2', result.stdout)

    def test_capture_and_lookup_require_explicit_flags(self):
        for args in [('capture', '--interface', 'fictional-interface'), ('lookup', '--ip', '192.0.2.1')]:
            result = self.cli(*args);self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['error'], 'ARGUMENTS_INVALID')

    def test_help_starts_no_native_dependencies(self):
        code = 'import sys;sys.path.insert(0,sys.argv[1]);import monitor;monitor.main([]);assert "scapy" not in sys.modules;assert "psutil" not in sys.modules;assert "requests" not in sys.modules;assert "tkinter" not in sys.modules'
        result = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_optimized_guards_refuse_invalid_input(self):
        result = subprocess.run([sys.executable, '-B', '-O', str(ROOT/'monitor.py'), 'lookup', '--ip', '192.0.2.1'],
                                cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error'], 'ARGUMENTS_INVALID')

    def test_cli_report_export_is_new_and_private(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'report.json'
            self.assertEqual(self.cli('demo', '--output', path).returncode, 0)
            before = path.read_bytes()
            self.assertEqual(self.cli('demo', '--output', path).returncode, 2)
            self.assertEqual(path.read_bytes(), before)


class WidgetTests(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk();self.root.withdraw()
        except Exception:
            if os.environ.get('NETWORK_MONITOR_REQUIRE_TK') == '1':raise
            self.skipTest('Native Tk unavailable')
        self.runner = Mock(return_value=core.demo().report())
        self.view = gui.Desktop(self.root, runner=self.runner)
        self.view.error = Mock();self.view.confirm = Mock(return_value=False)
        self.root.update()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.view.stopped.set()
        if self.view.worker:self.view.worker.join(timeout=3)
        try:
            if self.view.after_id:self.root.after_cancel(self.view.after_id)
            self.root.update_idletasks();self.root.destroy()
        except Exception:pass

    def pump(self):
        end = time.monotonic()+4
        while self.view.worker is not None and time.monotonic()<end:
            self.root.update();time.sleep(.01)
        self.assertIsNone(self.view.worker)

    def test_idle_constructor_never_calls_runner(self):
        self.runner.assert_not_called();self.assertIsNone(self.view.report)

    def test_real_demo_widgets_show_local_rule_counts(self):
        self.view.demo_button.invoke();self.runner.assert_not_called()
        self.assertIn('FICTIONAL DEMO', self.view.summary.get())
        self.assertEqual(len(self.view.events.get_children()), 2)

    def test_cancelled_capture_confirmation_starts_nothing(self):
        self.view.interface.set('fictional-interface');self.view.start_button.invoke()
        self.view.confirm.assert_called_once();self.runner.assert_not_called()

    def test_online_lookup_needs_confirmation(self):
        self.view.lookup_ip.set('192.0.2.1');self.view.lookup_button.invoke()
        self.view.confirm.assert_called_once();self.runner.assert_not_called()

    def test_capture_worker_uses_literal_selection(self):
        self.view.confirm.return_value = True
        self.view.interface.set('fictional-interface');self.view.seconds.set('1')
        self.view.start_button.invoke();self.pump()
        self.assertEqual(self.runner.call_args.args[:2], ('capture', ('fictional-interface', 1.0)))

    def test_invalid_duration_refuses_before_confirmation(self):
        self.view.interface.set('fictional-interface');self.view.seconds.set('nan')
        self.view.start_button.invoke();self.view.confirm.assert_not_called();self.runner.assert_not_called()

    def test_saving_requires_explicit_new_destination(self):
        self.view.demo_button.invoke()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'report.json'
            with patch('tkinter.filedialog.asksaveasfilename', return_value=str(path)):
                self.view.save_button.invoke()
            value = json.loads(path.read_text());self.assertFalse(value['addresses_included'])


if __name__ == '__main__':unittest.main()
