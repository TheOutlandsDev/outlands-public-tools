"""Fictional acceptance and exact failure boundaries for Batch 98."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
ENTRY = {
    'json-structure-profiler': 'profile.py',
    'json-structure-revision-comparator': 'compare.py',
    'xml-structure-profiler': 'profile.py',
    'xml-structure-revision-comparator': 'compare.py',
}


def fixture(name, variant='input'):
    return json.loads((TOOLS / name / 'examples' / (variant + '.json')).read_text(encoding='utf-8'))


def run(name, value):
    with tempfile.TemporaryDirectory(prefix='fictional-json-xml-') as directory:
        path = Path(directory) / 'input.json'
        path.write_text(json.dumps(value, ensure_ascii=True) + '\n', encoding='utf-8')
        result = subprocess.run([sys.executable, '-B', str(TOOLS / name / ENTRY[name]),
                                 '--input', str(path)], capture_output=True, text=True)
    if result.stderr:
        raise AssertionError(result.stderr)
    return result.returncode, json.loads(result.stdout)


class Batch98(unittest.TestCase):
    def test_fictional_examples_and_source_pins(self):
        for name in ENTRY:
            with self.subTest(name=name):
                code, report = run(name, fixture(name))
                self.assertEqual((code, report['status']), (0, 'PASS'))
                result = subprocess.run([sys.executable, '-B', str(TOOLS / name / 'source_check.py')],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)['status'], 'SOURCE_MATCH')
        for name in ('json-structure-revision-comparator', 'xml-structure-revision-comparator'):
            self.assertEqual(run(name, fixture(name, 'needs-review'))[0], 1)

    def test_json_paths_array_wildcard_and_no_values(self):
        code, report = run('json-structure-profiler', fixture('json-structure-profiler'))
        self.assertEqual(code, 0)
        paths = {tuple(row['path']): row for row in report['profile']['paths']}
        self.assertEqual(paths[('key:items', 'item:*', 'key:count')]['types'], {'integer': 2})
        self.assertNotIn('sample-a', json.dumps(report))
        self.assertFalse(report['values_reported'])

    def test_json_profile_shape_equal_does_not_prove_values_equal(self):
        code, report = run('json-structure-revision-comparator', fixture('json-structure-revision-comparator'))
        self.assertEqual(code, 0)
        self.assertNotEqual(report['baseline_json_sha256'], report['candidate_json_sha256'])
        self.assertEqual(report['baseline_profile_sha256'], report['candidate_profile_sha256'])
        self.assertFalse(report['value_equality_verified'])
        self.assertEqual(run('json-structure-revision-comparator', fixture('json-structure-revision-comparator', 'needs-review'))[1]['changes'][0]['path'],
                         ['key:items', 'item:*'])

    def test_json_duplicate_nonfinite_and_wrong_pin(self):
        value = fixture('json-structure-profiler')
        for text, code in [('{"a":1,"a":2}', 'JSON_DUPLICATE_KEY'),
                           ('{"a":NaN}', 'JSON_NONFINITE_NUMBER'),
                           ('{"a":', 'JSON_INVALID')]:
            with self.subTest(text=text):
                value['json_text'] = text
                self.assertEqual(run('json-structure-profiler', value), (2, {'status': 'ERROR', 'code': code}))
        value = fixture('json-structure-revision-comparator')
        value['candidate']['profile_sha256'] = '0' * 64
        self.assertEqual(run('json-structure-revision-comparator', value)[1]['code'], 'PROFILE_PIN_INVALID')

    def test_json_type_change_and_nested_limit(self):
        value = fixture('json-structure-profiler')
        value['json_text'] = '{"items":[1,"two",null,true]}'
        report = run('json-structure-profiler', value)[1]
        row = next(x for x in report['profile']['paths'] if x['path'] == ['key:items', 'item:*'])
        self.assertEqual(row['types'], {'boolean': 1, 'integer': 1, 'null': 1, 'string': 1})
        value['json_text'] = '[' * 14 + '0' + ']' * 14
        self.assertEqual(run('json-structure-profiler', value)[1]['code'], 'JSON_STRUCTURE_LIMIT')

    def test_xml_element_attribute_counts_and_no_values(self):
        code, report = run('xml-structure-profiler', fixture('xml-structure-profiler'))
        self.assertEqual(code, 0)
        paths = {tuple(row['path']): row for row in report['profile']['paths']}
        self.assertEqual(paths[('feed', 'item')]['attributes'], {'code': 2})
        self.assertEqual(paths[('feed', 'item')]['direct_text'], 2)
        self.assertNotIn('sample-a', json.dumps(report))

    def test_xml_shape_equal_does_not_prove_text_equal(self):
        code, report = run('xml-structure-revision-comparator', fixture('xml-structure-revision-comparator'))
        self.assertEqual(code, 0)
        self.assertNotEqual(report['baseline_xml_sha256'], report['candidate_xml_sha256'])
        self.assertEqual(report['baseline_profile_sha256'], report['candidate_profile_sha256'])
        self.assertFalse(report['text_equality_verified'])
        changed = run('xml-structure-revision-comparator', fixture('xml-structure-revision-comparator', 'needs-review'))[1]
        self.assertIn(['feed', 'item'], [item['path'] for item in changed['changes']])

    def test_xml_direct_tail_text_counts(self):
        value = fixture('xml-structure-profiler')
        value['xml_text'] = '<feed><item/>after</feed>'
        report = run('xml-structure-profiler', value)[1]
        self.assertEqual(report['profile']['paths'][0]['direct_text'], 1)

    def test_xml_dtd_malformed_and_wrong_pin(self):
        value = fixture('xml-structure-profiler')
        for text in ('<!DOCTYPE feed [<!ENTITY x "ok">]><feed>&x;</feed>', '<feed>'):
            with self.subTest(text=text):
                value['xml_text'] = text
                self.assertEqual(run('xml-structure-profiler', value)[0], 2)
        value = copy.deepcopy(fixture('xml-structure-revision-comparator'))
        value['candidate']['profile_sha256'] = '0' * 64
        self.assertEqual(run('xml-structure-revision-comparator', value)[1]['code'], 'PROFILE_PIN_INVALID')


if __name__ == '__main__':
    unittest.main()
