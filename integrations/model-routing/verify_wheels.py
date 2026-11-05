"""Fresh, offline single-tool and collection installs for local pilot wheels."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
ENTRIES = {
    'model-capability-checker': ('outlands_model_capability_checker.models',),
    'request-routing-checker': ('outlands_request_routing_checker.routes',),
    'fallback-chain-checker': ('outlands_fallback_chain_checker.fallbacks',),
    'inference-receipt-reconciler': ('outlands_inference_receipt_reconciler.receipts',),
}


def run(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, text=True, capture_output=True, env=env)


def verify(directory: Path) -> dict:
    directory = directory.resolve()
    manifest = json.loads((directory / 'MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['format'] == 'outlands-model-routing-wheel-pilot-v1'
    assert len(manifest['wheels']) == 5
    expected = {row['filename']: row['sha256'] for row in manifest['wheels']}
    assert set(expected) == {p.name for p in directory.glob('*.whl')}
    assert (directory / 'SHA256SUMS.txt').read_text(encoding='ascii') == ''.join(
        digest + '  ' + name + '\n' for name, digest in expected.items())
    for name, digest in expected.items():
        wheel = directory / name
        assert hashlib.sha256(wheel.read_bytes()).hexdigest() == digest
        with zipfile.ZipFile(wheel) as archive:
            members = archive.namelist()
            assert members and len(members) == len(set(members))
            assert all(not item.startswith('/') and '..' not in Path(item).parts and ':' not in item
                       for item in members)
            for item in members:
                data = archive.read(item)
                assert not re.search(rb'[A-Za-z]:[\\/]|/(?:home|Users)/', data), (name, item)
                assert b'appdata' not in data.lower(), (name, item)

    results = []
    with tempfile.TemporaryDirectory(prefix='outlands-routing-install-') as temporary:
        for tool, (module,) in ENTRIES.items():
            environment = Path(temporary) / tool
            run(sys.executable, '-m', 'venv', str(environment))
            python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            command = environment / ('Scripts' if os.name == 'nt' else 'bin') / ('outlands-' + tool)
            wheel = next(directory.glob('outlands_' + tool.replace('-', '_') + '-*.whl'))
            run(str(python), '-m', 'pip', 'install', '--no-index', '--no-deps', str(wheel))
            sample = ROOT / 'tools' / tool / 'examples/input.json'
            result = run(str(command), '--input', str(sample))
            report = json.loads(result.stdout)
            assert report['status'] == 'PASS' and report['format'].endswith('-report-v1')
            demo = run(str(command) + '-demo')
            assert json.loads(demo.stdout)['status'] == 'PASS'
            api = run(str(python), '-c', 'import importlib,json,sys; '
                      'm=importlib.import_module(sys.argv[1]); '
                      'r=m.check(open(sys.argv[2],"rb").read()); '
                      'print(json.dumps({"status":r["status"],"format":r["format"]}))',
                      module, str(sample))
            assert json.loads(api.stdout)['status'] == 'PASS'
            results.append({'tool': tool, 'single_install': 'PASS', 'cli': 'PASS',
                            'embedded_demo': 'PASS', 'api': 'PASS'})

        environment = Path(temporary) / 'collection'
        run(sys.executable, '-m', 'venv', str(environment))
        python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        scripts = environment / ('Scripts' if os.name == 'nt' else 'bin')
        run(str(python), '-m', 'pip', 'install', '--no-index', '--find-links', str(directory),
            'outlands-model-routing-collection==1.0.0')
        listed = run(str(scripts / 'outlands-model-routing')).stdout.splitlines()
        assert listed == ['outlands-' + name for name in ENTRIES]
        for tool in ENTRIES:
            result = run(str(scripts / ('outlands-' + tool)), '--input',
                         str(ROOT / 'tools' / tool / 'examples/input.json'))
            assert json.loads(result.stdout)['status'] == 'PASS'
            demo = run(str(scripts / ('outlands-' + tool + '-demo')))
            assert json.loads(demo.stdout)['status'] == 'PASS'

    return {'status': 'PASS', 'wheels': len(expected), 'individual': results,
            'collection': 'PASS', 'wheel_path_and_private_marker_audit': 'PASS'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheels', required=True, type=Path)
    print(json.dumps(verify(parser.parse_args().wheels)))
