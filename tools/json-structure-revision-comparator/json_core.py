"""Bounded, value-free shape summary for one supplied JSON document."""
from collections import defaultdict
from decimal import Decimal
import json

import toolkit as t


def _pairs(items):
    result = {}
    for key, value in items:
        t.require(key not in result, 'JSON_DUPLICATE_KEY')
        result[key] = value
    return result


def _constant(_value):
    raise t.Rejected('JSON_NONFINITE_NUMBER')


def profile(text):
    t.require(type(text) is str, 'JSON_TEXT_INVALID')
    try:
        raw = text.encode('utf-8')
    except UnicodeError:
        raise t.Rejected('JSON_TEXT_INVALID') from None
    t.require(len(raw) <= 4096, 'JSON_TEXT_LIMIT')
    try:
        document = json.loads(text, object_pairs_hook=_pairs,
                              parse_float=Decimal, parse_constant=_constant)
    except t.Rejected:
        raise
    except (ValueError, RecursionError):
        raise t.Rejected('JSON_INVALID') from None
    counts = defaultdict(lambda: defaultdict(int))
    pending = [(document, (), 0)]
    nodes = 0
    while pending:
        value, path, depth = pending.pop()
        nodes += 1
        t.require(nodes <= 512 and depth <= 12, 'JSON_STRUCTURE_LIMIT')
        if type(value) is dict:
            kind = 'object'
            for key, child in value.items():
                t.require(type(key) is str and len(key) <= 64, 'JSON_KEY_LIMIT')
                pending.append((child, path + ('key:' + key,), depth + 1))
        elif type(value) is list:
            kind = 'array'
            pending.extend((child, path + ('item:*',), depth + 1) for child in value)
        elif type(value) is str:
            kind = 'string'
            t.require(len(value) <= 4096, 'JSON_VALUE_LIMIT')
        elif type(value) is bool:
            kind = 'boolean'
        elif type(value) is int:
            kind = 'integer'
        elif type(value) is Decimal:
            kind = 'number'
        elif value is None:
            kind = 'null'
        else:
            raise t.Rejected('JSON_VALUE_INVALID')
        counts[path][kind] += 1
        t.require(len(counts) <= 256, 'JSON_PATH_LIMIT')
    shape = {'node_count': nodes, 'path_count': len(counts),
             'paths': [{'path': list(path), 'occurrences': sum(kinds.values()),
                        'types': dict(sorted(kinds.items()))}
                       for path, kinds in sorted(counts.items())]}
    return shape, t.digest(t.encode(shape)), t.digest(raw)
