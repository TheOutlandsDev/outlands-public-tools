"""Generated structures, metadata-only mappings and fresh private report tests."""
from pathlib import Path
import contextlib
import copy
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
import vpd_references as v
from make_demo import create


def fixture():
    return {'projinfo': {'projectfile': '/fictional/project/one.vpd'},
            'timeline': {'subitems': [{'subitems': [{'type': 'invented'}, {'type': 'invented'}]}, {'subitems': []}]},
            'videolist': {'subitems': [{'title': 'Private fictional title', 'path': '/fictional/source/video.mp4'}]},
            'audiolist': {'subitems': []}, 'imagelist': {'subitems': []}, 'subtitlelist': {'subitems': []}}


def encode(value):
    return json.dumps(value, ensure_ascii=True).encode('utf-8')


class VpdTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='outlands-vpd-tests-')
        self.root = Path(self.temporary.name).absolute()
        self.addCleanup(self.cleanup)
        self.data = encode(fixture())

    def cleanup(self):
        assert self.root.parent == Path(tempfile.gettempdir()).absolute()
        assert self.root.name.startswith('outlands-vpd-tests-')
        self.temporary.cleanup()

    def refuses(self, code, action):
        with self.assertRaises(v.CheckError) as observed:
            action()
        self.assertEqual(str(observed.exception), code)

    def report(self):
        return v.analyze_project(self.data)

    def mapping(self, report=None, items=None):
        report = report or self.report()
        return encode({'schemaVersion': 1, 'projectSha256': report['project_sha256'],
                       'files': items if items is not None else [{'referenceId': 'ref-000002', 'relativePath': 'media/video.mp4'}]})

    def media(self, *, present=True):
        root = self.root / 'copies'; (root / 'media').mkdir(parents=True)
        if present:
            (root / 'media/video.mp4').write_bytes(b'not actual media; never inspected')
        return root

    def cli(self, *arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = v.main(list(arguments))
        return code, json.loads(output.getvalue())

    def project(self, data=None):
        path = self.root / 'project.vpd'; path.write_bytes(self.data if data is None else data); return path

    def symlink(self, link, target, *, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError):
            if sys.platform.startswith('linux') or os.environ.get('VPD_REQUIRE_SYMLINK') == '1':
                self.fail('Required symlink fixture could not be created')
            self.skipTest('Native symlink creation privilege unavailable; required on Linux CI')

    def test_structural_counts_and_roles(self):
        report = self.report()
        self.assertEqual((report['timeline_track_entries'], report['timeline_block_entries']), (2, 2))
        self.assertEqual(report['media_bin_reference_count'], 1)
        self.assertEqual([x['role'] for x in report['references']], ['project_record_path', 'videolist_path'])
        self.assertEqual(report['status'], 'INVENTORY_ONLY')

    def test_default_omits_paths_titles_and_local_roots(self):
        report = self.report(); text = json.dumps(report) + v.render_html(report)
        for value in ['/fictional/', 'Private fictional title', str(self.root)]:
            self.assertNotIn(value, text)
        self.assertFalse(report['embedded_path_text_included'])

    def test_include_paths_is_explicit(self):
        report = v.analyze_project(self.data, include_path_text=True)
        self.assertIn('/fictional/source/video.mp4', json.dumps(report))
        self.assertEqual(report['references'][1]['json_pointer'], '/videolist/subitems/0/path')

    def test_original_bytes_are_hashed(self):
        self.assertEqual(self.report()['project_sha256'], hashlib.sha256(self.data).hexdigest())

    def test_unknown_path_is_not_declared_media(self):
        obj = fixture(); obj['customPrivateKey'] = {'path': '/fictional/unclassified'}
        report = v.analyze_project(encode(obj)); row = next(x for x in report['references'] if x['role'] == 'unclassified_path')
        self.assertEqual(row['location'], 'outside_supported_bin_structure')
        self.assertNotIn('customPrivateKey', json.dumps(report))
        self.assertIn('UNCLASSIFIED_PATH_FIELD', report['coverage_issues'])
        self.assertEqual(report['status'], 'REVIEW_REQUIRED')

    def test_other_bin_roles_supported_as_structural_fields(self):
        obj = fixture()
        for name in ['audiolist', 'imagelist', 'subtitlelist']:
            obj[name]['subitems'] = [{'path': 'invented/' + name}]
        report = v.analyze_project(encode(obj))
        self.assertEqual(report['media_bin_reference_count'], 4)

    def test_unrecognized_bin_entry_records_coverage(self):
        obj = fixture(); obj['videolist']['subitems'].append({'title': 'no path'})
        self.assertIn('BIN_ENTRY_WITHOUT_STRING_PATH', v.analyze_project(encode(obj))['coverage_issues'])

    def test_uncounted_track_records_coverage(self):
        obj = fixture(); obj['timeline']['subitems'].append({'other': []})
        report = v.analyze_project(encode(obj))
        self.assertIn('UNCOUNTED_TIMELINE_ENTRY', report['coverage_issues'])
        self.assertEqual(report['timeline_block_entries'], 2)

    def test_empty_reference_is_visible(self):
        obj = fixture(); obj['videolist']['subitems'][0]['path'] = ''
        report = v.analyze_project(encode(obj))
        self.assertIn('EMPTY_REFERENCE_TEXT', report['coverage_issues'])
        self.assertEqual(report['references'][1]['path_kind'], 'empty')

    def test_unsupported_structure_fails(self):
        for obj in [[], {}, {'timeline': {}}, fixture() | {'videolist': []}]:
            with self.subTest(obj=type(obj)):
                self.refuses('UNSUPPORTED_PROJECT_STRUCTURE', lambda: v.analyze_project(encode(obj)))

    def test_duplicate_json_keys_fail(self):
        self.refuses('DUPLICATE_JSON_KEY', lambda: v.analyze_project(b'{"x":1,"x":2}'))

    def test_nested_duplicate_json_keys_fail(self):
        self.refuses('DUPLICATE_JSON_KEY', lambda: v.parse_json(b'{"x":{"n":1,"n":2}}'))

    def test_nonfinite_numbers_fail(self):
        for text in [b'NaN', b'Infinity', b'-Infinity']:
            self.refuses('NONFINITE_JSON_NUMBER', lambda: v.parse_json(text))

    def test_numbers_have_lexical_and_exponent_bounds(self):
        for text in [b'1' * 129, b'1e5000']:
            self.refuses('JSON_NUMBER_LIMIT', lambda: v.parse_json(text))
        self.assertEqual(str(v.parse_json(b'1e-500')), '1E-500')

    def test_invalid_json_utf8_and_surrogates_fail(self):
        for text, code in [(b'{"a":', 'INVALID_JSON'), (b'\xff', 'UTF8_REQUIRED'), (b'"\\ud800"', 'JSON_STRING_LIMIT')]:
            self.refuses(code, lambda: v.parse_json(text))

    def test_depth_bound_before_decoder(self):
        self.refuses('JSON_DEPTH_LIMIT', lambda: v.parse_json(b'[' * 33 + b'0' + b']' * 33))
        self.assertEqual(v.parse_json(b'{"x":"[[[{\\\""}'), {'x': '[[[{"'})

    def test_string_and_key_limits(self):
        with patch.object(v, 'MAX_STRING', 8):
            self.refuses('JSON_STRING_LIMIT', lambda: v.parse_json(encode('x' * 9)))
        self.refuses('JSON_KEY_LIMIT', lambda: v.parse_json(encode({'x' * 257: 1})))

    def test_node_limit(self):
        with patch.object(v, 'MAX_NODES', 5):
            self.refuses('JSON_NODE_OR_DEPTH_LIMIT', lambda: v.parse_json(b'[1,2,3,4,5]'))

    def test_reference_limit(self):
        with patch.object(v, 'MAX_REFERENCES', 1):
            self.refuses('REFERENCE_LIMIT', self.report)

    def test_byte_limits_apply_to_api(self):
        with patch.object(v, 'MAX_PROJECT_BYTES', 2):
            self.refuses('INPUT_BYTE_LIMIT', self.report)

    def test_present_mapping_never_opens_media(self):
        root = self.media(); report = self.report()
        before = (root / 'media/video.mp4').read_bytes()
        with patch.object(os, 'open', side_effect=AssertionError('media open attempted')):
            v.apply_mapping(report, self.mapping(report), root)
        self.assertEqual(report['references'][1]['availability'], 'present_regular_file')
        self.assertEqual(report['status'], 'NO_MAPPING_FINDINGS')
        self.assertEqual((root / 'media/video.mp4').read_bytes(), before)
        self.assertFalse(report['references'][1]['media_content_read'])

    def test_missing_mapping_is_not_success(self):
        report = self.report(); v.apply_mapping(report, self.mapping(report), self.media(present=False))
        self.assertEqual(report['references'][1]['availability'], 'missing')
        self.assertEqual(report['status'], 'REVIEW_REQUIRED')

    def test_unmapped_media_requires_review(self):
        report = self.report(); v.apply_mapping(report, self.mapping(report, []), self.media())
        self.assertEqual(report['unmapped_media_reference_count'], 1)
        self.assertEqual(report['status'], 'REVIEW_REQUIRED')

    def test_directory_target_is_not_a_media_file(self):
        root = self.media(present=False); (root / 'media/video.mp4').mkdir()
        report = self.report(); v.apply_mapping(report, self.mapping(report), root)
        self.assertEqual(report['references'][1]['availability'], 'not_regular_file')

    def test_non_directory_component_is_reported(self):
        root = self.root / 'copies'; root.mkdir(); (root / 'media').write_bytes(b'')
        report = self.report(); v.apply_mapping(report, self.mapping(report), root)
        self.assertEqual(report['references'][1]['availability'], 'non_directory_component')

    def test_stale_project_hash_fails_before_checks(self):
        obj = json.loads(self.mapping()); obj['projectSha256'] = '0' * 64
        self.refuses('MAPPING_PROJECT_MISMATCH', lambda: v.apply_mapping(self.report(), encode(obj), self.media()))

    def test_mapping_fields_schema_and_boolean_are_strict(self):
        base = json.loads(self.mapping())
        for obj, code in [(base | {'x': 1}, 'INVALID_MAPPING_FIELDS'), (base | {'schemaVersion': True}, 'MAPPING_PROJECT_MISMATCH'),
                          (base | {'files': None}, 'INVALID_MAPPING_FILES')]:
            root = self.root / ('copies' + str(len(list(self.root.iterdir())))); root.mkdir()
            self.refuses(code, lambda: v.apply_mapping(self.report(), encode(obj), root))

    def test_mapping_unknown_project_role_and_duplicate_ids_fail(self):
        root = self.media()
        for items in [[{'referenceId': 'ref-999999', 'relativePath': 'a'}],
                      [{'referenceId': 'ref-000001', 'relativePath': 'a'}],
                      [{'referenceId': 'ref-000002', 'relativePath': 'a'}] * 2]:
            self.refuses('INVALID_MAPPING_REFERENCE', lambda: v.apply_mapping(self.report(), self.mapping(items=items), root))

    def test_unsafe_mapping_paths_fail(self):
        for text in ['../outside', '/outside', 'Q:/outside', 'a\\b', 'a//b', 'a/./b', 'NUL.txt', 'a.', 'a ', 'a\nb', 'a:b', 'a?b']:
            with self.subTest(text=text):
                self.refuses('INVALID_RELATIVE_MAPPING', lambda: v.safe_relative(text))

    def test_portable_mapping_collisions_fail(self):
        obj = fixture(); obj['videolist']['subitems'].append({'path': 'other.mp4'})
        report = v.analyze_project(encode(obj)); root = self.media()
        mapping = self.mapping(report, [{'referenceId': 'ref-000002', 'relativePath': 'Clip.mp4'},
                                        {'referenceId': 'ref-000003', 'relativePath': 'clip.mp4'}])
        self.refuses('PORTABLE_MAPPING_COLLISION', lambda: v.apply_mapping(report, mapping, root))

    def test_nfc_mapping_collisions_fail(self):
        obj = fixture(); obj['videolist']['subitems'].append({'path': 'other.mp4'})
        report = v.analyze_project(encode(obj)); root = self.media()
        mapping = self.mapping(report, [{'referenceId': 'ref-000002', 'relativePath': 'caf\u00e9.mp4'},
                                        {'referenceId': 'ref-000003', 'relativePath': 'cafe\u0301.mp4'}])
        self.refuses('PORTABLE_MAPPING_COLLISION', lambda: v.apply_mapping(report, mapping, root))

    def test_same_copy_for_multiple_references_is_explicit(self):
        obj = fixture(); obj['videolist']['subitems'].append({'path': 'other.mp4'})
        report = v.analyze_project(encode(obj)); root = self.media()
        mapping = self.mapping(report, [{'referenceId': name, 'relativePath': 'media/video.mp4'}
                                        for name in ['ref-000002', 'ref-000003']])
        v.apply_mapping(report, mapping, root)
        self.assertEqual(report['metadata_check_attempt_count'], 2)
        self.assertEqual(report['mapping_summary'], {'mapped_references': 2, 'unique_relative_paths': 1, 'reused_relative_path_references': 1})
        self.assertEqual(report['references'][1]['mapped_copy_id'], report['references'][2]['mapped_copy_id'])

    def test_mapping_byte_bound_applies_to_api(self):
        root = self.media()
        with patch.object(v, 'MAX_MAPPING_BYTES', 2):
            self.refuses('INPUT_BYTE_LIMIT', lambda: v.apply_mapping(self.report(), self.mapping(), root))

    def test_unknown_path_role_cannot_be_mapped_as_media(self):
        obj = fixture(); obj['export'] = {'path': 'fictional-render.mp4'}
        report = v.analyze_project(encode(obj)); root = self.media()
        ref_id = next(x['id'] for x in report['references'] if x['role'] == 'unclassified_path')
        mapping = self.mapping(report, [{'referenceId': ref_id, 'relativePath': 'media/video.mp4'}])
        self.refuses('INVALID_MAPPING_REFERENCE', lambda: v.apply_mapping(report, mapping, root))

    def test_unreadable_mapped_metadata_is_unknown_not_missing(self):
        root = self.media(); original = Path.lstat
        def deny(path):
            if path.name == 'video.mp4':
                raise PermissionError('fictional private detail')
            return original(path)
        report = self.report()
        with patch.object(Path, 'lstat', deny):
            v.apply_mapping(report, self.mapping(report), root)
        self.assertEqual(report['references'][1]['availability'], 'metadata_unavailable')
        self.assertNotIn('fictional private detail', json.dumps(report))

    def test_invalid_last_mapping_prevents_all_checks(self):
        report = self.report(); root = self.media()
        mapping = self.mapping(report, [{'referenceId': 'ref-000002', 'relativePath': 'media/video.mp4'},
                                       {'referenceId': 'no-such-id', 'relativePath': 'x'}])
        self.refuses('INVALID_MAPPING_REFERENCE', lambda: v.apply_mapping(report, mapping, root))
        self.assertTrue(all(not x['metadata_check_attempted'] for x in report['references']))

    def test_embedded_absolute_network_url_and_traversal_never_followed(self):
        for text, kind in [('/fictional/abs', 'posix_absolute'), ('Q:/fictional/a', 'windows_absolute'),
                           ('https://invalid.example/a', 'scheme_or_device_text'), ('../a', 'unsupported_relative_text'),
                           ('//fictional/share/a', 'network_or_device_text')]:
            obj = fixture(); obj['videolist']['subitems'][0]['path'] = text
            with patch.object(Path, 'lstat', side_effect=AssertionError('embedded path accessed')):
                report = v.analyze_project(encode(obj))
            self.assertEqual(report['references'][1]['path_kind'], kind)

    def test_mapping_link_leaf_rejected(self):
        root = self.media(present=False); target = self.root / 'outside'; target.write_bytes(b'')
        self.symlink(root / 'media/video.mp4', target)
        report = self.report(); v.apply_mapping(report, self.mapping(report), root)
        self.assertEqual(report['references'][1]['availability'], 'linked_path_rejected')

    def test_mapping_link_parent_not_resolved(self):
        root = self.root / 'copies'; root.mkdir(); outside = self.root / 'outside'; outside.mkdir()
        self.symlink(root / 'media', outside, directory=True)
        report = self.report(); v.apply_mapping(report, self.mapping(report), root)
        self.assertEqual(report['references'][1]['availability'], 'linked_path_rejected')

    def test_project_link_refused(self):
        original = self.project(); linked = self.root / 'linked.vpd'; self.symlink(linked, original)
        self.refuses('LINKED_PATH_REJECTED', lambda: v.read_snapshot(linked, 1000))

    def test_fifo_input_refused_before_open(self):
        if not hasattr(os, 'mkfifo'):
            self.skipTest('POSIX FIFO fixture; Linux CI required')
        target = self.root / 'input.vpd'; os.mkfifo(target)
        self.refuses('REGULAR_INPUT_REQUIRED', lambda: v.read_snapshot(target, 1000))

    def test_snapshot_limit_and_input_bytes_unchanged(self):
        path = self.project()
        self.assertEqual(v.read_snapshot(path, len(self.data)), self.data)
        self.refuses('INPUT_BYTE_LIMIT', lambda: v.read_snapshot(path, len(self.data) - 1))
        self.assertEqual(path.read_bytes(), self.data)

    def test_mutation_during_read_fails(self):
        path = self.project(); original_read = os.read; changed = False
        def mutate(fd, maximum):
            nonlocal changed
            block = original_read(fd, maximum)
            if block and not changed:
                changed = True; path.write_bytes(self.data + b' ')
            return block
        with patch.object(os, 'read', side_effect=mutate):
            self.refuses('INPUT_CHANGED', lambda: v.read_snapshot(path, 10000))

    def test_json_and_html_report_manifest_verified(self):
        output = self.root / 'report'; report = self.report(); v.write_report(report, output)
        manifest = json.loads((output / 'MANIFEST.json').read_text())
        self.assertEqual({x['path'] for x in manifest['files']}, {'report.json', 'report.html'})
        for row in manifest['files']:
            data = (output / row['path']).read_bytes()
            self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (row['bytes'], row['sha256']))

    def test_existing_output_refused_and_unchanged(self):
        output = self.root / 'report'; output.mkdir(); (output / 'owner.txt').write_bytes(b'retain')
        self.refuses('OUTPUT_EXISTS', lambda: v.write_report(self.report(), output))
        self.assertEqual((output / 'owner.txt').read_bytes(), b'retain')

    def test_output_inside_media_root_refused(self):
        root = self.media()
        self.refuses('OUTPUT_INSIDE_MEDIA_ROOT', lambda: v.write_report(self.report(), root / 'report', media_root=root))

    def test_output_size_bound_before_directory_creation(self):
        target = self.root / 'report'
        with patch.object(v, 'MAX_REPORT_BYTES', 10):
            self.refuses('REPORT_BYTE_LIMIT', lambda: v.write_report(self.report(), target))
        self.assertFalse(target.exists())

    def test_html_escaping_no_links_script_or_external_assets(self):
        obj = fixture(); obj['videolist']['subitems'][0]['path'] = '<script>alert("x")</script>\u202e'
        text = v.render_html(v.analyze_project(encode(obj), include_path_text=True))
        self.assertIn('&lt;script&gt;', text); self.assertIn('\\u202e', text)
        self.assertNotIn('<script', text); self.assertNotIn('href=', text); self.assertNotIn('src=', text)

    def test_output_failure_leaves_only_new_partial_directory(self):
        output = self.root / 'report'; original = v.exclusive_write; count = 0
        def fail_second(path, data):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('fictional failure')
            original(path, data)
        with patch.object(v, 'exclusive_write', side_effect=fail_second):
            with self.assertRaises(OSError):
                v.write_report(self.report(), output)
        self.assertTrue((output / 'report.json').exists()); self.assertFalse((output / 'MANIFEST.json').exists())

    def test_cli_inventory_stdout_omits_paths(self):
        project = self.project(); code, summary = self.cli('--project', str(project), '--output', str(self.root / 'out'))
        self.assertEqual(code, 0); self.assertEqual(summary['status'], 'INVENTORY_ONLY')
        self.assertNotIn(str(self.root), json.dumps(summary)); self.assertEqual(project.read_bytes(), self.data)

    def test_cli_mapping_pair_required(self):
        code, summary = self.cli('--project', str(self.root / 'project.vpd'), '--output', str(self.root / 'out'), '--media-root', str(self.root))
        self.assertEqual(code, 2); self.assertEqual(summary['error'], 'MAPPING_AND_MEDIA_ROOT_REQUIRED_TOGETHER')

    def test_cli_bad_json_and_argument_errors_are_safe(self):
        project = self.project(b'{')
        code, summary = self.cli('--project', str(project), '--output', str(self.root / 'out'))
        self.assertEqual((code, summary['error']), (2, 'INVALID_JSON'))
        code, summary = self.cli('--unknown', 'private-value')
        self.assertEqual((code, summary['error']), (2, 'ARGUMENTS_INVALID'))

    def test_cli_demo_missing_and_complete_mappings(self):
        for complete in [False, True]:
            root = self.root / str(complete); create(root, complete=complete)
            code, summary = self.cli('--project', str(root / 'project.vpd'), '--mapping', str(root / 'mapping.json'),
                                     '--media-root', str(root / 'copies'), '--output', str(root / 'report'))
            self.assertEqual(code, 0 if complete else 1)
            self.assertEqual(summary['status'], 'NO_MAPPING_FINDINGS' if complete else 'REVIEW_REQUIRED')

    def test_local_relative_and_network_paths_refused(self):
        for value in ['relative.vpd', '//fictional/share/file.vpd', '\\\\fictional\\share\\file.vpd']:
            self.refuses('LOCAL_ABSOLUTE_PATH_REQUIRED', lambda: v.local_path(value))


if __name__ == '__main__':
    unittest.main()
