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
        for version in ((3, 11), (3, 16), (4, 0)):
            with self.subTest(version=version), patch.object(launcher.sys, 'version_info', version), contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(2, launcher.main(['--check']))
            self.assertIn('Python 3.12 through 3.15', errors.getvalue())

    def test_each_supported_runtime_can_check_without_importing_app(self):
        for version in ((3, 12), (3, 13), (3, 14), (3, 15)):
            with self.subTest(version=version), patch.object(launcher.sys, 'version_info', version), patch('resource_monitor.core.LiveProvider', side_effect=AssertionError('live forbidden')), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(0, launcher.main(['--check']))
            self.assertIn(f'Python {version[0]}.{version[1]}', output.getvalue())

    def test_readiness_needs_no_live_provider_or_listener(self):
        with patch('resource_monitor.core.LiveProvider', side_effect=AssertionError('live forbidden')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, launcher.main(['--check']))

    def test_live_cannot_be_enabled_through_demo_launcher(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            launcher.main(['--live'])
        self.assertEqual(2, error.exception.code)

if __name__ == '__main__': unittest.main()
