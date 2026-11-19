import json
from pathlib import Path
import subprocess
import sys

import pytest


PROGRAM = Path(__file__).resolve().parents[1] / 'lot_identity.py'
PREFIX = 'PX-DEMO'


@pytest.fixture
def reconciliation_input():
    return {
        'queue': [{
            'modality': 'Demo mode',
            'part_number': 'DEMO-PART-B',
            'lot_prefix': PREFIX,
            'recommended_lot_count': 2,
            'recommended_start_by': '2042-03-17',
            'queue_status': 'ACTIVE',
        }],
        'last_lots': [{
            'product': 'DEMO-PART-B',
            'material_template': 'DEMO-TEMPLATE-B',
            'prefix': PREFIX,
            'last_lot_started': PREFIX + 'AAAZ',
            'next_lot_to_start': PREFIX + 'AABA',
        }],
    }


def run_cli(payload, directory):
    source = directory / 'fictional-snapshot.json'
    original = json.dumps(payload, indent=2).encode('utf-8') + b'\n'
    source.write_bytes(original)
    result = subprocess.run(
        [sys.executable, '-I', '-B', str(PROGRAM), '--input', str(source)],
        cwd=directory, capture_output=True, text=True, check=False, timeout=30,
    )
    assert source.read_bytes() == original
    assert list(directory.iterdir()) == [source]
    return result


def assert_refused(result):
    assert result.returncode == 2
    assert result.stdout == ''
    assert result.stderr.strip()
    assert 'Traceback' not in result.stderr
    assert PREFIX not in result.stderr
    assert 'PX-ALT' not in result.stderr
    assert 'fictional-snapshot.json' not in result.stderr


def test_cli_rollover_preserves_saved_input(reconciliation_input, tmp_path):
    result = run_cli(reconciliation_input, tmp_path)

    assert result.returncode == 0
    assert result.stderr == ''
    report = json.loads(result.stdout)
    assert report['status'] == 'reconciled'
    assert report['row_count'] == len(report['rows']) == 1
    row = report['rows'][0]
    assert row['lot_prefix'] == PREFIX
    assert row['last_lot_started'] == PREFIX + 'AAAZ'
    assert row['next_lot_to_start'] == PREFIX + 'AABA'
    assert row['recommended_lot_ids'] == [PREFIX + 'AABA', PREFIX + 'AABB']


def test_duplicate_queue_prefix_fails_closed(reconciliation_input, tmp_path):
    queue = reconciliation_input['queue']
    queue.append(queue[0].copy())

    assert_refused(run_cli(reconciliation_input, tmp_path))


def test_duplicate_mapping_prefix_fails_closed(reconciliation_input, tmp_path):
    mappings = reconciliation_input['last_lots']
    mappings.append(mappings[0].copy())

    assert_refused(run_cli(reconciliation_input, tmp_path))


def test_exhausted_sequence_fails_closed(reconciliation_input, tmp_path):
    mappings = reconciliation_input['last_lots']
    mappings.append({
        'product': None,
        'material_template': None,
        'prefix': 'PX-ALT',
        'last_lot_started': 'PX-ALTZZZZ',
        'next_lot_to_start': 'PX-ALTAAAA',
    })

    assert_refused(run_cli(reconciliation_input, tmp_path))
