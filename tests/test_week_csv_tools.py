"""Fictional acceptance and exact failure boundaries for Batch 97."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
ENTRY = {
    'iso-week-cohort-analyzer': 'analyze.py',
    'iso-week-claim-checker': 'claims.py',
    'csv-column-profiler': 'profile.py',
    'csv-profile-revision-comparator': 'compare.py',
}

def fixture(name, variant='input'):
    return json.loads((TOOLS / name / 'examples' / (variant + '.json')).read_text(encoding='utf-8'))

def run(name, value):
    with tempfile.TemporaryDirectory(prefix='fictional-week-csv-') as directory:
        path = Path(directory) / 'input.json'
        path.write_text(json.dumps(value, ensure_ascii=True) + '\n', encoding='utf-8')
        result = subprocess.run([sys.executable, '-B', str(TOOLS / name / ENTRY[name]),
                                 '--input', str(path)], capture_output=True, text=True)
    if result.stderr:
        raise AssertionError(result.stderr)
    return result.returncode, json.loads(result.stdout)

class Batch97(unittest.TestCase):
    def test_fictional_examples_and_source_pins(self):
        for name in ENTRY:
            with self.subTest(name=name):
                code, report = run(name, fixture(name))
                self.assertEqual((code, report['status']), (0, 'PASS'))
                check = subprocess.run([sys.executable, '-B', str(TOOLS / name / 'source_check.py')],
                                       capture_output=True, text=True)
                self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
                self.assertEqual(json.loads(check.stdout)['status'], 'SOURCE_MATCH')
        for name in ('iso-week-claim-checker', 'csv-profile-revision-comparator'):
            with self.subTest(review=name):
                self.assertEqual(run(name, fixture(name, 'needs-review'))[0], 1)

    def test_iso_year_boundary_and_week_dates(self):
        code, report = run('iso-week-cohort-analyzer', fixture('iso-week-cohort-analyzer'))
        self.assertEqual(code, 0)
        self.assertEqual([(x['week'], x['rows']) for x in report['cohort']['weeks']],
                         [('2020-W53', 2), ('2021-W01', 1)])
        self.assertEqual(report['cohort']['weeks'][0]['monday'], '2020-12-28')
        self.assertEqual(report['cohort']['weeks'][0]['sunday'], '2021-01-03')

    def test_week_order_independent_and_invalid_date(self):
        value = fixture('iso-week-cohort-analyzer')
        pin = run('iso-week-cohort-analyzer', value)[1]['cohort_sha256']
        value['snapshot']['rows'].reverse()
        self.assertEqual(run('iso-week-cohort-analyzer', value)[1]['cohort_sha256'], pin)
        value['snapshot']['rows'][0]['date'] = '2021-02-29'
        self.assertEqual(run('iso-week-cohort-analyzer', value)[1]['code'], 'DATE_INVALID')

    def test_week_claim_mismatch_missing_extra_and_false_pin(self):
        name = 'iso-week-claim-checker'
        code, report = run(name, fixture(name, 'needs-review'))
        self.assertEqual(code, 1)
        self.assertEqual(report['findings'][0]['code'], 'WEEK_MISMATCH')
        value = fixture(name)
        value['claims'] = value['claims'][:-1] + [{'id': 'extra', 'iso_year': 2021, 'iso_week': 1}]
        code, report = run(name, value)
        self.assertEqual(code, 1)
        self.assertEqual([x['code'] for x in report['findings']], ['CLAIM_MISSING', 'CLAIM_UNEXPECTED'])
        value = fixture(name); value['cohort_sha256'] = '0' * 64
        self.assertEqual(run(name, value)[1]['code'], 'COHORT_PIN_INVALID')

    def test_week_impossible_claim_refused(self):
        name = 'iso-week-claim-checker'
        value = fixture(name)
        value['claims'][0]['iso_year'] = 2021
        value['claims'][0]['iso_week'] = 53
        self.assertEqual(run(name, value)[1]['code'], 'CLAIM_WEEK_INVALID')

    def test_csv_profile_counts_and_quoted_newline(self):
        name = 'csv-column-profiler'
        code, report = run(name, fixture(name))
        self.assertEqual(code, 0)
        self.assertEqual(report['profile']['row_count'], 2)
        self.assertEqual(report['profile']['columns'][0]['distinct_nonblank'], 2)
        value = fixture(name)
        value['csv_text'] = 'item,count\n"a\nb",2\nfan,\n'
        code, report = run(name, value)
        self.assertEqual(code, 0)
        self.assertEqual(report['profile']['columns'][0]['maximum_length'], 3)
        self.assertEqual(report['profile']['columns'][1]['blank_rows'], 1)

    def test_csv_invalid_width_duplicate_header_and_quote(self):
        name = 'csv-column-profiler'
        for csv_text, expected in [
            ('item,count\nfan\n', 'CSV_ROW_WIDTH_INVALID'),
            ('item,item\nfan,2\n', 'CSV_HEADER_DUPLICATE'),
            ('item,count\n"fan,2\n', 'CSV_INVALID'),
        ]:
            with self.subTest(csv_text=csv_text):
                value = fixture(name); value['csv_text'] = csv_text
                self.assertEqual(run(name, value), (2, {'status': 'ERROR', 'code': expected}))

    def test_csv_profile_equality_is_not_record_equality(self):
        name = 'csv-profile-revision-comparator'
        code, report = run(name, fixture(name))
        self.assertEqual(code, 0)
        self.assertNotEqual(report['baseline_csv_sha256'], report['candidate_csv_sha256'])
        self.assertEqual(report['baseline_profile_sha256'], report['candidate_profile_sha256'])
        self.assertFalse(report['record_equality_verified'])

    def test_csv_profile_changes_and_false_pin(self):
        name = 'csv-profile-revision-comparator'
        code, report = run(name, fixture(name, 'needs-review'))
        self.assertEqual(code, 1)
        self.assertIn('BLANK_ROWS_CHANGED', [x['code'] for x in report['changes']])
        value = fixture(name)
        value['candidate']['profile_sha256'] = '0' * 64
        self.assertEqual(run(name, value)[1]['code'], 'PROFILE_PIN_INVALID')
        value = copy.deepcopy(fixture(name))
        value['candidate']['csv_text'] = 'count,item\n2,fan\n1,lamp\n'
        profile = run('csv-column-profiler',
                      {'format': 'outlands-csv-column-profile-v1',
                       'csv_text': value['candidate']['csv_text']})[1]
        value['candidate']['profile_sha256'] = profile['profile_sha256']
        self.assertIn('HEADER_ORDER_CHANGED', [x['code'] for x in run(name, value)[1]['changes']])

if __name__ == '__main__':
    unittest.main()
