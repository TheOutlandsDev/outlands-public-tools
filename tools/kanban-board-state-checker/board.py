"""Check declared Kanban positions, WIP limits, and transition references."""
import board_core as c
import toolkit as t

FORMAT = 'outlands-kanban-board-state-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'board'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    _, pin, counts, findings = c.assess(value['board'])
    return {'format': FORMAT, 'status': 'REVIEW_REQUIRED' if findings else 'PASS',
            'input_sha256': t.digest(raw), 'board_sha256': pin,
            'column_counts': counts, 'findings': findings,
            'source_completeness_verified': False,
            'operational_state_verified': False, 'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
