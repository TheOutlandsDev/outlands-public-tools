"""Compare two pinned, explicitly selected HTML table grids offline."""
import html_core as c
import toolkit as t

FORMAT = 'outlands-html-table-revision-v1'


def selected(value):
    t.fields(value, {'html', 'table', 'grid_sha256'})
    t.sha(value['grid_sha256'])
    grid, pin, count = c.grid(value['html'], value['table'])
    t.require(pin == value['grid_sha256'], 'GRID_PIN_INVALID')
    return grid, pin, count


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'baseline', 'candidate'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    before, before_pin, before_count = selected(value['baseline'])
    after, after_pin, after_count = selected(value['candidate'])
    shape_changed = (before['rows'], before['columns']) != (after['rows'], after['columns'])
    changes = []
    for r in range(max(before['rows'], after['rows'])):
        for c in range(max(before['columns'], after['columns'])):
            left = before['cells'][r][c] if r < before['rows'] and c < before['columns'] else None
            right = after['cells'][r][c] if r < after['rows'] and c < after['columns'] else None
            if left != right:
                changes.append({'row': r + 1, 'column': c + 1,
                                'kind': 'ADDED' if left is None else 'REMOVED' if right is None
                                else 'CHANGED'})
    return {'format': FORMAT, 'status': 'REVIEW_REQUIRED' if changes else 'PASS',
            'input_sha256': t.digest(raw), 'baseline_grid_sha256': before_pin,
            'candidate_grid_sha256': after_pin, 'baseline_table_count': before_count,
            'candidate_table_count': after_count, 'shape_changed': shape_changed,
            'changed_cells': changes, 'rendered_browser_layout_verified': False,
            'change_significance_inferred': False, 'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
