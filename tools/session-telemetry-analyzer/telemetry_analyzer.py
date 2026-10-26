"""Summarize selected saved JSONL telemetry observations; never query a live game. MIT."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import json
import re
import unicodedata
from inspection_support import (Parser, TextError, bounded_append, cli_error,
                                finish, require, source_inputs, source_record,
                                text_lines, write_report)

MAX_RECORDS = 4000
MAX_NODES = 1000
MAX_LOS = 256
MAX_POPULATION = 1000000000
MAX_DROPPED = 1000000000000
MAX_SECONDS = 315360000
TYPES = ('raid_start', 'snapshot', 'tracking_assigned', 'raid_end')
COMMON_KEYS = {'map', 'raid_seconds'}
MALFORMED_CODES = {'INVALID_JSON', 'DUPLICATE_JSON_KEY', 'JSON_NONFINITE_UNSUPPORTED',
                   'JSON_TEXT_UNSUPPORTED'}


def parse_record(text):
    """Decode one bounded record with exact numbers and no duplicate-name winner."""
    def pairs(values):
        out = {}
        for key, value in values:
            require(key not in out, 'DUPLICATE_JSON_KEY'); out[key] = value
        return out
    def number(token):
        require(len(token) <= 64, 'JSON_NUMBER_LIMIT')
        exponent = re.search(r'[eE]([+-]?[0-9]+)$', token)
        require(not exponent or abs(int(exponent[1])) <= 1000, 'JSON_NUMBER_LIMIT')
        try: value = Decimal(token)
        except InvalidOperation: raise TextError('INVALID_JSON') from None
        require(value.is_finite(), 'JSON_NONFINITE_UNSUPPORTED')
        return value
    def integer(token):
        require(len(token) <= 24, 'JSON_NUMBER_LIMIT'); return int(token)
    def constant(_token): raise TextError('JSON_NONFINITE_UNSUPPORTED')
    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_float=number,
                           parse_int=integer, parse_constant=constant)
    except (ValueError, InvalidOperation): raise TextError('INVALID_JSON') from None
    except RecursionError: raise TextError('JSON_STRUCTURE_LIMIT') from None
    pending = [(value, 0)]; visited = 0
    while pending:
        item, depth = pending.pop(); visited += 1
        require(depth <= 8 and visited <= MAX_NODES, 'JSON_STRUCTURE_LIMIT')
        if type(item) is dict:
            for key, child in item.items():
                require(len(key) <= 256, 'JSON_STRING_LIMIT')
                require(not any(unicodedata.category(c).startswith('C') or c in '\u2028\u2029' for c in key), 'JSON_TEXT_UNSUPPORTED')
                pending.append((child, depth + 1))
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            require(len(item) <= 1024, 'JSON_STRING_LIMIT')
            require(not any(unicodedata.category(c).startswith('C') or c in '\u2028\u2029' for c in item), 'JSON_TEXT_UNSUPPORTED')
    return value


def metric():
    return {'samples': 0, 'missing_samples': 0, 'invalid_samples': 0,
            'sum': 0, 'maximum': None}


def summarize(inputs):
    """Each selected file is a separate observation set, never a proven session."""
    require(type(inputs) is list and 1 <= len(inputs) <= 32, 'INPUT_COUNT_LIMIT')
    report = {'schema_version': 1, 'tool': 'Offline Session Telemetry Analyzer',
              'scope': 'Selected saved JSONL subset; per-file observations, not distinct-session or runtime evidence.',
              'sources': [], 'captures': [], 'findings': [], 'coverage_issues': []}
    observed = 0
    def issue(code, source, line, field=None, finding=False):
        row = {'code': code, 'source': source, 'line': line}
        if field is not None: row['field'] = field
        bounded_append(report['findings' if finding else 'coverage_issues'], row)
    for source, data in inputs:
        bounded_append(report['sources'], source_record(source, data))
        lines = text_lines(data)
        # A terminator does not introduce an additional JSON value.
        if not data or data == b'\xef\xbb\xbf': lines = []
        elif lines and lines[-1][1] == '' and data.endswith(b'\n'): lines.pop()
        capture = {'source': source, 'physical_lines': len(lines), 'blank_rows': 0,
                   'nonblank_rows': 0, 'decoded_rows': 0, 'accepted_events': 0,
                   'malformed_json_rows': 0, 'invalid_envelope_rows': 0,
                   'unsupported_event_rows': 0,
                   'event_counts': {name: 0 for name in TYPES},
                   'populations': {'players': metric(), 'bots': metric(), 'tracked_active': metric()},
                   'line_of_sight': {'present_collections': 0, 'missing_collections': 0,
                       'invalid_collections': 0, 'declared_entries': 0, 'valid_boolean_samples': 0,
                       'visible_samples': 0, 'missing_entry_values': 0, 'invalid_entry_values': 0},
                   'declared_time': {'valid_declarations': 0, 'invalid_declarations': 0,
                                     'last_in_file_seconds': None},
                   'dropped_data': {'end_rows': 0, 'valid_declarations': 0,
                                    'invalid_declarations': 0, 'state': 'unspecified',
                                    'declared_dropped_lines': None}}
        last_seconds = None; declared_drops = None
        if data.startswith(b'\xef\xbb\xbf'): issue('UTF8_BOM_EXTENSION', source, 1)
        def population(name, container, key, line, invalid_container=False):
            row = capture['populations'][name]
            if invalid_container:
                row['invalid_samples'] += 1
                issue('POPULATION_CONTAINER_INVALID', source, line, name); return
            if key not in container:
                row['missing_samples'] += 1; return
            value = container[key]
            if type(value) is not int or not 0 <= value <= MAX_POPULATION:
                row['invalid_samples'] += 1
                issue('POPULATION_VALUE_INVALID', source, line, name); return
            row['samples'] += 1; row['sum'] += value
            row['maximum'] = value if row['maximum'] is None else max(row['maximum'], value)
        for line, raw in lines:
            if not raw.strip(' \t'):
                capture['blank_rows'] += 1; issue('BLANK_RECORD_LINE', source, line); continue
            observed += 1; require(observed <= MAX_RECORDS, 'TELEMETRY_RECORD_LIMIT')
            capture['nonblank_rows'] += 1
            try: event = parse_record(raw)
            except TextError as error:
                if str(error) not in MALFORMED_CODES: raise
                capture['malformed_json_rows'] += 1; issue(str(error), source, line); continue
            capture['decoded_rows'] += 1
            if type(event) is not dict or type(event.get('type')) is not str or not event.get('type'):
                capture['invalid_envelope_rows'] += 1; issue('EVENT_ENVELOPE_INVALID', source, line); continue
            kind = event['type']
            if kind not in TYPES:
                capture['unsupported_event_rows'] += 1; issue('EVENT_TYPE_UNSUPPORTED', source, line); continue
            payload = event.get('payload')
            if type(payload) is not dict:
                capture['invalid_envelope_rows'] += 1; issue('PAYLOAD_OBJECT_REQUIRED', source, line); continue
            capture['accepted_events'] += 1; capture['event_counts'][kind] += 1
            if event.keys()-{'type','payload'}: issue('ENVELOPE_FIELDS_UNSUPPORTED', source, line)
            allowed = COMMON_KEYS | ({'player_count','bot_count','tracking','line_of_sight'} if kind == 'snapshot' else {'dropped_lines'} if kind == 'raid_end' else set())
            if payload.keys()-allowed: issue('PAYLOAD_FIELDS_UNSUPPORTED', source, line)
            if 'raid_seconds' in payload:
                value = payload['raid_seconds']
                if type(value) not in (int, Decimal) or not 0 <= value <= MAX_SECONDS:
                    capture['declared_time']['invalid_declarations'] += 1
                    issue('DECLARED_SECONDS_INVALID', source, line)
                else:
                    seconds = Decimal(value)
                    capture['declared_time']['valid_declarations'] += 1
                    capture['declared_time']['last_in_file_seconds'] = str(seconds)
                    if last_seconds is not None and seconds < last_seconds:
                        issue('DECLARED_TIME_DECREASE', source, line, finding=True)
                    last_seconds = seconds
            if kind == 'snapshot':
                population('players', payload, 'player_count', line)
                population('bots', payload, 'bot_count', line)
                tracking = payload.get('tracking', {})
                population('tracked_active', tracking, 'active_count', line, type(tracking) is not dict)
                if type(tracking) is dict and tracking.keys()-{'active_count'}:
                    issue('TRACKING_FIELDS_UNSUPPORTED', source, line)
                los = capture['line_of_sight']
                if 'line_of_sight' not in payload: los['missing_collections'] += 1
                elif type(payload['line_of_sight']) is not list:
                    los['invalid_collections'] += 1; issue('LOS_COLLECTION_INVALID', source, line)
                else:
                    entries = payload['line_of_sight']; require(len(entries) <= MAX_LOS, 'LOS_ENTRY_LIMIT')
                    los['present_collections'] += 1; los['declared_entries'] += len(entries)
                    for entry in entries:
                        if type(entry) is not dict:
                            los['invalid_entry_values'] += 1; issue('LOS_ENTRY_INVALID', source, line); continue
                        if entry.keys()-{'main_can_see_bot'}: issue('LOS_FIELDS_UNSUPPORTED', source, line)
                        if 'main_can_see_bot' not in entry: los['missing_entry_values'] += 1
                        elif type(entry['main_can_see_bot']) is not bool:
                            los['invalid_entry_values'] += 1; issue('LOS_VALUE_INVALID', source, line)
                        else:
                            los['valid_boolean_samples'] += 1
                            los['visible_samples'] += int(entry['main_can_see_bot'])
            if kind == 'raid_end':
                dropped = capture['dropped_data']; dropped['end_rows'] += 1
                if 'dropped_lines' in payload:
                    value = payload['dropped_lines']
                    if type(value) is not int or not 0 <= value <= MAX_DROPPED:
                        dropped['invalid_declarations'] += 1; issue('DROPPED_LINES_INVALID', source, line)
                    else:
                        dropped['valid_declarations'] += 1; declared_drops = value
        if not capture['accepted_events']: issue('NO_SUPPORTED_EVENTS', source, 0)
        if capture['event_counts']['raid_start'] > 1: issue('MULTIPLE_START_MARKERS', source, 0)
        dropped = capture['dropped_data']
        if dropped['end_rows'] > 1:
            dropped['state'] = 'ambiguous_multiple_end_rows'; issue('MULTIPLE_END_MARKERS', source, 0)
        elif dropped['valid_declarations'] == 1:
            dropped['state'] = 'declared'; dropped['declared_dropped_lines'] = str(declared_drops)
            if declared_drops: issue('DECLARED_DROPPED_LINES', source, 0, finding=True)
        elif dropped['invalid_declarations']: dropped['state'] = 'invalid'
        for row in capture['populations'].values():
            row['sample_mean'] = {'numerator': str(row['sum']), 'denominator': row['samples']} if row['samples'] else None
            row['sum'] = str(row['sum'])
        los = capture['line_of_sight']
        los['visible_fraction'] = {'numerator': str(los['visible_samples']), 'denominator': los['valid_boolean_samples']} if los['valid_boolean_samples'] else None
        bounded_append(report['captures'], capture)
    report['selected_files'] = len(inputs); report['nonblank_records_observed'] = observed
    return finish(report)


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--file', action='append', required=True)
    parser.add_argument('--output', required=True)
    try:
        args = parser.parse_args(argv)
        report = summarize(source_inputs(args.file))
        write_report(report, args.output, args.file)
        print(json.dumps({'status': report['status'], 'selected_files': report['selected_files'],
                          'nonblank_records_observed': report['nonblank_records_observed'],
                          'findings': len(report['findings']), 'coverage_issues': len(report['coverage_issues'])}, sort_keys=True))
        return int(report['status'] != 'NO_SCOPE_FINDINGS')
    except (TextError, OSError, ValueError, RecursionError) as error: return cli_error(error)


if __name__ == '__main__': raise SystemExit(main())
