"""Compare two pinned, unmapped CSV column profiles offline."""
import csv_core as c
import toolkit as t

FORMAT = 'outlands-csv-profile-revision-v1'


def selected(value):
    t.fields(value, {'csv_text', 'profile_sha256'})
    t.sha(value['profile_sha256'])
    profile, pin, csv_pin = c.profile(value['csv_text'])
    t.require(pin == value['profile_sha256'], 'PROFILE_PIN_INVALID')
    return profile, pin, csv_pin


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'baseline', 'candidate'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    before, before_pin, before_csv = selected(value['baseline'])
    after, after_pin, after_csv = selected(value['candidate'])
    changes = []
    if before['row_count'] != after['row_count']:
        changes.append({'header': None, 'code': 'ROW_COUNT_CHANGED'})
    if before['headers'] != after['headers']:
        if set(before['headers']) == set(after['headers']):
            changes.append({'header': None, 'code': 'HEADER_ORDER_CHANGED'})
        else:
            for header in sorted(set(before['headers']) - set(after['headers'])):
                changes.append({'header': header, 'code': 'HEADER_REMOVED'})
            for header in sorted(set(after['headers']) - set(before['headers'])):
                changes.append({'header': header, 'code': 'HEADER_ADDED'})
    left = {x['header']: x for x in before['columns']}
    right = {x['header']: x for x in after['columns']}
    for header in sorted(left.keys() & right.keys()):
        for field in ('blank_rows', 'nonblank_rows', 'distinct_nonblank',
                      'minimum_length', 'maximum_length'):
            if left[header][field] != right[header][field]:
                changes.append({'header': header, 'code': field.upper() + '_CHANGED',
                                'baseline': left[header][field], 'candidate': right[header][field]})
    return {'format': FORMAT, 'status': 'REVIEW_REQUIRED' if changes else 'PASS',
            'input_sha256': t.digest(raw), 'baseline_profile_sha256': before_pin,
            'candidate_profile_sha256': after_pin, 'baseline_csv_sha256': before_csv,
            'candidate_csv_sha256': after_csv, 'changes': changes,
            'record_equality_verified': False, 'types_inferred': False,
            'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
