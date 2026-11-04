"""Assign supplied date-only rows to ISO weeks and count each week."""
import week_core as c
import toolkit as t

FORMAT = 'outlands-iso-week-cohort-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'snapshot'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    cohort, pin = c.analyze(value['snapshot'])
    return {'format': FORMAT, 'status': 'PASS', 'input_sha256': t.digest(raw),
            'cohort_sha256': pin, 'cohort': cohort,
            'timezone_or_timestamp_inferred': False,
            'source_completeness_verified': False, 'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
