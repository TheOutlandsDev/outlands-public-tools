"""Check declared chart marks, axes, series, and units offline."""
import toolkit as t

FORMAT = 'outlands-chart-encoding-v1'
TYPES = {'string', 'integer', 'decimal'}
MARKS = {'bar', 'line', 'scatter'}


def source(row):
    t.fields(row, {'id', 'revision', 'fields'})
    t.identifier(row['id']); t.integer(row['revision'], 10**6, 1)
    t.require(type(row['fields']) is list and 1 <= len(row['fields']) <= 64, 'FIELD_LIMIT')
    fields = {}
    for item in row['fields']:
        t.fields(item, {'id', 'type', 'unit'})
        t.identifier(item['id'])
        t.require(type(item['type']) is str and item['type'] in TYPES, 'TYPE_INVALID')
        t.require(item['unit'] is None or type(item['unit']) is str and t.identifier(item['unit']), 'UNIT_INVALID')
        t.require(item['id'] not in fields, 'FIELD_DUPLICATE')
        fields[item['id']] = item
    return dict(row, fields=[fields[k] for k in sorted(fields)]), fields


def axis(row):
    t.fields(row, {'field', 'scale', 'unit'})
    t.identifier(row['field'])
    t.require(type(row['scale']) is str and row['scale'] in {'category', 'linear'}, 'SCALE_INVALID')
    t.require(row['unit'] is None or type(row['unit']) is str and t.identifier(row['unit']), 'UNIT_INVALID')


def chart(row):
    t.fields(row, {'id', 'revision', 'source', 'source_revision', 'source_sha256', 'mark', 'x', 'y', 'series'})
    for key in ('id', 'source'): t.identifier(row[key])
    for key in ('revision', 'source_revision'): t.integer(row[key], 10**6, 1)
    t.sha(row['source_sha256'])
    t.require(type(row['mark']) is str and row['mark'] in MARKS, 'MARK_INVALID')
    axis(row['x']); axis(row['y'])
    t.require(row['series'] is None or type(row['series']) is str and t.identifier(row['series']), 'SERIES_INVALID')


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'sources', 'charts'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    t.require(type(value['sources']) is list and 1 <= len(value['sources']) <= 32, 'SOURCE_LIMIT')
    t.require(type(value['charts']) is list and 1 <= len(value['charts']) <= 64, 'CHART_LIMIT')
    sources = {}
    for item in value['sources']:
        normalized, fields = source(item)
        t.require(item['id'] not in sources, 'SOURCE_DUPLICATE')
        sources[item['id']] = (normalized, fields, t.digest(t.encode(normalized)))
    seen, assessments = set(), []
    for item in value['charts']:
        chart(item)
        t.require(item['id'] not in seen, 'CHART_DUPLICATE'); seen.add(item['id'])
        selected = sources.get(item['source'])
        t.require(selected is not None and item['source_revision'] == selected[0]['revision'] and item['source_sha256'] == selected[2], 'SOURCE_PIN_INVALID')
        fields = selected[1]
        issues = []
        def issue(code): issues.append(code)
        for name in ('x', 'y'):
            spec = item[name]
            field = fields.get(spec['field'])
            if field is None:
                issue(name.upper() + '_FIELD_MISSING'); continue
            if spec['scale'] == 'category' and field['type'] != 'string' or spec['scale'] == 'linear' and field['type'] not in {'integer', 'decimal'}:
                issue(name.upper() + '_SCALE_TYPE_MISMATCH')
            if spec['unit'] != field['unit']:
                issue(name.upper() + '_UNIT_MISMATCH')
        if item['series'] is not None:
            field = fields.get(item['series'])
            if field is None: issue('SERIES_FIELD_MISSING')
            elif field['type'] != 'string': issue('SERIES_TYPE_MISMATCH')
        if item['x']['field'] == item['y']['field']: issue('AXES_SAME_FIELD')
        if item['mark'] == 'bar' and item['x']['scale'] != 'category': issue('MARK_X_SCALE_MISMATCH')
        if item['mark'] in {'line', 'scatter'} and item['x']['scale'] != 'linear': issue('MARK_X_SCALE_MISMATCH')
        if item['y']['scale'] != 'linear': issue('Y_SCALE_MISMATCH')
        assessments.append({'id': item['id'], 'chart_sha256': t.digest(t.encode(item)), 'valid': not issues, 'issues': sorted(set(issues))})
    return {'format': FORMAT, 'status': 'REVIEW_REQUIRED' if any(not x['valid'] for x in assessments) else 'PASS', 'input_sha256': t.digest(raw), 'sources': [{'id': key, 'sha256': sources[key][2]} for key in sorted(sources)], 'charts': sorted(assessments, key=lambda x: x['id']), 'rendered': False, 'source_values_checked': False, 'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__); parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
