"""Original MIT desktop monitor adaptation; explicit actions and bounded metadata."""
from __future__ import annotations
from dataclasses import dataclass
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from inspection_support import snapshot, strict_json, local_path, canonical_directory, no_links

MAX_RECORDS = 5000
MAX_HOSTS = 256
MAX_EVENTS = 200
MAX_INPUT = 1024 * 1024


class MonitorError(Exception):
    """Fixed category; do not forward credentials or upstream exception text."""


def require(condition, code):
    if not condition:raise MonitorError(code)


@dataclass(frozen=True)
class Rules:
    ports: tuple = (23, 135, 139, 445, 6667, 6668)
    minimum_bytes: int = 40
    maximum_bytes: int = 2000

    def validate(self):
        require(type(self.ports) is tuple and len(self.ports) <= 64 and
                all(type(p) is int and 1 <= p <= 65535 for p in self.ports) and
                len(set(self.ports)) == len(self.ports), 'RULES_INVALID')
        require(type(self.minimum_bytes) is int and type(self.maximum_bytes) is int and
                0 <= self.minimum_bytes <= self.maximum_bytes <= 65535, 'RULES_INVALID')
        return self


def address(value):
    require(type(value) is str and len(value) <= 45 and '%' not in value, 'ADDRESS_INVALID')
    try:result = ipaddress.ip_address(value)
    except ValueError:raise MonitorError('ADDRESS_INVALID') from None
    require(result.version == 4, 'IPV4_REQUIRED')
    return result


def normalize(row):
    keys = {'source', 'destination', 'protocol', 'source_port', 'destination_port', 'bytes'}
    require(type(row) is dict and set(row) == keys, 'PACKET_RECORD_INVALID')
    result = dict(row, source=str(address(row['source'])), destination=str(address(row['destination'])))
    require(type(row['protocol']) is str and row['protocol'] in ('TCP', 'UDP', 'OTHER'), 'PROTOCOL_INVALID')
    require(type(row['bytes']) is int and 0 <= row['bytes'] <= 65535, 'PACKET_LENGTH_INVALID')
    for key in ('source_port', 'destination_port'):
        value = row[key]
        require((row['protocol'] == 'OTHER' and value is None) or
                (row['protocol'] != 'OTHER' and type(value) is int and 0 <= value <= 65535), 'PORT_INVALID')
    return result


class Model:
    def __init__(self, mode, rules=None):
        require(mode in ('demo', 'replay', 'live'), 'MODE_INVALID')
        self.mode = mode
        self.rules = (rules or Rules()).validate()
        self.lock = threading.Lock()
        self.packets = self.bytes = self.rule_matches = self.invalid = 0
        self.hosts = {}
        self.events = []
        self.host_overflow = 0
        self.event_overflow = 0
        self.system = None

    def observe(self, record):
        row = normalize(record)
        with self.lock:
            require(self.packets < MAX_RECORDS, 'PACKET_LIMIT')
            self.packets += 1
            self.bytes += row['bytes']
            reasons = []
            if row['bytes'] < self.rules.minimum_bytes or row['bytes'] > self.rules.maximum_bytes:
                reasons.append('LENGTH_RULE')
            if row['protocol'] != 'OTHER' and any(row[key] in self.rules.ports for key in ('source_port', 'destination_port')):
                reasons.append('PORT_RULE')
            if reasons:self.rule_matches += 1
            for value in set((row['source'], row['destination'])):
                if value not in self.hosts:
                    if len(self.hosts) >= MAX_HOSTS:
                        self.host_overflow += 1
                        continue
                    self.hosts[value] = {'packets': 0}
                self.hosts[value]['packets'] += 1
            if reasons:
                event = {'packet': self.packets, 'protocol': row['protocol'], 'bytes': row['bytes'],
                         'source': row['source'], 'destination': row['destination'], 'rules': reasons}
                if len(self.events) < MAX_EVENTS:self.events.append(event)
                else:self.event_overflow += 1
        return reasons

    def bad_record(self):
        with self.lock:self.invalid += 1

    def report(self, outcome='completed', include_addresses=False):
        require(outcome in ('completed', 'cancelled', 'failed', 'packet_limit'), 'OUTCOME_INVALID')
        require(type(include_addresses) is bool, 'DETAIL_FLAG_INVALID')
        with self.lock:
            events = [{key: value for key, value in row.items() if include_addresses or key not in ('source', 'destination')}
                      for row in self.events]
            result = {'schema': 'outlands-network-monitor/1', 'mode': self.mode, 'outcome': outcome,
                      'packets_observed': self.packets, 'packet_bytes_observed': self.bytes,
                      'packets_matching_local_rules': self.rule_matches, 'invalid_records': self.invalid,
                      'tracked_unique_hosts': len(self.hosts), 'untracked_host_observations': self.host_overflow,
                      'omitted_rule_events': self.event_overflow, 'events': events,
                      'interpretation': 'Local rule matches are review hints, not a malware verdict.',
                      'addresses_included': include_addresses, 'reputation_requests_automatic': False,
                      'capture_incomplete': outcome == 'failed'}
            if include_addresses:
                result['hosts'] = [{'address': key, **value} for key, value in sorted(self.hosts.items())]
            result['status'] = 'REVIEW_REQUIRED' if self.invalid or self.host_overflow or self.event_overflow or outcome == 'failed' else 'OK'
            return result


def demo():
    model = Model('demo')
    rows = [
        ('192.0.2.10', '198.51.100.20', 'TCP', 50000, 443, 1500),
        ('192.0.2.10', '203.0.113.30', 'TCP', 50001, 23, 60),
        ('203.0.113.30', '192.0.2.10', 'UDP', 53, 50002, 2100),
    ]
    for values in rows:
        model.observe(dict(zip(('source', 'destination', 'protocol', 'source_port', 'destination_port', 'bytes'), values)))
    return model


def load_replay(value):
    try:value = strict_json(snapshot(value, MAX_INPUT), MAX_INPUT, 40000, 1024)
    except Exception:raise MonitorError('REPLAY_INPUT_INVALID') from None
    require(type(value) is dict and set(value) == {'schema', 'packets'} and value['schema'] == 'outlands-packet-metadata/1', 'REPLAY_INVALID')
    require(type(value['packets']) is list and 1 <= len(value['packets']) <= MAX_RECORDS, 'REPLAY_INVALID')
    model = Model('replay')
    for row in value['packets']:model.observe(row)
    return model


def export_report(value, report):
    validate_aggregate_report(report)
    try:
        target = local_path(value);parent = canonical_directory(target.parent);no_links(parent)
    except Exception:raise MonitorError('OUTPUT_PATH_INVALID') from None
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_. -]{0,114}\.json', target.name, re.I) and
            not re.fullmatch(r'CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]', target.name.split('.')[0].rstrip(' '), re.I), 'OUTPUT_NAME_INVALID')
    target = parent / target.name
    require(not target.exists() and not target.is_symlink(), 'OUTPUT_EXISTS_OR_PARENT_INVALID')
    data = (json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False)+'\n').encode()
    require(len(data) <= MAX_INPUT, 'REPORT_LIMIT')
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(descriptor, 'wb') as stream:stream.write(data)


def validate_aggregate_report(report):
    fields = {'schema','mode','outcome','packets_observed','packet_bytes_observed',
              'packets_matching_local_rules','invalid_records','tracked_unique_hosts',
              'untracked_host_observations','omitted_rule_events','events','interpretation',
              'addresses_included','reputation_requests_automatic','capture_incomplete','status'}
    require(type(report) is dict and set(report) == fields, 'REPORT_INVALID')
    require(report['schema'] == 'outlands-network-monitor/1' and report['mode'] in ('demo','replay','live')
            and report['outcome'] in ('completed','cancelled','failed','packet_limit'), 'REPORT_INVALID')
    require(report['addresses_included'] is False and report['reputation_requests_automatic'] is False,
            'AGGREGATE_REPORT_REQUIRED')
    require(type(report['capture_incomplete']) is bool, 'REPORT_INVALID')
    for key in ('packets_observed','packet_bytes_observed','packets_matching_local_rules','invalid_records',
                'tracked_unique_hosts','untracked_host_observations','omitted_rule_events'):
        require(type(report[key]) is int and 0 <= report[key] <= MAX_RECORDS * 65535, 'REPORT_INVALID')
    require(report['packets_observed'] <= MAX_RECORDS and report['tracked_unique_hosts'] <= MAX_HOSTS
            and report['packets_matching_local_rules'] <= report['packets_observed'], 'REPORT_INVALID')
    require(type(report['events']) is list and len(report['events']) <= MAX_EVENTS, 'REPORT_INVALID')
    last = 0
    for row in report['events']:
        require(type(row) is dict and set(row) == {'packet','protocol','bytes','rules'}, 'REPORT_INVALID')
        require(type(row['packet']) is int and last < row['packet'] <= report['packets_observed'], 'REPORT_INVALID')
        require(row['protocol'] in ('TCP','UDP','OTHER') and type(row['bytes']) is int and 0 <= row['bytes'] <= 65535, 'REPORT_INVALID')
        require(type(row['rules']) is list and 1 <= len(row['rules']) <= 2
                and all(type(v) is str and v in ('PORT_RULE','LENGTH_RULE') for v in row['rules'])
                and len(set(row['rules'])) == len(row['rules']), 'REPORT_INVALID')
        last = row['packet']
    require(len(report['events']) + report['omitted_rule_events'] == report['packets_matching_local_rules'], 'REPORT_INVALID')
    require(report['interpretation'] == 'Local rule matches are review hints, not a malware verdict.', 'REPORT_INVALID')
    expected = 'REVIEW_REQUIRED' if report['invalid_records'] or report['untracked_host_observations'] or report['omitted_rule_events'] or report['outcome'] == 'failed' or report['capture_incomplete'] else 'OK'
    require(report['status'] == expected, 'REPORT_INVALID')
    return report


def pulse_observation(data):
    """A pulse-count observation is never converted to a clean/malicious verdict."""
    require(type(data) is bytes and len(data) <= 262144, 'OTX_RESPONSE_LIMIT')
    def pairs(rows):
        out = {}
        for key, value in rows:
            require(key not in out, 'OTX_RESPONSE_INVALID');out[key] = value
        return out
    def invalid(_):raise MonitorError('OTX_RESPONSE_INVALID')
    try:value = json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, UnicodeError, RecursionError):raise MonitorError('OTX_RESPONSE_INVALID') from None
    require(type(value) is dict and type(value.get('pulse_info')) is dict, 'OTX_RESPONSE_INVALID')
    count = value['pulse_info'].get('count')
    require(type(count) is int and 0 <= count <= 10000000, 'OTX_RESPONSE_INVALID')
    return {'status': 'OBSERVATION', 'reported_pulse_count': count,
            'interpretation': 'Pulse membership is a reputation observation, not a malware verdict.'}


def lookup_otx(value, allow_online=False, request=None, key=None):
    require(allow_online is True, 'ONLINE_LOOKUP_NOT_AUTHORIZED')
    ip = address(value)
    require(ip.is_global and not ip.is_multicast, 'PUBLIC_UNICAST_IPV4_REQUIRED')
    key = os.environ.get('OTX_API_KEY', '') if key is None else key
    require(type(key) is str and re.fullmatch(r'[A-Za-z0-9_-]{16,256}', key), 'OTX_KEY_MISSING_OR_INVALID')
    session = None
    if request is None:
        try:from requests import Session
        except ImportError:raise MonitorError('REQUESTS_UNAVAILABLE') from None
        session = Session()
        session.trust_env = False  # Do not discover/send .netrc credentials or use environment proxies.
        request = session.get
    try:
        with request('https://otx.alienvault.com/api/v1/indicators/IPv4/'+str(ip)+'/general',
                     headers={'X-OTX-API-KEY': key}, timeout=(3, 5), allow_redirects=False, stream=True) as response:
            require(response.status_code == 200, 'OTX_HTTP_ERROR')
            chunks = []
            total = 0
            for block in response.iter_content(8192):
                total += len(block);require(total <= 262144, 'OTX_RESPONSE_LIMIT');chunks.append(block)
            return pulse_observation(b''.join(chunks))
    except MonitorError:raise
    except Exception:raise MonitorError('OTX_LOOKUP_FAILED') from None
    finally:
        if session is not None:session.close()


def packet_record(packet, IP, TCP, UDP):
    if not packet.haslayer(IP):return None
    layer = packet[IP]
    # Only the immediate IPv4 transport counts. An ICMP quotation or nested IP
    # packet must not lend its TCP/UDP ports to the outer endpoint addresses.
    payload = layer.payload
    unfragmented_start = int(layer.frag) == 0
    protocol = 'TCP' if unfragmented_start and int(layer.proto) == 6 and isinstance(payload, TCP) else 'UDP' if unfragmented_start and int(layer.proto) == 17 and isinstance(payload, UDP) else 'OTHER'
    transport = payload if protocol != 'OTHER' else None
    return normalize({'source': str(layer.src), 'destination': str(layer.dst), 'protocol': protocol,
                      'source_port': int(transport.sport) if transport else None,
                      'destination_port': int(transport.dport) if transport else None,
                      'bytes': len(packet)})


def capture(model, interface, seconds, stop, on_update=None, backend=None, clock=time.monotonic):
    require(type(interface) is str and 1 <= len(interface) <= 256 and not any(ord(c) < 32 for c in interface), 'INTERFACE_INVALID')
    require(type(seconds) in (int, float) and math.isfinite(seconds) and 1 <= seconds <= 600, 'DURATION_INVALID')
    if backend is None:
        try:
            from scapy.sendrecv import sniff
            from scapy.layers.inet import IP, TCP, UDP
        except ImportError:raise MonitorError('SCAPY_UNAVAILABLE') from None
    else:sniff, IP, TCP, UDP = backend
    outcome = 'completed'
    deadline = clock()+seconds
    def observed(packet):
        if stop.is_set() or model.packets >= MAX_RECORDS:return
        try:
            row = packet_record(packet, IP, TCP, UDP)
            if row is not None:model.observe(row)
        except MonitorError:model.bad_record()
    try:
        while not stop.is_set() and clock() < deadline and model.packets < MAX_RECORDS:
            sniff(iface=interface, filter='ip', prn=observed, store=False,
                  timeout=min(.5, max(.01, deadline-clock())), count=MAX_RECORDS-model.packets)
            if on_update:on_update(model.report())
        if stop.is_set():outcome = 'cancelled'
        elif model.packets >= MAX_RECORDS:outcome = 'packet_limit'
    except Exception:outcome = 'failed'
    return model.report(outcome)
