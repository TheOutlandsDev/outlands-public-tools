"""Actual CLI processes against invented files; no live hardware collection."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *args, optimized=False):
        return subprocess.run([sys.executable, '-B', *(['-O'] if optimized else []),
                               str(ROOT/'usb_monitor.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, timeout=12)

    def test_no_arguments_are_static_help(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0);self.assertIn('Fictional timeline', result.stdout)
        self.assertNotIn('Traceback', result.stderr)

    def test_help_does_not_import_native_or_gui_modules(self):
        code = 'import sys;sys.path.insert(0,sys.argv[1]);import usb_monitor;usb_monitor.main([]);assert "usb_windows" not in sys.modules;assert "usb_gui" not in sys.modules;assert "tkinter" not in sys.modules'
        result = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_all_demos_have_expected_exits(self):
        for name, exit_code in [('stable', 0), ('reconnect', 0), ('query-gap', 1)]:
            result = self.run_cli('demo', '--scenario', name)
            self.assertEqual(result.returncode, exit_code, result.stderr)
            self.assertEqual(json.loads(result.stdout)['mode'], 'demo')

    def test_live_flag_is_mandatory_and_error_is_fixed(self):
        for args in [('devices',), ('watch', '--device-id', 'USB\\FICTIONAL\\DEMO')]:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['error'], 'ARGUMENTS_INVALID')

    def test_demo_export_never_overwrites_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'report.json'
            result = self.run_cli('demo', '--output', target)
            self.assertEqual(result.returncode, 0)
            data = target.read_bytes()
            result = self.run_cli('demo', '--scenario', 'stable', '--output', target)
            self.assertEqual(result.returncode, 2);self.assertEqual(target.read_bytes(), data)

    def test_replay_uses_relative_samples_and_refuses_extra_data(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'samples.json'
            source.write_text(json.dumps({'schema': 'outlands-usb-samples/1', 'samples': [
                {'elapsed_ms': 0, 'present': True, 'code': None},
                {'elapsed_ms': 500, 'present': False, 'code': None}]}))
            before = source.read_bytes()
            result = self.run_cli('replay', '--file', source)
            self.assertEqual(result.returncode, 0);self.assertEqual(source.read_bytes(), before)
            self.assertEqual(len(json.loads(result.stdout)['events']), 2)
            value = json.loads(source.read_text());value['name'] = 'private label';source.write_text(json.dumps(value))
            result = self.run_cli('replay', '--file', source)
            self.assertEqual(result.returncode, 2);self.assertNotIn('private label', result.stdout)
            self.assertNotIn(str(source), result.stdout)

    def test_missing_input_does_not_disclose_path(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'private-file.json'
            result = self.run_cli('replay', '--file', source)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('private-file', result.stdout);self.assertNotIn(str(folder), result.stdout)

    def test_optimized_python_retains_refusal_guards(self):
        result = self.run_cli('demo', optimized=True)
        self.assertEqual(result.returncode, 0)
        result = self.run_cli('watch', '--live', '--device-id', 'not-usb', optimized=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error'], 'DEVICE_ID_INVALID')

    @unittest.skipIf(os.name == 'nt', 'Non-Windows live refusal')
    def test_actual_nonwindows_live_command_refuses(self):
        result = self.run_cli('devices', '--live')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error'], 'WINDOWS_REQUIRED')


if __name__ == '__main__':unittest.main()
