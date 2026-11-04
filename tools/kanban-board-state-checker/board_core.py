"""Validate a bounded declared board and deterministic column positions."""
import toolkit as t


def assess(board):
    t.fields(board, {'id', 'revision', 'columns', 'cards'})
    t.identifier(board['id']); t.integer(board['revision'], 10**6, 1)
    columns, cards = board['columns'], board['cards']
    t.require(type(columns) is list and 1 <= len(columns) <= 32, 'COLUMN_LIMIT')
    t.require(type(cards) is list and len(cards) <= 512, 'CARD_LIMIT')
    column_map = {}
    for row in columns:
        t.fields(row, {'id', 'wip_limit', 'allowed_next'})
        t.identifier(row['id'])
        t.require(row['id'] not in column_map, 'COLUMN_DUPLICATE')
        if row['wip_limit'] is not None:
            t.integer(row['wip_limit'], 512)
        t.require(type(row['allowed_next']) is list and len(row['allowed_next']) <= 32,
                  'TRANSITION_LIMIT')
        t.require(all(type(x) is str for x in row['allowed_next']), 'TRANSITION_INVALID')
        for target in row['allowed_next']:
            t.identifier(target)
        t.require(len(set(row['allowed_next'])) == len(row['allowed_next']),
                  'TRANSITION_DUPLICATE')
        column_map[row['id']] = row
    for row in columns:
        t.require(all(x in column_map and x != row['id'] for x in row['allowed_next']),
                  'TRANSITION_INVALID')
    card_ids = set()
    by_column = {name: [] for name in column_map}
    for row in cards:
        t.fields(row, {'id', 'column', 'position', 'blocked'})
        t.identifier(row['id'])
        t.require(row['id'] not in card_ids, 'CARD_DUPLICATE')
        card_ids.add(row['id'])
        t.identifier(row['column'])
        t.require(row['column'] in column_map, 'CARD_COLUMN_UNKNOWN')
        t.integer(row['position'], 511)
        t.require(type(row['blocked']) is bool, 'CARD_BLOCKED_INVALID')
        by_column[row['column']].append(row)
    findings, counts = [], []
    for name in sorted(column_map):
        cohort = by_column[name]
        positions = sorted(x['position'] for x in cohort)
        if len(positions) != len(set(positions)):
            findings.append({'column': name, 'code': 'POSITION_DUPLICATE'})
        if positions != list(range(len(cohort))):
            findings.append({'column': name, 'code': 'POSITION_GAP_OR_RANGE'})
        limit = column_map[name]['wip_limit']
        if limit is not None and len(cohort) > limit:
            findings.append({'column': name, 'code': 'WIP_LIMIT_EXCEEDED'})
        counts.append({'column': name, 'cards': len(cohort),
                       'blocked_cards': sum(x['blocked'] for x in cohort),
                       'wip_limit': limit})
    normalized = dict(board,
                      columns=[dict(x, allowed_next=sorted(x['allowed_next']))
                               for x in sorted(columns, key=lambda x: x['id'])],
                      cards=sorted(cards, key=lambda x: x['id']))
    return normalized, t.digest(t.encode(normalized)), counts, findings
