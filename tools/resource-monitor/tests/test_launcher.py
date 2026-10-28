import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('demo_launcher', Path(__file__).resolve().parents[1] / 'launch.py')
launcher = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(launcher)

class Launcher(unittest.TestCase):
    def test_wrong_runtime_refuses_before_app_import(self):
        with patch.object(launcher.sys, 'version_info', (3, 11)), contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(2, launcher.main(['--check']))
        self.assertIn('Python 3.12 or 3.13', errors.getvalue())

    def test_readiness_needs_no_live_provider_or_listener(self):
        with patch('resource_monitor.core.LiveProvider', side_effect=AssertionError('live forbidden')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, launcher.main(['--check']))

    def test_live_cannot_be_enabled_through_demo_launcher(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            launcher.main(['--live'])
        self.assertEqual(2, error.exception.code)

if __name__ == '__main__': unittest.main()
