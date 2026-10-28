"""Extract and verify new focused packages, then install/test only disposable apps."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

def execute(command, cwd):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), timeout=240)
    if result.returncode:
        # Dependency diagnostics can be inspected privately; no paths/tokens/logs in public receipts.
        print(result.stdout[-3000:], file=sys.stderr); print(result.stderr[-3000:], file=sys.stderr)
        raise ValueError('Extracted application check failed')
    return result.stdout

def accept(packages, workspace):
    assert workspace.is_absolute() and not workspace.exists()
    workspace.mkdir()
    matrix = json.loads((packages / 'release-matrix.json').read_text(encoding='utf-8'))
    receipts = []
    for item in matrix['applications']:
        data = (packages / item['filename']).read_bytes()
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
        prefix = item['app'] + '-' + item['version'] + '/'
        with zipfile.ZipFile(packages / item['filename']) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names)) == item['files']
            assert all(n.startswith(prefix) and '\\' not in n and '..' not in n.split('/') and ':' not in n for n in names)
            manifest = json.loads(archive.read(prefix + 'SOURCE-MANIFEST.json'))
            assert set(names) == {prefix + r['path'] for r in manifest['files']} | {prefix + 'SOURCE-MANIFEST.json'}
            for row in manifest['files']:
                member = archive.read(prefix + row['path'])
                assert len(member) == row['bytes'] and hashlib.sha256(member).hexdigest() == row['sha256']
            archive.extractall(workspace)
        app = workspace / prefix
        private = workspace / (item['app'] + '-private')
        if item['app'] == 'local-site-builder':
            execute(['npm.cmd' if os.name == 'nt' else 'npm', 'ci'], app)
            execute(['node', 'scripts/source-check.js'], app)
            execute(['node', '--test', '--test-concurrency=1', 'tests/app.test.js', 'tests/doctor.test.js'], app)
            result = execute(['node', 'scripts/download-check.js', '--workspace', str(private)], app)
        else:
            execute([sys.executable, '-B', 'source_check.py'], app)
            execute([sys.executable, '-B', '-W', 'error', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], app)
            execute(['node', '--test', 'tests/frontend.test.mjs'], app)
            result = execute([sys.executable, '-B', 'examples/download_check.py', '--workspace', str(private)], app)
        receipt = json.loads(result.strip().splitlines()[-1]); assert receipt['status'] == 'PASS'
        receipts.append(receipt)
    (workspace / 'acceptance.json').write_text(json.dumps(receipts, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='PASS', applications=receipts)))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages', type=Path, required=True); parser.add_argument('--workspace', type=Path, required=True)
    options = parser.parse_args(); accept(options.packages.resolve(), options.workspace)
