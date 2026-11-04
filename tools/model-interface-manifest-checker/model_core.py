"""Bounded offline model port-interface declarations and exact pins."""
import toolkit as t

DTYPES = {'float32', 'float64', 'int64', 'boolean'}


def symbol(row):
    t.fields(row, {'id', 'minimum', 'maximum'})
    t.identifier(row['id'])
    t.integer(row['minimum'], 10**9, 1)
    t.integer(row['maximum'], 10**9, 1)
    t.require(row['minimum'] <= row['maximum'], 'SYMBOL_RANGE_INVALID')
    return row


def port(row, symbols):
    t.fields(row, {'id', 'dtype', 'shape', 'required'})
    t.identifier(row['id'])
    t.require(type(row['dtype']) is str and row['dtype'] in DTYPES, 'DTYPE_INVALID')
    t.require(type(row['required']) is bool, 'REQUIRED_INVALID')
    t.require(type(row['shape']) is list and 1 <= len(row['shape']) <= 8, 'SHAPE_INVALID')
    for dimension in row['shape']:
        if type(dimension) is int:
            t.integer(dimension, 10**9, 1)
        else:
            t.identifier(dimension)
            t.require(dimension in symbols, 'SYMBOL_UNKNOWN')
    return row


def manifest(row):
    t.fields(row, {'id', 'revision', 'artifact_sha256', 'preprocessing_sha256', 'symbols', 'inputs', 'outputs'})
    t.identifier(row['id']); t.integer(row['revision'], 10**6, 1)
    t.sha(row['artifact_sha256']); t.sha(row['preprocessing_sha256'])
    t.require(type(row['symbols']) is list and len(row['symbols']) <= 16, 'SYMBOL_LIMIT')
    symbols = {}
    for item in row['symbols']:
        symbol(item)
        t.require(item['id'] not in symbols, 'SYMBOL_DUPLICATE')
        symbols[item['id']] = item
    ports = {}
    for side in ('inputs', 'outputs'):
        entries = row[side]
        t.require(type(entries) is list and 1 <= len(entries) <= 32, 'PORT_LIMIT')
        selected = {}
        for item in entries:
            port(item, symbols)
            t.require(item['id'] not in selected, 'PORT_DUPLICATE')
            selected[item['id']] = item
        ports[side] = selected
    used = {dimension for side in ports.values() for item in side.values() for dimension in item['shape'] if type(dimension) is str}
    t.require(used == set(symbols), 'SYMBOL_UNUSED')
    normalized = dict(row, symbols=[symbols[key] for key in sorted(symbols)], inputs=[ports['inputs'][key] for key in sorted(ports['inputs'])], outputs=[ports['outputs'][key] for key in sorted(ports['outputs'])])
    return normalized, ports, symbols, t.digest(t.encode(normalized))


def port_signature(item, symbols):
    shape = [dimension if type(dimension) is int else {'symbol':dimension, 'minimum':symbols[dimension]['minimum'], 'maximum':symbols[dimension]['maximum']} for dimension in item['shape']]
    return {'dtype':item['dtype'], 'shape':shape}
