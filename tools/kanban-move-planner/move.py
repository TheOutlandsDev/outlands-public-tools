"""Preview one pinned board move without changing any work item."""
import copy
import board_core as c
import toolkit as t

FORMAT = 'outlands-kanban-move-v1'


def check(raw):
    value = t.decode(raw)
    t.fields(value, {'format', 'board', 'board_sha256', 'move'})
    t.require(value['format'] == FORMAT, 'FORMAT_INVALID')
    t.sha(value['board_sha256'])
    board, pin, counts, findings = c.assess(value['board'])
    t.require(pin == value['board_sha256'], 'BOARD_PIN_INVALID')
    t.fields(value['move'], {'card', 'target_column', 'target_position'})
    move = value['move']
    t.identifier(move['card']); t.identifier(move['target_column'])
    t.integer(move['target_position'], 512)
    cards = {x['id']: x for x in board['cards']}
    columns = {x['id']: x for x in board['columns']}
    t.require(move['card'] in cards, 'CARD_UNKNOWN')
    t.require(move['target_column'] in columns, 'COLUMN_UNKNOWN')
    card = cards[move['card']]
    source = card['column']
    target = move['target_column']
    target_cohort = [x for x in board['cards'] if x['column'] == target and x['id'] != card['id']]
    t.require(move['target_position'] <= len(target_cohort), 'TARGET_POSITION_INVALID')
    issues = [{'code': 'BASELINE_BOARD_REVIEW_REQUIRED'}] if findings else []
    if card['blocked']:
        issues.append({'code': 'CARD_BLOCKED'})
    if source != target and target not in columns[source]['allowed_next']:
        issues.append({'code': 'TRANSITION_NOT_ALLOWED'})
    limit = columns[target]['wip_limit']
    if source != target and limit is not None and len(target_cohort) + 1 > limit:
        issues.append({'code': 'TARGET_WIP_LIMIT_EXCEEDED'})
    if issues:
        return {'format': FORMAT, 'status': 'REVIEW_REQUIRED',
                'input_sha256': t.digest(raw), 'baseline_board_sha256': pin,
                'baseline_findings': findings, 'issues': issues, 'candidate_board_sha256': None,
                'candidate_column_counts': None, 'target_changes_performed': False}
    proposed = copy.deepcopy(board)
    source_cards = sorted((x for x in proposed['cards'] if x['column'] == source and x['id'] != card['id']),
                          key=lambda x: x['position'])
    target_cards = (source_cards if source == target else
                    sorted((x for x in proposed['cards'] if x['column'] == target),
                           key=lambda x: x['position']))
    selected = next(x for x in proposed['cards'] if x['id'] == card['id'])
    target_cards.insert(move['target_position'], selected)
    for index, row in enumerate(target_cards):
        row['column'] = target
        row['position'] = index
    if source != target:
        for index, row in enumerate(source_cards):
            row['position'] = index
    proposed['revision'] += 1
    _, candidate_pin, candidate_counts, candidate_findings = c.assess(proposed)
    t.require(not candidate_findings, 'CANDIDATE_BOARD_INVALID')
    return {'format': FORMAT, 'status': 'PASS', 'input_sha256': t.digest(raw),
            'baseline_board_sha256': pin, 'baseline_column_counts': counts,
            'candidate_board_sha256': candidate_pin,
            'candidate_column_counts': candidate_counts, 'issues': [],
            'target_changes_performed': False}


def main(argv=None):
    parser = t.Parser(description=__doc__)
    parser.add_argument('--input', required=True); parser.add_argument('--out')
    return t.run(parser, lambda args: check(t.read(args.input)), argv)


if __name__ == '__main__': raise SystemExit(main())
