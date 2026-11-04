"""Validate supplied model input and output interface manifests offline."""
import model_core as c
import toolkit as t

FORMAT = 'outlands-model-interface-manifest-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'manifests'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    t.require(type(value['manifests']) is list and 1 <= len(value['manifests']) <= 32, 'MANIFEST_LIMIT')
    seen, summaries = set(), []
    for row in value['manifests']:
        normalized, ports, symbols, pin = c.manifest(row)
        t.require(normalized['id'] not in seen, 'MANIFEST_DUPLICATE'); seen.add(normalized['id'])
        summaries.append({'id':normalized['id'], 'revision':normalized['revision'], 'sha256':pin, 'input_ports':len(ports['inputs']), 'output_ports':len(ports['outputs']), 'dynamic_symbols':len(symbols)})
    return {'format':FORMAT, 'status':'PASS', 'input_sha256':t.digest(raw), 'manifests':sorted(summaries,key=lambda x:x['id']), 'artifact_bytes_verified':False, 'preprocessing_verified':False, 'runtime_compatibility_verified':False, 'target_changes_performed':False}


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
