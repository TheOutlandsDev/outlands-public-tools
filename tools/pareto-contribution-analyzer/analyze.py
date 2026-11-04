"""Describe exact Pareto contribution ranks and cumulative tie blocks offline."""
import pareto_core as c
import toolkit as t

FORMAT = 'outlands-pareto-contributions-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'snapshot'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    ranking, pin, count = c.analyze(value['snapshot'])
    return {
        'format': FORMAT,
        'status': 'PASS' if ranking['total'] != '0' else 'REVIEW_REQUIRED',
        'input_sha256': t.digest(raw),
        'ranking_sha256': pin,
        'ranking': ranking,
        'row_count': count,
        'issue': None if ranking['total'] != '0' else 'ZERO_TOTAL_UNRANKED_SHARES',
        'source_completeness_verified': False,
        'cause_or_priority_inferred': False,
        'target_changes_performed': False,
    }


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
