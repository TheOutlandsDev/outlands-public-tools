from pathlib import Path
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from init_inspector import inspect, main


def run(text, details=False, extra=None):
    return inspect([('input-0001', text.encode()), *(extra or [])], details)


class InitTests(unittest.TestCase):
    def test_service_action_resolution(self):
        report = run('service demo /fictional/demo --secret-token\n class main\n disabled\non boot\n start demo\n')
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        self.assertEqual(report['references'][0]['resolution'], 'unique_selected_declaration')
        self.assertEqual(report['services'][0]['argument_count'], 1)
        self.assertNotIn('secret-token', json.dumps(report)); self.assertNotIn('/fictional', json.dumps(report))

    def test_duplicate_override_not_resolved(self):
        report = run('service demo /a\nservice demo /b\n override\non boot\n start demo')
        self.assertEqual(report['references'][0]['resolution'], 'ambiguous_selected_declarations')
        self.assertEqual(len(report['references'][0]['service_ids']), 2)
        self.assertIn('DUPLICATE_SERVICE_DECLARATION', {r['code'] for r in report['findings']})

    def test_import_is_section_and_never_followed(self):
        report = run('on boot\n start absent\nimport /not/read.rc\n start other')
        self.assertEqual(len(report['imports']),1); self.assertEqual(len(report['references']),1)
        self.assertIn('IMPORTS_NOT_FOLLOWED', {r['code'] for r in report['coverage_issues']})
        self.assertIn('STATEMENT_WITHOUT_SUPPORTED_SECTION', {r['code'] for r in report['coverage_issues']})

    def test_dynamic_and_quoted_statements_explicit(self):
        for text in ('service ${name} /a', 'service demo "/a b"', 'service demo /a\\\n --arg', "service demo '/a'"):
            report=run(text); self.assertTrue(report['coverage_issues']); self.assertFalse(report['services'])

    def test_restart_references_and_reboot_markers(self):
        report = run('service demo /a\n critical\n reboot_on_failure reboot\n onrestart reboot\n onrestart restart next\nservice next /b')
        self.assertEqual(report['references'][0]['resolution'], 'unique_selected_declaration')
        self.assertEqual(len(report['findings']),3)

    def test_wrong_context_not_indexed(self):
        report = run('start demo\non boot\n disabled\nservice demo /a\n mount_all /fstab')
        self.assertFalse(report['references']); self.assertFalse(report['mount_all']); self.assertEqual(len(report['coverage_issues']),3)

    def test_mount_all_modes(self):
        report = run('on boot\n mount_all /fstab --early\n mount_all /fstab --late\n mount_all /fstab\n mount_all /fstab --wrong', True)
        self.assertEqual([r['mode'] for r in report['mount_all']], ['--early','--late','unspecified'])
        self.assertEqual(len(report['coverage_issues']),1)

    def test_multiple_selected_files_and_private_details(self):
        report = run('on boot\n start demo', True, [('input-0002', b'service demo /fictional/bin secret')])
        self.assertEqual(report['references'][0]['service_ids'], ['service-0001'])
        self.assertEqual(report['services'][0]['executable'], '/fictional/bin')
        self.assertNotIn('secret', json.dumps(report))

    def test_empty_comments_and_invalid_header(self):
        self.assertEqual(run('# generated\n\n')['status'], 'NO_SCOPE_FINDINGS')
        report=run('service\non\nimport\n strange')
        self.assertEqual(len(report['coverage_issues']),4)

    def test_unknown_option_and_command_not_silently_clean(self):
        report=run('service demo /a\n socket test stream 0660\non boot\n setprop a b')
        self.assertEqual(len(report['coverage_issues']),2)

    def test_cli_exit_and_private_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve(); source=base/'input.rc'; source.write_text('on boot\n start missing', encoding='utf-8')
            capture=io.StringIO()
            with contextlib.redirect_stdout(capture): result=main(['--file',str(source),'--output',str(base/'out')])
            self.assertEqual(result,1); self.assertNotIn(str(base),capture.getvalue())
            self.assertNotIn('missing',capture.getvalue()); self.assertTrue((base/'out/report.html').is_file())
            capture=io.StringIO()
            with contextlib.redirect_stdout(capture): result=main(['--file',str(base/'private-absent.rc'),'--output',str(base/'error')])
            self.assertEqual(result,2); self.assertNotIn('private-absent',capture.getvalue()); self.assertFalse((base/'error').exists())

    def test_real_cli_generated_example(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve()
            subprocess.run([sys.executable,'-B',str(ROOT/'examples/generate.py'),'--output',str(base/'fixtures')],check=True,capture_output=True)
            result=subprocess.run([sys.executable,'-B',str(ROOT/'init_inspector.py'),'--file',str(base/'fixtures/clean.rc'),'--output',str(base/'clean')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            result=subprocess.run([sys.executable,'-B',str(ROOT/'init_inspector.py'),'--file',str(base/'fixtures/review.rc'),'--output',str(base/'review')],capture_output=True,text=True)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)


if __name__ == '__main__': unittest.main()
