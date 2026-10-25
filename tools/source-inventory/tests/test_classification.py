"""Original generated inventory/rule fixtures; no real projects or body rescans."""
import contextlib
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import classify_inventory as c
import source_inventory as s
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
import create_classification_example as example


def rules(*items, sensitive=True):
    return {'schema_version': 'outlands.path_rules.v1', 'case_sensitive': sensitive,
            'rules': list(items) or [{'id': 'source', 'category': 'code', 'kind': 'suffix', 'value': '.py'}]}


def rule(identifier='source', category='code', kind='suffix', value='.py'):
    return {'id': identifier, 'category': category, 'kind': kind, 'value': value}


class Classification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='outlands-classification-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'fictional-source'; self.source.mkdir()
        (self.source / 'app.py').write_bytes(b'# Fictional source\n')
        (self.source / 'README.md').write_bytes(b'# Fictional readme\n')
        (self.source / 'docs').mkdir()
        (self.source / 'docs' / 'guide.md').write_bytes(b'Fictional guide\n')
        self.report_parent = self.root / 'inventory'; self.report_parent.mkdir()
        self.run, _ = s.snapshot(self.source, self.report_parent, 'demo')
        self.rulefile = self.root / 'rules.json'
        self.write_rules(rules())
        self.output = self.root / 'classified'

    def write_rules(self, value):
        self.rulefile.write_text(json.dumps(value), encoding='utf-8')

    def parsed(self):
        return c.parse_inventory((self.run / 'files.csv').read_bytes(), (self.run / 'summary.json').read_bytes())

    def alter_csv(self, operation):
        text = (self.run / 'files.csv').read_bytes().decode()
        rows = list(csv.reader(io.StringIO(text, newline='')))
        operation(rows)
        output = io.StringIO(newline=''); writer = csv.writer(output); writer.writerows(rows)
        data = output.getvalue().encode()
        (self.run / 'files.csv').write_bytes(data)
        summary = json.loads((self.run / 'summary.json').read_text())
        summary['files_csv_sha256'] = hashlib.sha256(data).hexdigest().upper()
        (self.run / 'summary.json').write_text(json.dumps(summary), encoding='utf-8')

    def rejects(self, code, operation=None):
        with self.assertRaises(c.ClassificationError) as caught:
            (operation or self.parsed)()
        self.assertEqual(str(caught.exception), code)

    def test_first_match_all_ids_and_category_totals(self):
        config = rules(rule('docs', 'documentation', 'prefix', 'docs/'), rule('markdown', 'text', 'suffix', '.md'))
        report = c.classify_rows(self.parsed()[0], config)
        guide = next(r for r in report['rows'] if r['path'] == 'docs/guide.md')
        self.assertEqual(guide['category'], 'documentation')
        self.assertEqual(guide['matching_rule_ids'], ['docs', 'markdown'])
        self.assertTrue(guide['overlap'])
        self.assertEqual(report['overlapping_files'], 1)
        self.assertEqual(report['unmatched_files'], 1)
        self.assertEqual(report['category_totals']['documentation'], {'files': 1, 'bytes': 16})

    def test_rule_reordering_changes_only_selection(self):
        rows = self.parsed()[0]
        one, two = rule('docs', 'docs', 'prefix', 'docs/'), rule('md', 'text', 'suffix', '.md')
        a = c.classify_rows(rows, rules(one, two)); b = c.classify_rows(rows, rules(two, one))
        self.assertEqual(a['overlapping_files'], b['overlapping_files'])
        self.assertNotEqual(a['category_totals'], b['category_totals'])

    def test_case_sensitivity_is_explicit(self):
        rows = [{'path': 'APP.PY', 'bytes': 2}]
        self.assertEqual(c.classify_rows(rows, rules())['unmatched_files'], 1)
        self.assertEqual(c.classify_rows(rows, rules(sensitive=False))['unmatched_files'], 0)

    def test_exact_and_literal_not_regex(self):
        rows = [{'path': 'literal.*', 'bytes': 1}, {'path': 'literal.txt', 'bytes': 1}]
        result = c.classify_rows(rows, rules(rule(kind='exact', value='literal.*')))
        self.assertEqual(result['unmatched_files'], 1)

    def test_unicode_casefold(self):
        result = c.classify_rows([{'path': 'Straße.py', 'bytes': 1}], rules(rule(kind='prefix', value='STRASSE'), sensitive=False))
        self.assertEqual(result['unmatched_files'], 0)

    def test_deterministic_casefold_then_exact_row_order(self):
        rows = [{'path': name, 'bytes': 1} for name in ['z.py', 'B.py', 'a.py', 'A.py']]
        self.assertEqual([r['path'] for r in c.classify_rows(rows, rules())['rows']], ['A.py', 'a.py', 'B.py', 'z.py'])

    def test_zero_rows_are_valid(self):
        (self.source / 'app.py').unlink(); (self.source / 'README.md').unlink(); (self.source / 'docs' / 'guide.md').unlink()
        self.run, _ = s.snapshot(self.source, self.report_parent, 'empty')
        report = c.classify(self.run, self.rulefile, self.output)
        self.assertEqual(report['file_count'], 0)
        self.assertEqual(report['category_totals'], {})

    def test_successful_reports_and_independent_manifest_hashes(self):
        before = {p.name: p.read_bytes() for p in self.run.iterdir()}
        result = c.classify(self.run, self.rulefile, self.output)
        self.assertEqual(result['file_count'], 3)
        manifest = json.loads((self.output / 'MANIFEST.json').read_text())
        self.assertEqual(len(manifest['files']), 2)
        for row in manifest['files']:
            data = (self.output / row['path']).read_bytes()
            self.assertEqual(len(data), row['bytes'])
            self.assertEqual(hashlib.sha256(data).hexdigest().upper(), row['sha256'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.run.iterdir()})

    def test_does_not_reopen_original_file_bodies(self):
        for p in self.source.rglob('*'):
            if p.is_file(): p.unlink()
        self.assertEqual(c.classify(self.run, self.rulefile, self.output)['file_count'], 3)

    def test_cli_stdout_omits_paths_and_exposes_counts(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = c.main(['--inventory', str(self.run), '--rules', str(self.rulefile), '--output', str(self.output)])
        self.assertEqual(status, 0)
        self.assertNotIn(str(self.root), stdout.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())['file_count'], 3)

    def test_existing_output_refused_and_unchanged(self):
        c.classify(self.run, self.rulefile, self.output)
        before = (self.output / 'classification.json').read_bytes()
        self.rejects('OUTPUT_EXISTS', lambda: c.classify(self.run, self.rulefile, self.output))
        self.assertEqual(before, (self.output / 'classification.json').read_bytes())

    def test_output_inside_inventory_refused(self):
        self.rejects('OUTPUT_OVERLAPS_INPUT', lambda: c.classify(self.run, self.rulefile, self.run / 'new'))

    def test_output_containing_rule_input_refused(self):
        self.rejects('OUTPUT_OVERLAPS_INPUT', lambda: c.classify(self.run, self.rulefile, self.root))

    def test_missing_output_parent_cli_safe_error(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(c.main(['--inventory', str(self.run), '--rules', str(self.rulefile), '--output', str(self.root / 'absent' / 'new')]), 2)
        self.assertNotIn(str(self.root), out.getvalue())

    def test_relative_paths_refused(self):
        self.rejects('ABSOLUTE_PATH_REQUIRED', lambda: c.classify(Path('relative'), self.rulefile, self.output))

    def test_unc_paths_refused_without_stat(self):
        with patch.object(c.inventory, '_directory', side_effect=AssertionError('stat called')):
            self.rejects('LOCAL_PATH_REQUIRED', lambda: c.classify(Path('//server/share'), self.rulefile, self.output))

    def test_duplicate_json_keys_any_depth_refused(self):
        self.rejects('JSON_DUPLICATE_KEY', lambda: c.parse_rules(b'{"schema_version":"outlands.path_rules.v1","case_sensitive":true,"rules":[{"id":"a","id":"b"}]}'))

    def test_unknown_rules_fields_refused(self):
        obj = rules(); obj['unexpected'] = 1
        self.rejects('JSON_FIELDS_INVALID', lambda: c.parse_rules(json.dumps(obj).encode()))

    def test_rule_boolean_and_kind_types_refused(self):
        obj = rules(); obj['case_sensitive'] = 1
        self.rejects('RULE_SCHEMA_INVALID', lambda: c.parse_rules(json.dumps(obj).encode()))
        self.rejects('RULE_KIND_UNSUPPORTED', lambda: c.parse_rules(json.dumps(rules(rule(kind='regex'))).encode()))

    def test_empty_rule_values_and_duplicate_ids_refused(self):
        self.rejects('RULE_PATTERN_INVALID', lambda: c.parse_rules(json.dumps(rules(rule(value=''))).encode()))
        self.rejects('RULE_ID_DUPLICATE', lambda: c.parse_rules(json.dumps(rules(rule(), rule())).encode()))

    def test_categories_are_safe_slugs(self):
        self.rejects('RULE_LABEL_INVALID', lambda: c.parse_rules(json.dumps(rules(rule(category='=FORMULA'))).encode()))

    def test_rule_count_and_pattern_limits(self):
        self.rejects('RULE_COUNT_LIMIT', lambda: c.parse_rules(json.dumps(rules(*[rule(str(i)) for i in range(129)])).encode()))
        self.rejects('RULE_PATTERN_INVALID', lambda: c.parse_rules(json.dumps(rules(rule(value='x' * 1025))).encode()))

    def test_float_nan_and_non_object_json_refused(self):
        for text in (b'{"n":1.5}', b'{"n":NaN}', b'{"n":Infinity}'):
            self.rejects('JSON_INTEGER_REQUIRED', lambda data=text: c.parse_rules(data))
        self.rejects('JSON_OBJECT_REQUIRED', lambda: c.parse_rules(b'[]'))

    def test_json_depth_and_surrogate_limits(self):
        text = ('{"a":' * 20 + '1' + '}' * 20).encode()
        self.rejects('JSON_STRUCTURE_LIMIT', lambda: c.parse_rules(text))
        self.rejects('INVALID_JSON_TEXT', lambda: c.parse_rules(br'{"x":"\ud800"}'))
        self.rejects('INVALID_JSON_TEXT', lambda: c.parse_rules(br'{"\ud800":1}'))

    def test_rule_file_byte_limit(self):
        self.rejects('INPUT_BYTE_LIMIT', lambda: c.parse_rules(b' ' * (c.MAX_RULE_BYTES + 1)))

    def test_csv_hash_mismatch(self):
        data = (self.run / 'files.csv').read_bytes() + b'\n'
        self.rejects('CSV_HASH_MISMATCH', lambda: c.parse_inventory(data, (self.run / 'summary.json').read_bytes()))

    def test_summary_unknown_fields_and_boolean_counts(self):
        raw = (self.run / 'summary.json').read_bytes(); obj = json.loads(raw)
        obj['file_count'] = True
        self.rejects('INVENTORY_TOTALS_INVALID', lambda: c.parse_inventory((self.run / 'files.csv').read_bytes(), json.dumps(obj).encode()))
        obj = json.loads(raw); obj['unexpected'] = 1
        self.rejects('JSON_FIELDS_INVALID', lambda: c.parse_inventory((self.run / 'files.csv').read_bytes(), json.dumps(obj).encode()))

    def test_summary_totals_and_top_levels_must_match(self):
        raw = (self.run / 'summary.json').read_bytes()
        for key, value in [('total_bytes', 1), ('top_level_counts', {})]:
            obj = json.loads(raw); obj[key] = value
            self.rejects('INVENTORY_TOTALS_MISMATCH', lambda value=obj: c.parse_inventory((self.run / 'files.csv').read_bytes(), json.dumps(value).encode()))

    def test_csv_headers_and_column_count(self):
        self.alter_csv(lambda rows: rows[0].reverse())
        self.rejects('CSV_HEADER_INVALID')

    def test_csv_duplicate_rows(self):
        self.alter_csv(lambda rows: rows.append(rows[1]))
        self.rejects('CSV_PATH_DUPLICATE')

    def test_csv_wrong_bytes_and_hash(self):
        self.alter_csv(lambda rows: rows[1].__setitem__(2, '1.5'))
        self.rejects('CSV_BYTES_INVALID')

    def test_csv_unsupported_path(self):
        self.alter_csv(lambda rows: rows[1].__setitem__(0, '../escape'))
        self.rejects('CSV_PATH_INVALID')

    def test_csv_escape_flag_requires_canonical_encoding(self):
        self.alter_csv(lambda rows: rows[1].__setitem__(1, 'true'))
        self.rejects('CSV_ESCAPE_INVALID')

    def test_leading_apostrophe_and_formula_path_roundtrip(self):
        for name in ("'quote.py", '=formula.py', ' leading.py'):
            (self.source / name).write_bytes(b'x')
        self.run, _ = s.snapshot(self.source, self.report_parent, 'escape')
        report = c.classify(self.run, self.rulefile, self.output)
        paths = {r['path'] for r in report['rows']}
        self.assertTrue({"'quote.py", '=formula.py', ' leading.py'} <= paths)
        with (self.output / 'classified-paths.csv').open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        formula = next(r for r in rows if r['path'].endswith('formula.py'))
        self.assertEqual(formula['path'], "'=formula.py")
        self.assertEqual(formula['path_escaped'], 'true')

    def test_matching_work_budget_fails_before_output(self):
        with patch.object(c, 'MAX_MATCH_WORK', 1):
            self.rejects('MATCH_WORK_LIMIT', lambda: c.classify(self.run, self.rulefile, self.output))
        self.assertFalse(self.output.exists())

    def test_comparison_count_budget(self):
        with patch.object(c, 'MAX_COMPARISONS', 1):
            self.rejects('MATCH_WORK_LIMIT', lambda: c.classify(self.run, self.rulefile, self.output))

    def test_output_size_bound_before_directory_creation(self):
        with patch.object(c, 'MAX_REPORT_BYTES', 1):
            self.rejects('REPORT_BYTE_LIMIT', lambda: c.classify(self.run, self.rulefile, self.output))
        self.assertFalse(self.output.exists())

    def test_rule_changed_after_snapshot_refused(self):
        actual = c._read
        def changed(path, maximum):
            result = actual(path, maximum)
            if path == self.rulefile:
                self.rulefile.write_bytes(self.rulefile.read_bytes() + b' ')
            return result
        with patch.object(c, '_read', side_effect=changed):
            self.rejects('INPUT_CHANGED', lambda: c.classify(self.run, self.rulefile, self.output))
        self.assertFalse(self.output.exists())

    def test_oversized_input_rejected_before_open(self):
        with patch.object(c, 'MAX_RULE_BYTES', 1), patch.object(c.os, 'open', wraps=os.open) as opened:
            self.rejects('INPUT_BYTE_LIMIT', lambda: c._read(self.rulefile, 1))
            opened.assert_not_called()

    def test_nonregular_directory_rejected(self):
        self.rejects('REGULAR_INPUT_REQUIRED', lambda: c._read(self.root, 10))

    def test_fifo_rejected_before_open_on_posix(self):
        if os.name == 'nt' or not hasattr(os, 'mkfifo'):
            self.skipTest('POSIX FIFO fixture unavailable')
        fifo = self.root / 'pipe'; os.mkfifo(fifo)
        with patch.object(c.os, 'open', side_effect=AssertionError('FIFO opened')):
            self.rejects('REGULAR_INPUT_REQUIRED', lambda: c._read(fifo, 10))

    def test_symlink_input_refused_when_native_available(self):
        link = self.root / 'linked-rules.json'
        try:
            link.symlink_to(self.rulefile)
        except OSError:
            self.skipTest('Native symlink privilege unavailable')
        with self.assertRaises(s.InventoryError):
            c.classify(self.run, link, self.output)

    def test_partial_output_failure_is_not_success(self):
        with patch.object(c.inventory, '_exclusive_write', side_effect=OSError('fictional write failure')):
            with self.assertRaises(OSError):
                c.classify(self.run, self.rulefile, self.output)
        self.assertTrue(self.output.is_dir())
        self.assertFalse((self.output / 'MANIFEST.json').exists())

    def test_invalid_cli_options_are_safe(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out): self.assertEqual(c.main(['--unknown']), 2)
        self.assertEqual(json.loads(out.getvalue())['error'], 'ARGUMENTS_INVALID')

    def test_example_generator_classifies_fictional_scope(self):
        target = self.root / 'example'
        result = example.create(target)
        self.assertEqual((result['file_count'], result['unmatched_files'], result['overlapping_files']), (4, 1, 1))
        report = json.loads((target / 'classification' / 'classification.json').read_text())
        self.assertEqual(set(report['category_totals']), {'documentation', 'text', 'source'})
        with self.assertRaises(ValueError): example.create(target)

    def test_csv_extra_column_refused(self):
        self.alter_csv(lambda rows: rows[1].append('extra'))
        self.rejects('CSV_ROWS_INVALID')

    def test_csv_status_and_digest_contract(self):
        self.alter_csv(lambda rows: rows[1].__setitem__(5, 'skipped'))
        self.rejects('CSV_ROW_INVALID')
        self.alter_csv(lambda rows: (rows[1].__setitem__(5, 'ok'), rows[1].__setitem__(4, 'not-a-hash')))
        self.rejects('CSV_ROW_INVALID')

    def test_csv_invalid_utf8_refused_with_matching_digest(self):
        raw = (self.run / 'files.csv').read_bytes() + b'\xff'
        summary = json.loads((self.run / 'summary.json').read_text())
        summary['files_csv_sha256'] = hashlib.sha256(raw).hexdigest()
        self.rejects('CSV_INVALID', lambda: c.parse_inventory(raw, json.dumps(summary).encode()))

    def test_row_count_hard_limit_fails(self):
        with patch.object(c, 'MAX_ROWS', 1):
            self.rejects('INVENTORY_TOTALS_INVALID')

    def test_rule_json_huge_integer_has_controlled_failure(self):
        self.rejects('INVALID_JSON', lambda: c.parse_rules(b'{"n":' + b'1' * 5000 + b'}'))

    def test_json_output_escapes_control_and_bidi_path_text(self):
        result = c.classify_rows([{'path': 'docs/line\n\u202efictional.md', 'bytes': 1}], rules(rule(value='.md')))
        encoded = json.dumps(result, ensure_ascii=True)
        self.assertIn('\\n', encoded)
        self.assertIn('\\u202e', encoded)

    def test_rule_categories_do_not_repeat_aggregate_bytes(self):
        report = c.classify_rows([{'path': 'a.py', 'bytes': 5}], rules(rule('one'), rule('two')))
        self.assertEqual(report['category_totals'], {'code': {'files': 1, 'bytes': 5}})
        self.assertEqual(report['overlapping_files'], 1)

    def test_invalid_programmatic_rows_fail_coverage(self):
        self.rejects('ROW_INVALID', lambda: c.classify_rows([{'wrong': 1}], rules()))


if __name__ == '__main__':
    unittest.main()
