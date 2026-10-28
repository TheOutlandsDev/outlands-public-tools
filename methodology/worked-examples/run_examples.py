"""Three fictional workflows. Requires the complete or release-QA source package."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

def run(script, args, expected):
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / script), *map(str, args)],
                            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=60)
    if result.returncode != expected:
        raise ValueError('EXAMPLE_COMMAND_FAILED')
    data = json.loads(result.stdout)
    return data

def examples(destination):
    destination = Path(destination)
    if not destination.is_absolute() or destination.exists() or not destination.parent.is_dir():
        raise ValueError('NEW_ABSOLUTE_WORKSPACE_REQUIRED')
    destination = destination.resolve()
    if destination.is_relative_to(ROOT):
        raise ValueError('EXTERNAL_WORKSPACE_REQUIRED')
    required = ['tools/source-inventory/source_inventory.py',
                'tools/source-inventory-diff/inventory_diff.py',
                'tools/dependency-lock-diff/lock_diff.py',
                'tools/documentation-check/docs_check.py']
    if not all((ROOT / p).is_file() for p in required):
        raise ValueError('COMPLETE_OR_RELEASE_QA_PACKAGE_REQUIRED')
    destination.mkdir(mode=0o700)
    source = destination / 'fictional-source'
    reports = destination / 'inventory-reports'
    source.mkdir(); reports.mkdir()
    (source / 'guide.md').write_text('# Orchard demo\nRevision one.\n', encoding='utf-8')
    (source / 'sample.txt').write_text('Entirely fictional marker.\n', encoding='utf-8')
    command = ['--root', source, '--output-dir', reports, '--label', 'orchard', '--tree']
    before = run(required[0], command, 0)
    (source / 'guide.md').write_text('# Orchard demo\nRevision two.\n', encoding='utf-8')
    (source / 'added.txt').write_text('An invented addition.\n', encoding='utf-8')
    after = run(required[0], command, 0)
    old = reports / before['snapshot']; new = reports / after['snapshot']
    match = run(required[1], ['--before', old, '--after', old], 0)
    changed = run(required[1], ['--before', old, '--after', new], 1)
    if match['status'] != 'MATCHING_SELECTED_RECORDS' or changed['status'] != 'REVIEW_REQUIRED':
        raise ValueError('INVENTORY_EXPECTATION_FAILED')
    locks = ROOT / 'tools/dependency-lock-diff/examples'
    equivalent = run(required[2], ['--before', locks / 'before.lock', '--after', locks / 'equivalent.lock'], 0)
    different = run(required[2], ['--before', locks / 'before.lock', '--after', locks / 'after.lock'], 1)
    if equivalent['status'] != 'MATCHING_LOCK_RECORDS' or different['status'] != 'LOCK_DIFFERENCES_REPORTED':
        raise ValueError('LOCK_EXPECTATION_FAILED')
    documents = destination / 'fictional-documents'; documents.mkdir()
    (documents / 'README.md').write_text('# Orchard handoff\n[Guide](guide.md)\n', encoding='utf-8')
    broken = run(required[3], ['--root', documents], 1)
    (documents / 'guide.md').write_text('# Orchard guide\nAll content was invented.\n', encoding='utf-8')
    fixed = run(required[3], ['--root', documents], 0)
    if broken['status'] == 'PASS' or fixed['status'] != 'PASS':
        raise ValueError('DOCUMENT_EXPECTATION_FAILED')
    receipt = {'schema': 1, 'data': 'fictional', 'examples_passed': 3, 'command_checks': 8,
               'inventory': {'unchanged': match['status'], 'edited': changed['status']},
               'dependency_locks': {'equivalent': equivalent['status'], 'changed': different['status']},
               'documentation': {'missing_link': broken['status'], 'corrected': fixed['status']},
               'limits': 'Selected local source/metadata checks; no deployment, install, authenticity or production acceptance.'}
    (destination / 'observed-results.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, sort_keys=True))
    return receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    try:
        examples(parser.parse_args().workspace)
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, json.JSONDecodeError):
        print(json.dumps({'status': 'ERROR', 'code': 'EXAMPLE_NOT_COMPLETED'}))
        sys.exit(1)
