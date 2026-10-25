"""Generate and classify an original fictional Source Inventory workspace."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import classify_inventory as classifier
import source_inventory as inventory


def create(destination: Path) -> dict:
    target = classifier._absolute(destination)
    inventory._directory(target.parent)
    if target.exists() or target.is_symlink():
        raise ValueError('Fresh destination required')
    target.mkdir(mode=0o700, exist_ok=False)
    source = target / 'fictional-source'; source.mkdir(mode=0o700)
    (source / 'docs').mkdir(mode=0o700)
    fixtures = {'app.py': '# Fictional example only.\n', 'README.md': '# Fictional project\n',
                'docs/guide.md': 'Fictional documentation.\n', 'scratch.txt': 'Fictional unmatched item.\n'}
    for name, text in fixtures.items():
        inventory._exclusive_write(source / name, text.encode('utf-8'))
    reports = target / 'inventories'; reports.mkdir(mode=0o700)
    run, _ = inventory.snapshot(source, reports, 'fictional')
    config = {'schema_version': 'outlands.path_rules.v1', 'case_sensitive': True, 'rules': [
        {'id': 'docs-first', 'category': 'documentation', 'kind': 'prefix', 'value': 'docs/'},
        {'id': 'markdown', 'category': 'text', 'kind': 'suffix', 'value': '.md'},
        {'id': 'python', 'category': 'source', 'kind': 'suffix', 'value': '.py'}]}
    rules = target / 'rules.json'
    inventory._exclusive_write(rules, (json.dumps(config, indent=2) + '\n').encode('utf-8'))
    result = classifier.classify(run, rules, target / 'classification')
    return {'result': 'FICTIONAL_CLASSIFICATION_CREATED', 'inventory_run': run.relative_to(target).as_posix(),
            'rules': 'rules.json', 'output': 'classification', 'file_count': result['file_count'],
            'unmatched_files': result['unmatched_files'], 'overlapping_files': result['overlapping_files'],
            'contains_real_data': False}


def main(argv=None):
    parser = classifier.Parser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    try:
        args = parser.parse_args(argv)
        print(json.dumps(create(args.destination), sort_keys=True))
        return 0
    except (classifier.ClassificationError, inventory.InventoryError, OSError, ValueError):
        print(json.dumps({'result': 'INCOMPLETE', 'error': 'FRESH_TRUSTED_DESTINATION_REQUIRED'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
