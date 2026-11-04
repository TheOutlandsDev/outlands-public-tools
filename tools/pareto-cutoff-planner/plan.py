"""Apply a caller-selected contribution cutoff to exact Pareto tie blocks."""
from fractions import Fraction
import pareto_core as c
import toolkit as t

FORMAT = 'outlands-pareto-cutoff-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'snapshot', 'ranking_sha256', 'cutoff'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    t.sha(value['ranking_sha256'])
    cutoff = c.decimal(value['cutoff'], 1)
    ranking, pin, count = c.analyze(value['snapshot'])
    t.require(value['ranking_sha256'] == pin, 'RANKING_PIN_INVALID')
    if ranking['total'] == '0':
        selection = None
        status = 'REVIEW_REQUIRED'
        issue = 'ZERO_TOTAL_NO_CUTOFF_SELECTION'
    else:
        selected = []
        covered = Fraction(0)
        boundary = None
        if cutoff > 0:
            for block in ranking['blocks']:
                selected.extend(block['categories'])
                covered = Fraction(block['cumulative_share'])
                boundary = block['rank']
                if covered >= cutoff: break
        selection = {
            'cutoff': c.render(cutoff),
            'selected_categories': sorted(selected),
            'selected_count': len(selected),
            'boundary_rank': boundary,
            'covered_share': c.ratio(covered),
            'whole_block_overshoot': c.ratio(covered - cutoff),
        }
        status = 'PASS'
        issue = None
    return {
        'format': FORMAT,
        'status': status,
        'input_sha256': t.digest(raw),
        'ranking_sha256': pin,
        'snapshot_sha256': ranking['snapshot_sha256'],
        'row_count': count,
        'selection': selection,
        'issue': issue,
        'threshold_chosen_by_tool': False,
        'source_completeness_verified': False,
        'action_authorized': False,
    }


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
