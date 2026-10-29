"""Compare stored text/table blocks by explicit document position, without rendering."""
import docx_core
import toolkit as t


def _summary(block, show_values):
    if block is None:
        return None
    result = dict(kind=block['kind'], sha256=t.digest(t.encode(block)), id=block['id'])
    if block['kind'] == 'table':
        result.update(rows=len(block['rows']), columns=len(block['rows'][0]))
    if show_values:
        result['value'] = block['text'] if block['kind'] == 'paragraph' else block['rows']
    return result


def compare(before_raw, after_raw, show_values=False):
    t.require(type(show_values) is bool, 'OPTION_INVALID')
    before, after = docx_core.extract(before_raw), docx_core.extract(after_raw)
    changes = []
    for index in range(max(len(before['blocks']), len(after['blocks']))):
        old = before['blocks'][index] if index < len(before['blocks']) else None
        new = after['blocks'][index] if index < len(after['blocks']) else None
        if old == new:
            continue
        kind = 'ADDED' if old is None else 'REMOVED' if new is None else 'KIND_CHANGED' if old['kind'] != new['kind'] else 'CHANGED'
        change = dict(position=index + 1, classification=kind,
                      before=_summary(old, show_values), after=_summary(new, show_values))
        if old and new and old['kind'] == new['kind'] == 'table':
            cells = []
            for row in range(max(len(old['rows']), len(new['rows']))):
                a = old['rows'][row] if row < len(old['rows']) else []
                b = new['rows'][row] if row < len(new['rows']) else []
                for col in range(max(len(a), len(b))):
                    left = a[col] if col < len(a) else None
                    right = b[col] if col < len(b) else None
                    if left == right:
                        continue
                    record = dict(row=row + 1, column=col + 1,
                        before_sha256=t.digest(t.encode(left)) if left is not None else None,
                        after_sha256=t.digest(t.encode(right)) if right is not None else None)
                    if show_values:
                        record.update(before=left, after=right)
                    cells.append(record)
                    t.require(len(cells) <= 4096, 'CELL_CHANGE_LIMIT')
            change['cell_changes'] = cells
        changes.append(change)
        t.require(len(changes) <= 512, 'BLOCK_CHANGE_LIMIT')
    return dict(format='outlands-document-diff-v1', status='DIFFERENCES' if changes else 'MATCH',
                comparison='SUPPORTED_STORED_CONTENT_BY_POSITION', before_source_sha256=t.digest(before_raw),
                after_source_sha256=t.digest(after_raw), raw_bytes_changed=before_raw != after_raw,
                before_content_sha256=before['content_sha256'], after_content_sha256=after['content_sha256'],
                before_counts=before['counts'], after_counts=after['counts'], changes=changes,
                values_included=show_values, document_properties_compared=False,
                formatting_compared=False, document_executed=False)


def main(argv=None):
    parser = t.Parser(prog='document-content-diff', description=__doc__)
    parser.add_argument('--before', required=True)
    parser.add_argument('--after', required=True)
    parser.add_argument('--show-values', action='store_true')
    parser.add_argument('--out')
    return t.run(parser, lambda a: compare(t.read(a.before), t.read(a.after), a.show_values), argv)


if __name__ == '__main__':
    raise SystemExit(main())
