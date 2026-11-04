"""Compare two recomputed and pinned JSON structure reports."""
import json_core as core
import toolkit as t

FORMAT = 'outlands-json-structure-compare-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'baseline', 'candidate'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    profiles, pins, sources = [], [], []
    for name in ('baseline', 'candidate'):
        item = value[name]
        t.fields(item, {'json_text', 'profile_sha256'})
        profile, pin, source = core.profile(item['json_text'])
        t.require(t.sha(item['profile_sha256']) == pin, 'PROFILE_PIN_INVALID')
        profiles.append(profile); pins.append(pin); sources.append(source)
    before = {tuple(row['path']): row for row in profiles[0]['paths']}
    after = {tuple(row['path']): row for row in profiles[1]['paths']}
    changes = []
    for path in sorted(before.keys() | after.keys()):
        old, new = before.get(path), after.get(path)
        if old == new:
            continue
        changes.append({'path': list(path), 'baseline': None if old is None else
                        {'occurrences': old['occurrences'], 'types': old['types']},
                        'candidate': None if new is None else
                        {'occurrences': new['occurrences'], 'types': new['types']}})
    return {'format': FORMAT, 'status': 'PASS' if not changes else 'REVIEW',
            'baseline_json_sha256': sources[0], 'candidate_json_sha256': sources[1],
            'baseline_profile_sha256': pins[0], 'candidate_profile_sha256': pins[1],
            'changes': changes, 'value_equality_verified': False,
            'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
