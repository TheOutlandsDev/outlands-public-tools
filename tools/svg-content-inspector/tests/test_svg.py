"""Original generated markup and disposable files; no SVG is rendered."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import svg_inspector as s


def svg(body='', attrs=''):
    return ('<svg xmlns="http://www.w3.org/2000/svg" ' + attrs + '>' + body + '</svg>').encode('utf-8')


class SvgTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='outlands-svg-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def rejects(self, code, function):
        with self.assertRaises(s.InspectionError) as result:
            function()
        self.assertEqual(str(result.exception), code)

    def cli(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = s.main(args)
        return status, json.loads(output.getvalue())

    def source(self, data=None):
        path = self.root / 'input.svg'
        path.write_bytes(svg() if data is None else data)
        return path

    def native_link(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError):
            if os.name == 'posix' or os.environ.get('OUTLANDS_REQUIRE_SYMLINK_TEST') == '1':
                self.fail('Required native symlink fixture unavailable')
            self.skipTest('Native Windows symlink creation privilege unavailable')

    def test_minimal_namespace_and_empty_dimensions(self):
        report = s.inspect(svg())
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')
        self.assertEqual(report['node_count'], 1)
        self.assertEqual(report['dimensions']['width'], {'present': False})

    def test_prefixed_svg_namespace_accepted(self):
        report = s.inspect(b'<x:svg xmlns:x="http://www.w3.org/2000/svg"><x:rect/></x:svg>')
        self.assertEqual(report['node_count'], 2)
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')

    def test_namespace_suffix_spoof_and_unnamespaced_root_refused(self):
        for data in (b'<notsvg/>', b'<svg/>', b'<svg xmlns="urn:fictional-svg"/>', b'<html xmlns="http://www.w3.org/2000/svg"/>'):
            with self.subTest(data=data):
                self.rejects('SVG_NAMESPACE_ROOT_REQUIRED', lambda: s.inspect(data))

    def test_declared_lengths_and_exact_decimal_viewbox(self):
        report = s.inspect(svg(attrs='width="2.5cm" height="1e2%" viewBox="-1,-2,300,400"'))
        self.assertEqual(report['dimensions']['width']['value'], '2.5')
        self.assertEqual(report['dimensions']['width']['unit'], 'cm')
        self.assertEqual(report['dimensions']['height']['value'], '100')
        self.assertEqual(report['dimensions']['viewBox']['values'], ['-1', '-2', '300', '400'])

    def test_dimensions_do_not_convert_units(self):
        report = s.inspect(svg(attrs='width="1in" height="12em"'))
        self.assertEqual(report['dimensions']['width']['value'], '1')
        self.assertIn('no unit conversion', report['dimensions']['interpretation'])

    def test_length_unit_ascii_case_normalized(self):
        report = s.inspect(svg(attrs='width="1Q" height="10PX"'))
        self.assertEqual(report['dimensions']['width']['unit'], 'q')
        self.assertEqual(report['dimensions']['height']['unit'], 'px')

    def test_unsupported_and_nonfinite_dimensions_are_review_findings(self):
        for value in ('NaN', 'Infinity', 'calc(1px + 2px)', 'auto', '-1', '1e999', '1future', '1e-100'):
            with self.subTest(value=value):
                report = s.inspect(svg(attrs='width="' + value + '"'))
                self.assertEqual(report['status'], 'REVIEW_REQUIRED')
                self.assertEqual(report['dimensions']['width']['status'], 'invalid_or_unsupported')

    def test_zero_dimension_is_explicit_finding(self):
        report = s.inspect(svg(attrs='width="0" height="1"'))
        self.assertIn('ZERO_DIMENSION_DECLARATION', [x['code'] for x in report['findings']])

    def test_invalid_viewbox_shapes_are_reviewed(self):
        for value in ('0 0 0 10', '0 0 -1 10', '0 0 10', '0,,0,10,10', 'NaN 0 10 10'):
            with self.subTest(value=value):
                report = s.inspect(svg(attrs='viewBox="' + value + '"'))
                self.assertEqual(report['dimensions']['viewBox']['status'], 'invalid_or_unsupported')

    def test_doctype_and_entities_rejected_before_expansion(self):
        samples = [b'<!DOCTYPE svg><svg xmlns="http://www.w3.org/2000/svg"/>',
                   b'<!DOCTYPE svg [<!ENTITY x "x">]><svg xmlns="http://www.w3.org/2000/svg">&x;</svg>',
                   b'<!DOCTYPE svg SYSTEM "file:///fictional/no-file"><svg xmlns="http://www.w3.org/2000/svg"/>',
                   b'<!DOCTYPE svg [<!ENTITY x SYSTEM "https://fictional.invalid/x">]><svg xmlns="http://www.w3.org/2000/svg">&x;</svg>']
        for data in samples:
            with self.subTest(data=data):
                self.rejects('DTD_AND_ENTITIES_REJECTED', lambda: s.inspect(data))

    def test_builtin_xml_entities_remain_supported(self):
        report = s.inspect(svg('<title>A &amp; B &lt; C</title>'))
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')

    def test_commented_doctype_text_is_inert(self):
        report = s.inspect(svg('<!-- <!DOCTYPE svg> --><rect/>'))
        self.assertEqual(report['status'], 'NO_SCOPE_FINDINGS')

    def test_malformed_xml_and_duplicate_attributes_fail(self):
        for data in (svg('<g>'), svg('<g a="1" a="2"/>'), b'', b'<', b'<svg xmlns="http://www.w3.org/2000/svg"/>junk'):
            with self.subTest(data=data):
                self.rejects('INVALID_XML', lambda: s.inspect(data))

    def test_utf8_and_encoding_declaration(self):
        self.rejects('UTF8_REQUIRED', lambda: s.inspect(b'\xff'))
        self.rejects('XML_DECLARATION_UNSUPPORTED', lambda: s.inspect(b'<?xml version="1.0" encoding="ISO-8859-1"?>' + svg()))
        self.assertEqual(s.inspect(b'\xef\xbb\xbf' + svg())['status'], 'NO_SCOPE_FINDINGS')

    def test_old_expat_runtime_fails_closed(self):
        with patch.object(s.expat, 'version_info', (2, 6, 3)):
            self.rejects('EXPAT_SECURITY_UPDATE_REQUIRED', lambda: s.inspect(svg()))

    def test_input_option_types_and_byte_limit(self):
        self.rejects('INPUT_BYTE_LIMIT', lambda: s.inspect('not bytes'))
        self.rejects('INVALID_OPTION', lambda: s.inspect(svg(), include_details=1))
        with patch.object(s, 'MAX_BYTES', 10):
            self.rejects('INPUT_BYTE_LIMIT', lambda: s.inspect(svg()))

    def test_depth_and_node_limits(self):
        with patch.object(s, 'MAX_DEPTH', 2):
            self.rejects('NODE_OR_DEPTH_LIMIT', lambda: s.inspect(svg('<g><rect/></g>')))
        with patch.object(s, 'MAX_NODES', 2):
            self.rejects('NODE_OR_DEPTH_LIMIT', lambda: s.inspect(svg('<rect/><circle/>')))

    def test_attribute_count_and_value_limits(self):
        with patch.object(s, 'MAX_NODE_ATTRIBUTES', 1):
            self.rejects('ATTRIBUTE_LIMIT', lambda: s.inspect(svg(attrs='width="1" height="2"')))
        with patch.object(s, 'MAX_ATTRIBUTES', 1):
            self.rejects('ATTRIBUTE_LIMIT', lambda: s.inspect(svg('<rect y="2"/>', 'width="1"')))
        with patch.object(s, 'MAX_ATTRIBUTE_CHARS', 2):
            self.rejects('ATTRIBUTE_CHARACTER_LIMIT', lambda: s.inspect(svg(attrs='width="123"')))

    def test_text_and_style_limits(self):
        with patch.object(s, 'MAX_TEXT_CHARS', 2):
            self.rejects('TEXT_CHARACTER_LIMIT', lambda: s.inspect(svg('<text>abc</text>')))
        with patch.object(s, 'MAX_STYLE_CHARS', 2):
            self.rejects('STYLE_CHARACTER_LIMIT', lambda: s.inspect(svg('<style>abc</style>')))
        with patch.object(s, 'MAX_TOTAL_STYLE_CHARS', 2):
            self.rejects('TOTAL_STYLE_CHARACTER_LIMIT', lambda: s.inspect(svg('<rect fill="red"/>')))

    def test_namespace_and_id_limits(self):
        with patch.object(s, 'MAX_REFERENCES', 1):
            self.rejects('REFERENCE_LIMIT', lambda: s.inspect(svg('<use href="#a"/><use href="#b"/>')))
        self.rejects('ID_CHARACTER_LIMIT', lambda: s.inspect(svg('<g id="' + 'a' * 1025 + '"/>')))
        self.rejects('NAMESPACE_LIMIT', lambda: s.inspect(svg(attrs='xmlns:x="' + 'a' * 2049 + '"')))

    def test_finding_limit_refuses_partial_success(self):
        with patch.object(s, 'MAX_FINDINGS', 1):
            self.rejects('FINDING_LIMIT', lambda: s.inspect(svg('<script/><foreignObject/>')))

    def test_active_elements_events_and_images(self):
        report = s.inspect(svg('<script/><foreignObject/><animate/><image href="data:image/x,fictional"/><rect onclick="ignored"/>'))
        codes = [x['code'] for x in report['findings']]
        self.assertEqual(codes.count('ACTIVE_OR_ANIMATED_ELEMENT'), 3)
        self.assertIn('IMAGE_ELEMENT', codes)
        self.assertIn('EVENT_HANDLER_ATTRIBUTE', codes)
        self.assertEqual(report['status'], 'REVIEW_REQUIRED')

    def test_foreign_and_unknown_markup_have_explicit_coverage(self):
        report = s.inspect(svg('<x:privateForeignThing xmlns:x="urn:fictional"/><notKnown/>'))
        self.assertIn('FOREIGN_MARKUP_UNINSPECTED', report['coverage_issues'])
        self.assertIn('SVG_ELEMENT_OUTSIDE_SUBSET', report['coverage_issues'])
        self.assertNotIn('urn:fictional', json.dumps(report))
        self.assertNotIn('privateForeignThing', json.dumps(report))

    def test_unknown_namespaced_attribute_has_coverage(self):
        report = s.inspect(svg('<rect xmlns:x="urn:fictional" x:thing="secret-value"/>'))
        self.assertIn('FOREIGN_ATTRIBUTE_NAMESPACE', report['coverage_issues'])
        self.assertNotIn('secret-value', json.dumps(report))

    def test_processing_instruction_is_not_followed(self):
        report = s.inspect(b'<?xml-stylesheet href="https://fictional.invalid/x.css"?>' + svg())
        self.assertIn('PROCESSING_INSTRUCTION_UNINSPECTED', report['coverage_issues'])
        self.assertNotIn('fictional.invalid', json.dumps(report))

    def test_inspection_does_not_open_referenced_files_or_network(self):
        data = svg('<image href="https://fictional.invalid/a"/><use href="file:///fictional/no-file"/>')
        with patch('builtins.open', side_effect=AssertionError('Referenced file opened')), \
             patch.object(os, 'open', side_effect=AssertionError('Referenced descriptor opened')), \
             patch('socket.socket', side_effect=AssertionError('Network socket opened')):
            report = s.inspect(data)
        self.assertEqual(len(report['references']), 2)

    def test_reference_classification_without_opening_targets(self):
        cases = [('#a', 'internal_fragment'), ('https://fictional.invalid/a', 'external_network'),
                 ('//fictional.invalid/a', 'external_network'), ('file:///fictional/a', 'external_file'),
                 ('/fictional/a', 'external_file'), ('Q:/fictional/a', 'external_file'),
                 ('data:text/plain,fictional', 'data'), ('javascript:fictional', 'active_scheme'),
                 ('custom:fictional', 'unknown_scheme'), ('media/a.svg', 'external_relative')]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(s.reference_kind(text), expected)

    def test_internal_fragment_unique_missing_duplicate(self):
        report = s.inspect(svg('<defs><g id="found"/><g id="twice"/><g id="twice"/></defs>'
                               '<use href="#found"/><use href="#lost"/><use href="#twice"/>'))
        self.assertEqual([r['resolution'] for r in report['references']], ['resolved_unique', 'missing', 'ambiguous_duplicate_id'])
        self.assertTrue(any(i['duplicates'] for i in report['ids']))
        self.assertEqual(report['references'][0]['target_nodes'], ['node-000003'])
        self.assertNotIn('found', json.dumps(report))

    def test_non_simple_fragments_and_ids_are_not_guessed(self):
        report = s.inspect(svg('<g id="two words"/><use href="#two%20words"/>'))
        self.assertIn('ID_TEXT_OUTSIDE_FRAGMENT_SUBSET', report['coverage_issues'])
        self.assertEqual(report['references'][0]['kind'], 'unsupported_fragment')
        self.assertEqual(report['references'][0]['resolution'], 'not_inspected')

    def test_href_precedence_and_xmlbase_explicit(self):
        report = s.inspect(svg('<use xmlns:x="http://www.w3.org/1999/xlink" href="#a" x:href="#b"/>',
                               'xml:base="https://fictional.invalid/"'))
        self.assertIn('HREF_PRECEDENCE_NOT_EVALUATED', report['coverage_issues'])
        self.assertIn('BASE_URL_NOT_RESOLVED', report['coverage_issues'])

    def test_reference_details_are_explicit_and_private(self):
        data = svg('<g id="private-id"/><image href="https://fictional.invalid/private-name.png"/>')
        default = s.inspect(data)
        detailed = s.inspect(data, include_details=True)
        self.assertNotIn('private-name', json.dumps(default))
        self.assertNotIn('private-id', json.dumps(default))
        self.assertIn('private-name', json.dumps(detailed))
        self.assertEqual(detailed['ids'][0]['id_text'], 'private-id')

    def test_css_urls_and_imports_outside_comments_strings(self):
        refs, issues = s.css_references('/*url(ignore)*/ @import "theme.css"; .x {fill:URL( "#paint" ); content:"url(ignore)"}')
        self.assertEqual(refs, [('css_import', 'theme.css'), ('css_url', '#paint')])
        self.assertIn('CSS_AT_RULE_NOT_INTERPRETED', issues)

    def test_css_escapes_always_prevent_full_coverage_claim(self):
        refs, issues = s.css_references(r'fill:u\72l(https://fictional.invalid/x);')
        self.assertIn('CSS_ESCAPES_UNINSPECTED', issues)
        report = s.inspect(svg('<rect style="fill:u\\72l(https://fictional.invalid/x)"/>'))
        self.assertEqual(report['status'], 'REVIEW_REQUIRED')

    def test_css_malformed_url_string_comment(self):
        for text in ('fill:url("unterminated)', 'fill:url(a b)', '/*unclosed', 'fill:url(a(b)'):
            with self.subTest(text=text):
                refs, issues = s.css_references(text)
                self.assertTrue(issues)

    def test_css_unknown_function_and_nonascii_are_reviewed(self):
        _, issues = s.css_references('fill:var(--x); color:rgb(1,2,3); /*é*/')
        self.assertIn('CSS_FUNCTION_NOT_INTERPRETED', issues)
        self.assertIn('CSS_TEXT_OUTSIDE_LITERAL_SUBSET', issues)

    def test_css_comments_do_not_join_identifier_pieces(self):
        refs, _ = s.css_references('u/**/rl(https://fictional.invalid/not-url)')
        self.assertEqual(refs, [])

    def test_inline_style_and_stylesheet_coverage_always_visible(self):
        report = s.inspect(svg('<style>rect { fill: url(#paint) }</style><rect style="fill:blue"/><g id="paint"/>'))
        self.assertIn('STYLESHEET_RULES_NOT_EVALUATED', report['coverage_issues'])
        self.assertIn('CSS_CASCADE_AND_DECLARATIONS_NOT_EVALUATED', report['coverage_issues'])
        self.assertEqual(report['references'][0]['resolution'], 'resolved_unique')

    def test_cdata_style_chunks_are_combined(self):
        report = s.inspect(svg('<style><![CDATA[rect {fill:url(]]>#a<![CDATA[)}]]></style><g id="a"/>'))
        self.assertEqual(report['references'][0]['kind'], 'internal_fragment')

    def test_presentation_url_is_observed(self):
        report = s.inspect(svg('<defs><linearGradient id="g"/></defs><rect fill="url(#g)"/>'))
        self.assertEqual(len(report['references']), 1)
        self.assertEqual(report['references'][0]['resolution'], 'resolved_unique')

    def test_xml_character_entities_do_not_hide_active_scheme(self):
        report = s.inspect(svg('<a href="&#x6a;avascript:fictional"/>'))
        self.assertEqual(report['references'][0]['kind'], 'active_scheme')

    def test_raw_source_text_and_metadata_never_in_default_report(self):
        report = s.inspect(svg('<title>Fictional private title</title><desc>Fictional hidden note</desc><text>Fictional private text</text>'))
        text = json.dumps(report)
        self.assertNotIn('Fictional private', text)
        self.assertNotIn('hidden note', text)

    def test_static_html_escapes_details_and_never_embeds_svg(self):
        report = s.inspect(svg('<image href="https://fictional.invalid/?q=&lt;script&gt;"/>'), include_details=True)
        text = s.render_html(report)
        self.assertIn('&lt;script&gt;', text)
        self.assertNotIn('<script>', text)
        self.assertNotIn('<svg', text)
        self.assertNotIn('<img', text)
        self.assertNotIn('href=', text)
        self.assertIn('Content-Security-Policy', text)

    def test_html_preserves_generated_json_layout_but_escapes_raw_controls(self):
        report = s.inspect(svg('<image href="data:text/plain,Fictional"/>'), include_details=True)
        report['references'][0]['reference_text'] = 'line\nnext'
        text = s.render_html(report)
        self.assertIn('<pre>{\n', text)
        self.assertIn('<td>line\\u000anext</td>', text)
        self.assertNotIn('<td>line\nnext</td>', text)

    def test_fresh_reports_and_independent_manifest_hashes(self):
        path = self.source(svg('<rect/>'))
        output = self.root / 'report'
        code, stdout = self.cli(['--svg', str(path), '--output', str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(stdout['status'], 'NO_SCOPE_FINDINGS')
        manifest = json.loads((output / 'MANIFEST.json').read_text())
        self.assertEqual(len(manifest['files']), 2)
        for item in manifest['files']:
            data = (output / item['path']).read_bytes()
            self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (item['bytes'], item['sha256']))
        self.assertEqual(path.read_bytes(), svg('<rect/>'))

    def test_review_exit_and_default_stdout_privacy(self):
        path = self.source(svg('<image href="https://fictional.invalid/private-path"/>'))
        code, output = self.cli(['--svg', str(path), '--output', str(self.root / 'review')])
        self.assertEqual(code, 1)
        self.assertEqual(output['status'], 'REVIEW_REQUIRED')
        self.assertNotIn('private-path', json.dumps(output))
        self.assertNotIn(str(path), json.dumps(output))

    def test_existing_output_refused_unchanged(self):
        path = self.source()
        output = self.root / 'report'; output.mkdir(); marker = output / 'marker.txt'; marker.write_bytes(b'keep')
        code, report = self.cli(['--svg', str(path), '--output', str(output)])
        self.assertEqual(code, 2)
        self.assertEqual(report['error'], 'OUTPUT_EXISTS')
        self.assertEqual(marker.read_bytes(), b'keep')

    def test_output_cannot_replace_input_file(self):
        path = self.source()
        code, report = self.cli(['--svg', str(path), '--output', str(path)])
        self.assertEqual((code, report['error']), (2, 'OUTPUT_EXISTS'))
        self.assertEqual(path.read_bytes(), svg())

    def test_safe_argument_and_io_errors(self):
        for args in ([], ['--unknown'], ['--svg', 'relative.svg', '--output', str(self.root / 'o')],
                     ['--svg', str(self.root / 'missing.svg'), '--output', str(self.root / 'o')]):
            with self.subTest(args=args):
                code, report = self.cli(args)
                self.assertEqual(code, 2)
                self.assertEqual(report['status'], 'INCOMPLETE')
                self.assertNotIn(str(self.root), json.dumps(report))

    def test_output_parent_must_exist(self):
        path = self.source()
        code, _ = self.cli(['--svg', str(path), '--output', str(self.root / 'missing' / 'report')])
        self.assertEqual(code, 2)
        self.assertFalse((self.root / 'missing').exists())

    def test_nonregular_and_oversized_input_refused(self):
        self.rejects('REGULAR_INPUT_REQUIRED', lambda: s.snapshot(self.root))
        path = self.source()
        with patch.object(s, 'MAX_BYTES', 5):
            self.rejects('INPUT_BYTE_LIMIT', lambda: s.snapshot(path))

    def test_fifo_rejected_before_open(self):
        if os.name != 'posix':
            self.skipTest('POSIX FIFO case')
        path = self.root / 'fifo'; os.mkfifo(path)
        with patch.object(s.os, 'open', side_effect=AssertionError('FIFO was opened')):
            self.rejects('REGULAR_INPUT_REQUIRED', lambda: s.snapshot(path))

    def test_symlink_input_refused(self):
        target = self.source(); link = self.root / 'link.svg'; self.native_link(link, target)
        self.rejects('LINKED_PATH_REJECTED', lambda: s.snapshot(link))

    def test_symlink_parent_refused(self):
        target = self.root / 'real'; target.mkdir(); (target / 'a.svg').write_bytes(svg())
        link = self.root / 'linked'; self.native_link(link, target)
        self.rejects('LINKED_PATH_REJECTED', lambda: s.snapshot(link / 'a.svg'))

    def test_input_change_during_read_is_failure(self):
        path = self.source()
        original = os.read
        changed = False
        def read(fd, amount):
            nonlocal changed
            data = original(fd, amount)
            if not changed:
                changed = True
                info = path.stat(); os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000_000))
            return data
        with patch.object(s.os, 'read', side_effect=read):
            self.rejects('INPUT_CHANGED', lambda: s.snapshot(path))

    def test_input_replacement_between_stat_and_open_is_failure(self):
        path = self.source()
        original = os.open
        def opening(name, flags):
            replacement = self.root / 'replacement'; replacement.write_bytes(svg('<rect/>'))
            replacement.replace(path)
            return original(name, flags)
        with patch.object(s.os, 'open', side_effect=opening):
            self.rejects('INPUT_CHANGED', lambda: s.snapshot(path))

    def test_report_limit_before_directory_creation(self):
        output = self.root / 'report'
        with patch.object(s, 'MAX_REPORT_BYTES', 2):
            self.rejects('REPORT_BYTE_LIMIT', lambda: s.write_report(s.inspect(svg()), output))
        self.assertFalse(output.exists())

    def test_partial_output_failure_is_not_success(self):
        path = self.source(); output = self.root / 'report'
        with patch.object(s, 'write_exclusive', side_effect=OSError('Fictional private upstream error')):
            code, report = self.cli(['--svg', str(path), '--output', str(output)])
        self.assertEqual((code, report['error']), (2, 'IO_OR_METADATA_ERROR'))
        self.assertNotIn('private upstream', json.dumps(report))

    def test_unsafe_native_paths_fail_without_stat(self):
        for value in ('//fictional/share/file.svg', '\\\\fictional\\share\\a.svg', 'relative.svg'):
            with self.subTest(value=value):
                self.rejects('LOCAL_ABSOLUTE_PATH_REQUIRED', lambda: s.local_path(value))

    def test_byte_hash_and_deterministic_report(self):
        data = svg('<rect width="20"/>', 'viewBox="0 0 10 10"')
        self.assertEqual(s.inspect(data), s.inspect(data))
        self.assertEqual(s.inspect(data)['source_sha256'], hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    unittest.main()
