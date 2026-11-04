"""Exact, bounded category contribution ranking over caller-supplied rows."""
from fractions import Fraction
import re
import toolkit as t


def decimal(value, maximum=10**12):
    t.require(type(value) is str and re.fullmatch(r'(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,6})?', value), 'DECIMAL_INVALID')
    number = Fraction(value)
    t.require(0 <= number <= maximum, 'DECIMAL_RANGE')
    return number


def render(number):
    scaled = number * 10**6
    t.require(scaled.denominator == 1, 'DECIMAL_RENDER_INVALID')
    whole, part = divmod(scaled.numerator, 10**6)
    return str(whole) + ('.' + str(part).zfill(6).rstrip('0') if part else '')


def ratio(value):
    return str(value.numerator) + '/' + str(value.denominator)


def snapshot(value):
    t.fields(value, {'id', 'revision', 'rows'})
    t.identifier(value['id']); t.integer(value['revision'], 10**6, 1)
    t.require(type(value['rows']) is list and 1 <= len(value['rows']) <= 512, 'ROW_LIMIT')
    seen, totals = set(), {}
    for row in value['rows']:
        t.fields(row, {'id', 'category', 'amount'})
        t.identifier(row['id']); t.identifier(row['category'])
        t.require(row['id'] not in seen, 'ROW_DUPLICATE'); seen.add(row['id'])
        totals[row['category']] = totals.get(row['category'], Fraction(0)) + decimal(row['amount'])
    t.require(len(totals) <= 64, 'CATEGORY_LIMIT')
    normalized = dict(value, rows=sorted(value['rows'], key=lambda row: row['id']))
    return normalized, totals


def analyze(value):
    normalized, totals = snapshot(value)
    total = sum(totals.values(), Fraction(0))
    groups = {}
    for category, amount in totals.items():
        groups.setdefault(amount, []).append(category)
    blocks, cumulative, rank = [], Fraction(0), 1
    for amount in sorted(groups, reverse=True):
        categories = sorted(groups[amount])
        block_total = amount * len(categories)
        cumulative += block_total
        blocks.append({
            'rank': rank,
            'categories': categories,
            'each_amount': render(amount),
            'block_total': render(block_total),
            'cumulative_share': ratio(cumulative / total) if total else None,
        })
        rank += len(categories)
    t.require(cumulative == total, 'ACCOUNTING_FAILED')
    ranking = {'snapshot_sha256': t.digest(t.encode(normalized)), 'total': render(total), 'blocks': blocks}
    return ranking, t.digest(t.encode(ranking)), len(value['rows'])
