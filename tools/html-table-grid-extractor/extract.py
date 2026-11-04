"""Extract one explicitly selected bounded HTML table into a rectangular grid."""
import html_core as c
import toolkit as t

FORMAT = 'outlands-html-table-grid-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'html', 'table'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    grid, pin, count = c.grid(value['html'], value['table'])
    return {'format': FORMAT, 'status': 'PASS', 'input_sha256': t.digest(raw),
            'grid_sha256': pin, 'grid': grid, 'table_count': count,
            'rendered_browser_layout_verified': False,
            'source_completeness_verified': False, 'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
