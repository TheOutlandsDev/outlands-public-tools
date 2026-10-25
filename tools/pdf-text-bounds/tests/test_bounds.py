"""Original synthetic PDFs, actual parser checks and bounded-process fixtures."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
import pdf_bounds as b
import check_advisories as a
from make_demo import make_pdf, create


class Bounds(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='outlands-pdf-bounds-')
        self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
    def core(self, data=None, **kw):
        return b.inspect_snapshot(data or make_pdf(), b.options(**kw))
    def reject(self, code, function):
        with self.assertRaises(b.BoundsError) as error:
            function()
        self.assertEqual(str(error.exception), code)
    def file(self, name='input.pdf', data=None):
        path = self.root / name; path.write_bytes(data or make_pdf()); return path
    def cli(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output): result = b.main(args)
        return result, output.getvalue()
    def test_inside_real_parser_has_geometry_without_text(self):
        report = self.core()
        self.assertEqual(report['status'], 'NO_GEOMETRY_FINDINGS')
        self.assertEqual(report['characters_observed'], len('Fictional inside'))
        self.assertNotIn('Fictional', json.dumps(report))
        self.assertEqual(report['outside_characters'], 0)
    def test_outside_right_geometry(self):
        report = self.core(make_pdf(text='EDGE', x=198), tolerance=0)
        self.assertEqual(report['status'], 'BOUNDS_FINDINGS')
        self.assertEqual(report['outside_characters'], 4)
        self.assertTrue(all('right' in row['outside'] for row in report['findings']))
    def test_left_top_bottom(self):
        for kw, side in [({'x': -5}, 'left'), ({'y': 98}, 'top'), ({'y': -2}, 'bottom')]:
            with self.subTest(side=side):
                report = self.core(make_pdf(text='X', **kw), tolerance=0)
                self.assertIn(side, report['findings'][0]['outside'])
    def test_tolerance_changes_only_boundary_decision(self):
        data = make_pdf(text='X', x=-0.5)
        self.assertEqual(self.core(data, tolerance=0)['outside_characters'], 1)
        self.assertEqual(self.core(data, tolerance=1)['outside_characters'], 0)
    def test_crop_detects_text_inside_media_but_outside_effective_crop(self):
        data = make_pdf(text='Crop edge', x=5, crop=(20, 10, 180, 90))
        self.assertEqual(self.core(data, box='media')['outside_characters'], 0)
        report = self.core(data, box='crop')
        self.assertGreater(report['outside_characters'], 0)
        self.assertEqual(report['pages'][0]['selected_boundary'], [20, 10, 180, 90])
    def test_crop_larger_than_media_is_intersected(self):
        report = self.core(make_pdf(crop=(-50, -50, 250, 150)), box='crop')
        self.assertEqual(report['pages'][0]['selected_boundary'], [0, 0, 200, 100])
    def test_rotated_crop_retains_outside_evidence(self):
        data = make_pdf(text='Crop edge', x=5, crop=(20, 10, 180, 90), rotation=90)
        self.assertEqual(self.core(data, box='media')['outside_characters'], 0)
        self.assertGreater(self.core(data, box='crop')['outside_characters'], 0)
    def test_nonzero_media_origin_uses_actual_box(self):
        report = self.core(make_pdf(text='Offset', x=30, y=70, media=(10, 20, 210, 120)))
        self.assertEqual(report['status'], 'NO_GEOMETRY_FINDINGS')
        self.assertEqual(report['pages'][0]['media_box'], [10, -20, 210, 80])
    def test_rotations_in_real_parser(self):
        for angle in (0, 90, 180, 270):
            with self.subTest(rotation=angle):
                report = self.core(make_pdf(text='Inside', rotation=angle))
                self.assertEqual(report['pages'][0]['rotation'], angle)
                self.assertEqual(report['outside_characters'], 0)
    def test_unsupported_rotation_is_coverage_error(self):
        self.reject('UNSUPPORTED_ROTATION', lambda: self.core(make_pdf(rotation=45)))
    def test_invalid_nonoverlapping_crop(self):
        self.reject('UNSUPPORTED_GEOMETRY', lambda: self.core(make_pdf(crop=(300, 300, 400, 400))))
    def test_no_text_requires_review(self):
        report = self.core(make_pdf(empty=True))
        self.assertEqual(report['status'], 'REVIEW_REQUIRED')
        self.assertEqual(report['pages_without_text'], 1)
    def test_multiple_pages_and_character_counts(self):
        report = self.core(make_pdf(text='AB', pages=3))
        self.assertEqual(report['page_count'], 3)
        self.assertEqual(report['characters_observed'], 6)
    def test_page_limit_no_successful_partial_report(self):
        self.reject('PAGE_LIMIT', lambda: self.core(make_pdf(pages=2), max_pages=1))
    def test_page_lifecycle_never_materializes_eager_page_collection(self):
        import pdfplumber
        with patch.object(pdfplumber.PDF, 'pages', property(lambda _self: (_ for _ in ()).throw(AssertionError('eager pages')))):
            self.assertEqual(self.core()['page_count'], 1)
            self.reject('PAGE_LIMIT', lambda: self.core(make_pdf(pages=2), max_pages=1))
    def test_character_limit(self):
        self.reject('CHARACTER_LIMIT', lambda: self.core(make_pdf(text='AB'), max_chars=1))
    def test_finding_limit(self):
        with patch.object(b, 'MAX_FINDINGS', 1):
            self.reject('FINDING_LIMIT', lambda: self.core(make_pdf(text='AB', x=-30)))
    def test_bbox_nonfinite_and_zero_area(self):
        for rectangle in [(0, 0, float('nan'), 10), (0, 0, 0, 10), (0, 0, 10, float('inf'))]:
            self.reject('UNSUPPORTED_GEOMETRY', lambda r=rectangle: b.rect(r))
        self.assertEqual(b.rect((1, 2, 1, 2), allow_zero=True), (1, 2, 1, 2))
    def test_invalid_option_values(self):
        for field, values in {'box': ['other', 1, True], 'tolerance': [-1, 73, True, float('nan'), float('inf')],
                              'max_pages': [0, 501, True, 1.5], 'max_chars': [0, 500001, True],
                              'timeout': [0, 121, True, float('nan')]}.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(b.BoundsError):
                    b.options(**{field: value})
    def test_closed_dependency_versions(self):
        self.assertEqual(b.dependency_versions(), b.PINS)
        with patch.object(b, 'version', return_value='0'):
            self.reject('DEPENDENCY_VERSION_MISMATCH', b.dependency_versions)
    def test_missing_dependency_fixed_code(self):
        with patch.object(b, 'version', side_effect=b.PackageNotFoundError('private-name')):
            self.reject('DEPENDENCIES_REQUIRED', b.dependency_versions)
    def test_truncated_or_non_pdf_envelope(self):
        for data in (b'not a PDF', make_pdf()[:-8], b'X' + make_pdf()):
            self.reject('UNSUPPORTED_PDF_ENVELOPE', lambda d=data: self.core(d))
    def test_encrypted_pdf_rejected_in_real_parser(self):
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter(); writer.clone_document_from_reader(PdfReader(io.BytesIO(make_pdf())))
        writer.encrypt('fictional-fixture-password', algorithm='AES-256')
        stream = io.BytesIO(); writer.write(stream)
        self.reject('ENCRYPTED_PDF_UNSUPPORTED', lambda: self.core(stream.getvalue()))
    def test_encrypted_empty_user_password_is_still_unsupported(self):
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter(); writer.clone_document_from_reader(PdfReader(io.BytesIO(make_pdf())))
        writer.encrypt('', owner_password='fictional-owner-password', algorithm='AES-256')
        stream = io.BytesIO(); writer.write(stream)
        self.reject('ENCRYPTED_PDF_UNSUPPORTED', lambda: self.core(stream.getvalue()))
    def test_actual_malformed_parser_error_is_incomplete_without_report(self):
        path = self.file(data=b'%PDF-1.4\nnot a valid object tree\n%%EOF\n')
        output = self.root / 'report'
        code, stdout = self.cli(['--pdf', str(path), '--output', str(output)])
        self.assertEqual(code, 2); self.assertFalse(output.exists())
        self.assertEqual(json.loads(stdout)['status'], 'INCOMPLETE')
    def test_worker_uses_actual_pinned_library(self):
        report = b.run_worker(make_pdf(), b.options())
        self.assertEqual(report['status'], 'NO_GEOMETRY_FINDINGS')
        self.assertEqual(report['libraries'], b.PINS)
    def test_worker_timeout(self):
        self.reject('WORKER_TIMEOUT', lambda: b.run_worker(b'', b.options(timeout=0.1),
            command=[sys.executable, '-I', '-B', '-c', 'import time;time.sleep(10)']))
    def test_worker_output_limit(self):
        self.reject('WORKER_OUTPUT_LIMIT', lambda: b.run_worker(b'', b.options(),
            command=[sys.executable, '-I', '-B', '-c', 'import sys;sys.stdout.buffer.write(b"x"*5000000)']))
    def test_worker_stderr_is_not_forwarded(self):
        self.reject('WORKER_FAILED', lambda: b.run_worker(b'', b.options(),
            command=[sys.executable, '-I', '-B', '-c', 'import sys;sys.stderr.write("private detail")']))
    def test_worker_invalid_protocol(self):
        self.reject('WORKER_PROTOCOL', lambda: b.run_worker(b'', b.options(),
            command=[sys.executable, '-I', '-B', '-c', 'print("not json")']))
    def test_worker_rejects_raw_error_text(self):
        self.reject('WORKER_PROTOCOL', lambda: b.run_worker(b'', b.options(),
            command=[sys.executable, '-I', '-B', '-c', 'print(\'{"error":"private path"}\')']))
    def test_worker_guard_denies_network_process_and_writes(self):
        for event, args in [('socket.connect', ()), ('subprocess.Popen', ()), ('os.system', ()),
                            ('os.rename', ()), ('open', ('not-opened', 'w', 0))]:
            with self.subTest(event=event), self.assertRaises(PermissionError): b._worker_guard(event, args)
        b._worker_guard('open', ('not-opened', 'r', 0))
    def test_input_hash_and_bytes_unchanged(self):
        path = self.file(); before = path.read_bytes()
        report = b.inspect(path, self.root / 'report')
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(report['pdf_sha256'], hashlib.sha256(before).hexdigest())
    def test_output_manifest_independent_readback(self):
        output = self.root / 'report'; b.inspect(self.file(), output)
        manifest = json.loads((output / 'MANIFEST.json').read_text())
        self.assertEqual(len(manifest['files']), 2)
        for row in manifest['files']:
            data = (output / row['path']).read_bytes()
            self.assertEqual(len(data), row['bytes']); self.assertEqual(hashlib.sha256(data).hexdigest(), row['sha256'])
    def test_existing_output_refused_without_replacement(self):
        output = self.root / 'existing'; output.mkdir(); keep = output / 'keep.txt'; keep.write_text('retained')
        self.reject('OUTPUT_EXISTS', lambda: b.write_report(self.core(), output))
        self.assertEqual(keep.read_text(), 'retained')
    def test_html_contains_no_text_or_active_resources(self):
        report = self.core(make_pdf(text='PRIVATE_DEMO_MARKER', x=190)); rendered = b.render_html(report)
        for token in ('PRIVATE_DEMO_MARKER', '<script', '<iframe', '<img', 'href=', 'src='):
            self.assertNotIn(token, rendered)
        self.assertIn('Content-Security-Policy', rendered)
    def test_html_value_escaping(self):
        report = self.core(); report['status'] = '<script>fictional</script>'
        self.assertNotIn('<script>', b.render_html(report)); self.assertIn('&lt;script&gt;', b.render_html(report))
    def test_html_programmatic_numeric_cells_also_escape(self):
        report = self.core(make_pdf(x=-5)); report['page_count'] = '<script>fixture</script>'
        report['findings'][0]['page'] = '<img src=fixture>'
        self.assertNotIn('<script>', b.render_html(report)); self.assertNotIn('<img ', b.render_html(report))
    def test_report_limit_before_directory_creation(self):
        output = self.root / 'report'
        with patch.object(b, 'MAX_REPORT_BYTES', 1):
            self.reject('REPORT_BYTE_LIMIT', lambda: b.write_report(self.core(), output))
        self.assertFalse(output.exists())
    def test_exclusive_file_write(self):
        path = self.root / 'kept'; path.write_bytes(b'kept')
        with self.assertRaises(FileExistsError): b.exclusive_write(path, b'new')
        self.assertEqual(path.read_bytes(), b'kept')
    def test_partial_new_output_error_does_not_claim_success(self):
        output = self.root / 'partial'; path = self.file(); real = b.exclusive_write; count = 0
        def fail_second(name, data):
            nonlocal count
            count += 1
            if count == 2: raise OSError('private simulated write failure')
            real(name, data)
        with patch.object(b, 'exclusive_write', side_effect=fail_second):
            code, stdout = self.cli(['--pdf', str(path), '--output', str(output)])
        self.assertEqual(code, 2); self.assertEqual(json.loads(stdout)['status'], 'INCOMPLETE')
        self.assertTrue((output/'report.json').exists()); self.assertFalse((output/'MANIFEST.json').exists())
    def test_cli_counts_and_errors_omit_paths_and_text(self):
        path = self.file(data=make_pdf(text='SECRET_DEMO_TEXT')); output = self.root / 'report'
        code, stdout = self.cli(['--pdf', str(path), '--output', str(output)])
        self.assertEqual(code, 0)
        self.assertNotIn(str(path), stdout); self.assertNotIn('SECRET_DEMO_TEXT', stdout)
        code, stdout = self.cli(['--pdf', str(self.root / 'missing.pdf'), '--output', str(output)])
        self.assertEqual(code, 2); self.assertNotIn('missing.pdf', stdout)
    def test_cli_findings_and_no_text_exit_one(self):
        for index, data in enumerate((make_pdf(x=-5), make_pdf(empty=True))):
            code, _ = self.cli(['--pdf', str(self.file(str(index)+'.pdf', data)), '--output', str(self.root / ('report'+str(index)))])
            self.assertEqual(code, 1)
    def test_cli_arguments_invalid(self):
        for args in ([], ['--unknown'], ['--pdf', 'relative.pdf', '--output', str(self.root/'new')],
                     ['--pdf', str(self.file()), '--output', str(self.root/'new'), '--tolerance', 'nan']):
            code, _ = self.cli(args); self.assertEqual(code, 2)
    def test_invalid_extension_and_directory(self):
        self.reject('PDF_EXTENSION_REQUIRED', lambda: b.read_snapshot(self.file('input.txt')))
        path = self.root / 'dir.pdf'; path.mkdir()
        self.reject('REGULAR_INPUT_REQUIRED', lambda: b.read_snapshot(path))
    def test_input_size_rejected_before_open(self):
        path = self.file()
        with patch.object(b, 'MAX_BYTES', 1), patch.object(b.os, 'open', side_effect=AssertionError('opened')):
            self.reject('INPUT_BYTE_LIMIT', lambda: b.read_snapshot(path))
    def test_changed_snapshot_refused(self):
        path = self.file(); actual = b.identity
        with patch.object(b, 'identity', side_effect=lambda info: (*actual(info), id(info))):
            self.reject('INPUT_CHANGED', lambda: b.read_snapshot(path))
    def test_unsafe_paths_refused_without_io(self):
        for path in ('relative.pdf', '//fictional/share/file.pdf', '\\\\fictional\\share\\file.pdf', str(self.root/'a'/'..'/'x.pdf')):
            with self.subTest(path=path), self.assertRaises(b.BoundsError): b.local_path(path)
    def test_generated_demo_is_original_and_mixed(self):
        destination = self.root / 'demo'; response = create(destination)
        self.assertFalse(response['contains_real_documents'])
        self.assertEqual(len(list(destination.glob('*.pdf'))), 6)
        self.assertEqual(self.core((destination/'inside.pdf').read_bytes())['outside_characters'], 0)
        self.assertGreater(self.core((destination/'outside.pdf').read_bytes())['outside_characters'], 0)
        self.reject('OUTPUT_EXISTS', lambda: create(destination))
    def test_requirements_match_closed_dependency_contract(self):
        module = Path(b.__file__).parent
        actual = dict(line.split('==') for line in (module / 'requirements.txt').read_text().splitlines())
        self.assertEqual(actual, b.PINS)
        self.assertEqual((module / 'requirements-dev.txt').read_text().splitlines(), ['-r requirements.txt', 'pypdf==6.21.2'])
        records = json.loads((module/'docs/DEPENDENCIES.json').read_text())['packages']
        self.assertEqual({row['name']:row['version'] for row in records if row['scope']=='runtime'}, b.PINS)
    def advisory_response(self, selected, vulnerabilities=None):
        return io.BytesIO(json.dumps({'info': {'version': selected}, 'vulnerabilities': vulnerabilities or []}).encode())
    def test_advisory_checker_fixed_pins_and_current_empty_records(self):
        def opened(url, timeout):
            self.assertTrue(url.startswith('https://pypi.org/pypi/')); self.assertEqual(timeout, 30)
            selected = url.split('/')[-2]; return self.advisory_response(selected)
        with patch.object(a.importlib.metadata, 'version', side_effect=lambda name: a.ALL_PINS[name]), patch.object(a.urllib.request, 'urlopen', side_effect=opened):
            self.assertEqual(a.check()['packages'], 9)
    def test_advisory_checker_rejects_reported_advisories(self):
        with patch.object(a.importlib.metadata, 'version', side_effect=lambda name: a.ALL_PINS[name]), patch.object(a.urllib.request, 'urlopen', side_effect=lambda url, timeout: self.advisory_response(url.split('/')[-2], [{'id': 'FICTIONAL-TEST'}])):
            with self.assertRaises(ValueError): a.check()
    def test_advisory_checker_refuses_large_or_wrong_version_response(self):
        for response in (b'x' * (2 * 1024 * 1024 + 1), json.dumps({'info': {'version': '0'}, 'vulnerabilities': []}).encode()):
            with patch.object(a.importlib.metadata, 'version', side_effect=lambda name: a.ALL_PINS[name]), patch.object(a.urllib.request, 'urlopen', return_value=io.BytesIO(response)):
                with self.assertRaises((ValueError, json.JSONDecodeError)): a.check()
    def test_zero_page_document_fails(self):
        self.reject('NO_PAGES', lambda: self.core(make_pdf(pages=0)))
    def test_symlink_input_refused(self):
        target = self.file(); link = self.root / 'link.pdf'
        try: link.symlink_to(target)
        except OSError:
            if os.name == 'posix': raise
            self.skipTest('Native symlink privilege unavailable')
        self.reject('LINKED_PATH_REJECTED', lambda: b.read_snapshot(link))
    @unittest.skipUnless(os.name == 'posix', 'POSIX FIFO fixture')
    def test_fifo_rejected_before_open(self):
        path = self.root / 'pipe.pdf'; os.mkfifo(path)
        self.reject('REGULAR_INPUT_REQUIRED', lambda: b.read_snapshot(path))


if __name__ == '__main__': unittest.main()
