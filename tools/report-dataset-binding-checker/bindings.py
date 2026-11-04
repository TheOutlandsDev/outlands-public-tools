"""Check offline report field bindings against pinned dataset schemas."""
import toolkit as t

FORMAT = 'outlands-report-dataset-bindings-v1'
TYPES = {'string', 'integer', 'decimal', 'boolean'}


def dataset(row):
    t.fields(row, {'id', 'revision', 'fields'})
    t.identifier(row['id']); t.integer(row['revision'], 10**6, 1)
    t.require(type(row['fields']) is list and 1 <= len(row['fields']) <= 64, 'FIELD_LIMIT')
    found = {}
    for field in row['fields']:
        t.fields(field, {'id', 'type', 'nullable'})
        t.identifier(field['id']); t.require(type(field['type']) is str and field['type'] in TYPES, 'TYPE_INVALID')
        t.require(type(field['nullable']) is bool, 'NULLABLE_INVALID')
        t.require(field['id'] not in found, 'FIELD_DUPLICATE')
        found[field['id']] = field
    normalized = dict(row, fields=[found[key] for key in sorted(found)])
    return normalized, found


def report(row):
    t.fields(row, {'id', 'revision', 'dataset', 'dataset_revision', 'dataset_sha256', 'fields'})
    for key in ('id', 'dataset'): t.identifier(row[key])
    for key in ('revision', 'dataset_revision'): t.integer(row[key], 10**6, 1)
    t.sha(row['dataset_sha256'])
    t.require(type(row['fields']) is list and 1 <= len(row['fields']) <= 64, 'BINDING_LIMIT')
    found = {}
    for field in row['fields']:
        t.fields(field, {'id', 'source', 'expected_type', 'required'})
        t.identifier(field['id']); t.identifier(field['source'])
        t.require(type(field['expected_type']) is str and field['expected_type'] in TYPES, 'TYPE_INVALID')
        t.require(type(field['required']) is bool, 'REQUIRED_INVALID')
        t.require(field['id'] not in found, 'BINDING_DUPLICATE')
        found[field['id']] = field
    return dict(row, fields=[found[key] for key in sorted(found)]), found


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'datasets', 'reports'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    t.require(type(value['datasets']) is list and 1 <= len(value['datasets']) <= 32, 'DATASET_LIMIT')
    t.require(type(value['reports']) is list and 1 <= len(value['reports']) <= 32, 'REPORT_LIMIT')
    datasets = {}
    for item in value['datasets']:
        normalized, fields = dataset(item)
        t.require(item['id'] not in datasets, 'DATASET_DUPLICATE')
        datasets[item['id']] = (normalized, fields, t.digest(t.encode(normalized)))
    seen, findings, assessments = set(), [], []
    for item in value['reports']:
        normalized, bindings = report(item)
        t.require(item['id'] not in seen, 'REPORT_DUPLICATE'); seen.add(item['id'])
        selected = datasets.get(item['dataset'])
        t.require(selected is not None and item['dataset_revision'] == selected[0]['revision'] and item['dataset_sha256'] == selected[2], 'DATASET_PIN_INVALID')
        issues = []
        for alias in sorted(bindings):
            binding = bindings[alias]
            source = selected[1].get(binding['source'])
            if source is None: code = 'SOURCE_MISSING'
            elif source['type'] != binding['expected_type']: code = 'TYPE_MISMATCH'
            elif binding['required'] and source['nullable']: code = 'REQUIRED_NULLABLE'
            else: continue
            issues.append({'field': alias, 'code': code})
        findings.extend({'report': item['id'], **issue} for issue in issues)
        assessments.append({'id': item['id'], 'binding_sha256': t.digest(t.encode(normalized)), 'valid': not issues, 'field_count': len(bindings), 'issues': issues})
    return {'format': FORMAT, 'status': 'REVIEW_REQUIRED' if findings else 'PASS', 'input_sha256': t.digest(raw), 'datasets': [{'id': key, 'sha256': datasets[key][2]} for key in sorted(datasets)], 'reports': sorted(assessments, key=lambda x: x['id']), 'findings': sorted(findings, key=lambda x: (x['report'], x['field'])), 'data_values_checked': False, 'source_completeness_verified': False, 'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__); parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
