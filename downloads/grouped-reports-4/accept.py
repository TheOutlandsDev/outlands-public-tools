"""Run every invented example and source pin from a freshly extracted archive."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

from build import plan
from verify import verify


def accept(archive_path, checksum_path):
    receipt = verify(archive_path, checksum_path)
    value = plan()
    safe_env = {key: os.environ[key] for key in ('PATH', 'SystemRoot', 'SYSTEMROOT', 'TEMP', 'TMP') if key in os.environ}
    safe_env.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    local_temp = None
    if os.name == 'nt':
        local_temp = Path(os.environ.get('LOCALAPPDATA', '')) / 'Temp'
        if not local_temp.is_dir():
            raise ValueError('LOCAL_WINDOWS_TEMP_REQUIRED')
    with tempfile.TemporaryDirectory(prefix='grouped-reports-4-', dir=local_temp) as directory:
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(directory)
        root = Path(directory) / ('outlands-grouped-reports-4-' + value['version'])
        for row in value['tools']:
            tool = root / 'tools' / row['id']
            check = subprocess.run([sys.executable, '-B', 'source_check.py'], cwd=tool,
                                   env=safe_env, capture_output=True, text=True, timeout=60)
            if check.returncode or json.loads(check.stdout)['status'] != 'SOURCE_MATCH':
                raise ValueError('FRESH_SOURCE_CHECK_FAILED')
            demo = subprocess.run([sys.executable, '-B', row['entry'], '--input', str(tool / 'examples/input.json')],
                                  cwd=tool, env=safe_env, capture_output=True, text=True, timeout=60)
            try:
                outcome = json.loads(demo.stdout)
            except (ValueError, TypeError):
                outcome = {}
            expected = 'REVIEW_REQUIRED' if row['id'] == 'grouped-report-scenario-comparator' else 'PASS'
            expected_exit = 1 if expected == 'REVIEW_REQUIRED' else 0
            if demo.returncode != expected_exit or outcome.get('status') != expected:
                code = outcome.get('code', 'UNSPECIFIED')
                code = code if type(code) is str and re.fullmatch('[A-Z_]{1,64}', code) else 'UNSPECIFIED'
                raise ValueError('FRESH_FICTIONAL_DEMO_FAILED:' + row['id'] + ':' + code + ':' + str(demo.returncode))
    return {'status': 'PASS', 'sha256': receipt['sha256'], 'source_checks': 4,
            'fictional_demos': 4, 'expected_review_cases': 1,
            'real_data_used': False, 'targets_modified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--checksums', required=True)
    args = parser.parse_args()
    print(json.dumps(accept(args.archive, args.checksums), sort_keys=True))
