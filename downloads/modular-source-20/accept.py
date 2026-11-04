"""Run every invented example and source pin from a freshly extracted archive."""
import argparse
import json
import os
from pathlib import Path
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
    with tempfile.TemporaryDirectory(prefix='modular-source-20-') as directory:
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(directory)
        root = Path(directory) / ('outlands-modular-tools-20-' + value['version'])
        for row in value['tools']:
            tool = root / 'tools' / row['id']
            check = subprocess.run([sys.executable, '-B', 'source_check.py'], cwd=tool,
                                   env=safe_env, capture_output=True, text=True, timeout=60)
            if check.returncode or json.loads(check.stdout)['status'] != 'SOURCE_MATCH':
                raise ValueError('FRESH_SOURCE_CHECK_FAILED')
            demo = subprocess.run([sys.executable, '-B', row['entry'], '--input', 'examples/input.json'],
                                  cwd=tool, env=safe_env, capture_output=True, text=True, timeout=60)
            if demo.returncode or json.loads(demo.stdout)['status'] != 'PASS':
                raise ValueError('FRESH_FICTIONAL_DEMO_FAILED')
    return {'status': 'PASS', 'sha256': receipt['sha256'], 'source_checks': 20,
            'fictional_demos': 20, 'real_data_used': False, 'targets_modified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--checksums', required=True)
    args = parser.parse_args()
    print(json.dumps(accept(args.archive, args.checksums), sort_keys=True))
