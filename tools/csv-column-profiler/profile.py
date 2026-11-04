"""Summarize bounded raw CSV columns without a field map or type inference."""
import csv_core as c
import toolkit as t

FORMAT = 'outlands-csv-column-profile-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'csv_text'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    profile, pin, csv_pin = c.profile(value['csv_text'])
    return {'format': FORMAT, 'status': 'PASS', 'input_sha256': t.digest(raw),
            'csv_sha256': csv_pin, 'profile_sha256': pin, 'profile': profile,
            'types_inferred': False, 'source_completeness_verified': False,
            'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
