"""Report bounded JSON paths and type counts without reporting values."""
import json_core as core
import toolkit as t

FORMAT = 'outlands-json-structure-profile-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'json_text'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    shape, pin, source = core.profile(value['json_text'])
    return {'format': FORMAT, 'status': 'PASS', 'input_sha256': t.digest(raw),
            'json_sha256': source, 'profile_sha256': pin, 'profile': shape,
            'values_reported': False, 'completeness_verified': False}


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
