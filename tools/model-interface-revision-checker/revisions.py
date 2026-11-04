"""Compare two pinned model port-interface declarations for selected changes."""
import model_core as c
import toolkit as t

FORMAT = 'outlands-model-interface-revision-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'baseline', 'candidate', 'baseline_sha256', 'candidate_sha256'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    t.sha(value['baseline_sha256']); t.sha(value['candidate_sha256'])
    old, old_ports, old_symbols, old_pin = c.manifest(value['baseline'])
    new, new_ports, new_symbols, new_pin = c.manifest(value['candidate'])
    t.require(value['baseline_sha256'] == old_pin and value['candidate_sha256'] == new_pin, 'MANIFEST_PIN_INVALID')
    t.require(old['id'] == new['id'] and old['revision'] < new['revision'], 'REVISION_PAIR_INVALID')
    issues, additions = [], {'inputs':[], 'outputs':[]}
    if old['preprocessing_sha256'] != new['preprocessing_sha256']:
        issues.append({'side':'manifest','port':None,'code':'PREPROCESSING_CHANGED'})
    for side in ('inputs','outputs'):
        before, after = old_ports[side], new_ports[side]
        for name in sorted(before):
            if name not in after:
                issues.append({'side':side,'port':name,'code':'PORT_REMOVED'})
                continue
            left, right = before[name], after[name]
            left_sig, right_sig = c.port_signature(left,old_symbols), c.port_signature(right,new_symbols)
            if left_sig['dtype'] != right_sig['dtype']:
                issues.append({'side':side,'port':name,'code':'DTYPE_CHANGED'})
            if left_sig['shape'] != right_sig['shape']:
                issues.append({'side':side,'port':name,'code':'SHAPE_CHANGED'})
            if side == 'inputs' and not left['required'] and right['required']:
                issues.append({'side':side,'port':name,'code':'INPUT_BECAME_REQUIRED'})
            if side == 'outputs' and left['required'] and not right['required']:
                issues.append({'side':side,'port':name,'code':'OUTPUT_GUARANTEE_WEAKENED'})
        for name in sorted(set(after)-set(before)):
            additions[side].append(name)
            if side == 'inputs' and after[name]['required']:
                issues.append({'side':side,'port':name,'code':'NEW_REQUIRED_INPUT'})
    issues.sort(key=lambda x:(x['side'],x['port'] or '',x['code']))
    return {
        'format':FORMAT,
        'status':'REVIEW_REQUIRED' if issues else 'PASS',
        'input_sha256':t.digest(raw),
        'model':old['id'],
        'baseline_revision':old['revision'],
        'candidate_revision':new['revision'],
        'baseline_sha256':old_pin,
        'candidate_sha256':new_pin,
        'added_ports':additions,
        'issues':issues,
        'artifact_bytes_verified':False,
        'runtime_compatibility_verified':False,
        'deployment_authorized':False,
    }


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
