"""Fictional CLI acceptance and failure boundaries for four offline tools."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
ENTRY = {
    'report-parameter-contract-checker': 'parameters.py',
    'report-dataset-binding-checker': 'bindings.py',
    'chart-encoding-contract-checker': 'charts.py',
    'report-chart-coverage-reconciler': 'coverage.py',
}


def example(name):
    return json.loads((TOOLS / name / 'examples/input.json').read_text(encoding='utf-8'))


def invoke(name, value):
    with tempfile.TemporaryDirectory(prefix='fictional-chart-contract-') as directory:
        input_path = Path(directory) / 'input.json'
        input_path.write_text(json.dumps(value, ensure_ascii=True) + '\n', encoding='utf-8')
        process = subprocess.run([sys.executable, '-B', str(TOOLS / name / ENTRY[name]), '--input', str(input_path)], capture_output=True, text=True)
    if process.stderr:
        raise AssertionError(process.stderr)
    return process.returncode, json.loads(process.stdout)


class ReportChartContracts(unittest.TestCase):
    def test_fictional_examples_and_pins(self):
        for name in ENTRY:
            with self.subTest(name=name):
                code, result = invoke(name, example(name))
                self.assertEqual((code, result['status']), (0, 'PASS'))
                process = subprocess.run([sys.executable, '-B', str(TOOLS / name / 'source_check.py')], capture_output=True, text=True)
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
                self.assertEqual(json.loads(process.stdout)['status'], 'SOURCE_MATCH')

    def test_report_parameter_cases_and_stale_pin(self):
        name = 'report-parameter-contract-checker'
        value = example(name)
        value['cases'][0]['values'] = {'region': 'west', 'mode': 'detailed', 'include_detail': True}
        self.assertEqual(invoke(name, value)[0], 0)
        value['cases'][0]['values'] = {'region': 'east', 'include_detail': True}
        code, result = invoke(name, value)
        self.assertEqual(code, 1)
        self.assertIn('INACTIVE_VALUE', [f['code'] for f in result['cases'][0]['findings']])
        value['cases'][0]['report_sha256'] = '0' * 64
        self.assertEqual(invoke(name, value)[1]['code'], 'REPORT_PIN_INVALID')

    def test_report_parameter_cycles_and_bad_default(self):
        name = 'report-parameter-contract-checker'
        value = example(name)
        value['reports'][0]['parameters'][0]['when'] = {'parameter': 'mode', 'equals': 'summary'}
        value['reports'][0]['parameters'][1]['when'] = {'parameter': 'region', 'equals': 'east'}
        self.assertEqual(invoke(name, value)[1]['code'], 'DEPENDENCY_CYCLE')
        value = example(name)
        value['reports'][0]['parameters'][0]['default'] = 'north'
        self.assertEqual(invoke(name, value)[1]['code'], 'DEFAULT_INVALID')

    def test_dataset_binding_mismatch_and_pin(self):
        name = 'report-dataset-binding-checker'
        value = example(name)
        value['reports'][0]['fields'][0]['source'] = 'missing'
        code, result = invoke(name, value)
        self.assertEqual(code, 1)
        self.assertEqual(result['findings'][0]['code'], 'SOURCE_MISSING')
        value = example(name)
        value['reports'][0]['fields'][1]['required'] = True
        self.assertEqual(invoke(name, value)[1]['findings'][0]['code'], 'REQUIRED_NULLABLE')
        value['reports'][0]['dataset_sha256'] = 'f' * 64
        self.assertEqual(invoke(name, value)[1]['code'], 'DATASET_PIN_INVALID')

    def test_chart_encoding_rules_and_pin(self):
        name = 'chart-encoding-contract-checker'
        value = example(name)
        value['charts'][0]['mark'] = 'scatter'
        value['charts'][0]['y']['unit'] = 'meters'
        code, result = invoke(name, value)
        self.assertEqual(code, 1)
        self.assertEqual(set(result['charts'][0]['issues']), {'MARK_X_SCALE_MISMATCH', 'Y_UNIT_MISMATCH'})
        value['charts'][0]['source_sha256'] = '0' * 64
        self.assertEqual(invoke(name, value)[1]['code'], 'SOURCE_PIN_INVALID')

    def test_chart_coverage_missing_duplicate_and_order(self):
        name = 'report-chart-coverage-reconciler'
        value = example(name)
        value['charts'][0]['series'][0]['point_row_ids'] = ['sample_b', 'sample_a']
        self.assertEqual(invoke(name, value)[1]['charts'][0]['series'][0]['issues'], ['ORDER_MISMATCH'])
        value['charts'][0]['series'][0]['point_row_ids'] = ['sample_a', 'sample_a']
        code, result = invoke(name, value)
        self.assertEqual(code, 1)
        self.assertEqual(set(result['charts'][0]['series'][0]['issues']), {'DUPLICATE_POINT', 'MISSING_POINT'})
        value['charts'][0]['series'][0]['point_row_ids'] = ['sample_a', 'sample_c']
        self.assertEqual(set(invoke(name, value)[1]['charts'][0]['series'][0]['issues']), {'MISSING_POINT', 'UNEXPECTED_POINT'})
        value['charts'][0]['snapshot_sha256'] = 'f' * 64
        self.assertEqual(invoke(name, value)[1]['code'], 'SNAPSHOT_PIN_INVALID')

    def test_duplicate_json_key_refused(self):
        name = 'report-parameter-contract-checker'
        with tempfile.TemporaryDirectory(prefix='fictional-chart-contract-') as directory:
            path = Path(directory) / 'input.json'
            path.write_text('{"format":"x","format":"y"}', encoding='utf-8')
            process = subprocess.run([sys.executable, '-B', str(TOOLS / name / ENTRY[name]), '--input', str(path)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(json.loads(process.stdout)['code'], 'JSON_DUPLICATE_KEY')


if __name__ == '__main__': unittest.main()
