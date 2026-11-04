"""Fictional acceptance and failure boundaries for Batch 96."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
ENTRY = {
    'html-table-grid-extractor': 'extract.py',
    'html-table-revision-comparator': 'compare.py',
    'kanban-board-state-checker': 'board.py',
    'kanban-move-planner': 'move.py',
}

def fixture(name, variant='input'):
    return json.loads((TOOLS / name / 'examples' / (variant + '.json')).read_text(encoding='utf-8'))

def run(name, value):
    with tempfile.TemporaryDirectory(prefix='fictional-html-kanban-') as directory:
        path = Path(directory) / 'input.json'
        path.write_text(json.dumps(value, ensure_ascii=True) + '\n', encoding='utf-8')
        result = subprocess.run([sys.executable, '-B', str(TOOLS / name / ENTRY[name]),
                                 '--input', str(path)], capture_output=True, text=True)
    if result.stderr:
        raise AssertionError(result.stderr)
    return result.returncode, json.loads(result.stdout)

class Batch96(unittest.TestCase):
    def test_fictional_examples_and_source_pins(self):
        for name in ENTRY:
            with self.subTest(name=name):
                code, report = run(name, fixture(name))
                self.assertEqual((code, report['status']), (0, 'PASS'))
                check = subprocess.run([sys.executable, '-B', str(TOOLS / name / 'source_check.py')],
                                       capture_output=True, text=True)
                self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
                self.assertEqual(json.loads(check.stdout)['status'], 'SOURCE_MATCH')
        for name in ('html-table-revision-comparator', 'kanban-board-state-checker',
                     'kanban-move-planner'):
            with self.subTest(review=name):
                code, report = run(name, fixture(name, 'needs-review'))
                self.assertEqual((code, report['status']), (1, 'REVIEW_REQUIRED'))

    def test_html_grid_and_spans(self):
        name = 'html-table-grid-extractor'
        value = fixture(name)
        code, report = run(name, value)
        self.assertEqual(code, 0)
        self.assertEqual((report['grid']['rows'], report['grid']['columns']), (3, 2))
        self.assertEqual(report['grid']['cells'][1][0]['text'], 'fan')
        value['html'] = '<table><tr><th colspan="2">Parts</th></tr><tr><td rowspan="2">fan</td><td>2</td></tr><tr><td>3</td></tr></table>'
        code, report = run(name, value)
        self.assertEqual(code, 0)
        self.assertEqual(report['grid']['cells'][2][0]['anchor'], [2, 1])
        self.assertEqual(report['grid']['cells'][0][1]['anchor'], [1, 1])

    def test_html_unsupported_and_incomplete_markup_refused(self):
        name = 'html-table-grid-extractor'
        for html, expected in [
            ('<table><tr><td>x</td></tr>', 'HTML_NESTING_INVALID'),
            ('<table><tbody><tr><td>x</td></tr></tbody></table>', 'HTML_TAG_UNSUPPORTED'),
            ('<table><tr><td><script>x</script></td></tr></table>', 'HTML_TAG_UNSUPPORTED'),
            ('<table><tr><td colspan="2">x</td></tr><tr><td>y</td></tr></table>', 'HTML_GRID_NOT_RECTANGULAR'),
        ]:
            with self.subTest(html=html):
                value = fixture(name); value['html'] = html
                self.assertEqual(run(name, value), (2, {'status': 'ERROR', 'code': expected}))

    def test_html_revision_pin_and_changed_coordinate(self):
        name = 'html-table-revision-comparator'
        code, report = run(name, fixture(name, 'needs-review'))
        self.assertEqual(code, 1)
        self.assertEqual(report['changed_cells'], [{'row': 2, 'column': 2, 'kind': 'CHANGED'}])
        value = fixture(name)
        value['candidate']['grid_sha256'] = '0' * 64
        self.assertEqual(run(name, value)[1]['code'], 'GRID_PIN_INVALID')

    def test_board_wip_and_position_findings(self):
        name = 'kanban-board-state-checker'
        code, report = run(name, fixture(name, 'needs-review'))
        self.assertEqual(code, 1)
        self.assertIn('WIP_LIMIT_EXCEEDED', [x['code'] for x in report['findings']])
        value = fixture(name)
        value['board']['cards'][2]['position'] = 0
        code, report = run(name, value)
        self.assertEqual(code, 1)
        self.assertIn('POSITION_DUPLICATE', [x['code'] for x in report['findings']])

    def test_board_normalization_and_invalid_references(self):
        name = 'kanban-board-state-checker'
        value = fixture(name)
        pin = run(name, value)[1]['board_sha256']
        value['board']['cards'].reverse()
        value['board']['columns'].reverse()
        value['board']['columns'][0]['allowed_next'].reverse()
        self.assertEqual(run(name, value)[1]['board_sha256'], pin)
        value['board']['columns'][0]['allowed_next'] = ['missing']
        self.assertEqual(run(name, value)[1]['code'], 'TRANSITION_INVALID')

    def test_move_capacity_transition_and_stale_pin(self):
        name = 'kanban-move-planner'
        code, report = run(name, fixture(name, 'needs-review'))
        self.assertEqual(code, 1)
        self.assertIn('TARGET_WIP_LIMIT_EXCEEDED', [x['code'] for x in report['issues']])
        value = fixture(name)
        value['move']['target_column'] = 'backlog'
        value['move']['target_position'] = 1
        self.assertIn('TRANSITION_NOT_ALLOWED', [x['code'] for x in run(name, value)[1]['issues']])
        value = fixture(name)
        value['board_sha256'] = '0' * 64
        self.assertEqual(run(name, value)[1]['code'], 'BOARD_PIN_INVALID')

    def test_move_reorder_and_blocked(self):
        name = 'kanban-move-planner'
        value = fixture(name)
        value['move'] = {'card': 'test_icon', 'target_column': 'doing', 'target_position': 0}
        code, report = run(name, value)
        self.assertEqual(code, 0)
        self.assertNotEqual(report['baseline_board_sha256'], report['candidate_board_sha256'])
        blocked = copy.deepcopy(value)
        blocked['board']['cards'][2]['blocked'] = True
        blocked['board_sha256'] = run('kanban-board-state-checker',
                                     {'format': 'outlands-kanban-board-state-v1',
                                      'board': blocked['board']})[1]['board_sha256']
        code, report = run(name, blocked)
        self.assertEqual(code, 1)
        self.assertIn('CARD_BLOCKED', [x['code'] for x in report['issues']])
        self.assertIsNone(report['candidate_board_sha256'])

if __name__ == '__main__':
    unittest.main()
