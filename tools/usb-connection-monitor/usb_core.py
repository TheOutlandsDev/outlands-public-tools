"""Original MIT sampled-presence model. No device identifiers in session reports."""
from __future__ import annotations
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import threading
import time
from inspection_support import TextError, canonical_directory, local_path, no_links, snapshot, strict_json

MAX_SAMPLES = 7201
MAX_ELAPSED_MS = 3_620_000
MAX_REPORT = 2 * 1024 * 1024
CODES = {'QUERY_FAILED', 'QUERY_TIMEOUT', 'QUERY_OUTPUT_LIMIT', 'QUERY_INVALID',
         'WINDOWS_REQUIRED', 'POWERSHELL_UNAVAILABLE', 'CANCELLED'}


def require(condition, code):
    if not condition:
        raise TextError(code)


@dataclass(frozen=True)
class Settings:
    seconds: float = 60
    interval: float = 2

    def validate(self):
        for value, low, high in [(self.seconds, 1, 3600), (self.interval, .5, 60)]:
            require(type(value) in (int, float) and math.isfinite(value) and low <= value <= high,
                    'SETTINGS_INVALID')
        return self


class Session:
    def __init__(self, mode, settings=None):
        require(type(mode) is str and mode in ('demo', 'replay', 'live'), 'MODE_INVALID')
        self.settings = (settings or Settings()).validate()
        self.mode = mode
        self.samples = []
        self.events = []
        self.previous = 'unset'
        self.counts = {'present': 0, 'absent': 0, 'unknown': 0}

    def observe(self, elapsed_ms, present, code=None):
        require(type(elapsed_ms) is int and 0 <= elapsed_ms <= MAX_ELAPSED_MS, 'ELAPSED_INVALID')
        require(not self.samples or elapsed_ms >= self.samples[-1]['elapsed_ms'], 'TIME_ORDER_INVALID')
        require(present is None or type(present) is bool, 'PRESENCE_INVALID')
        require((present is None and type(code) is str and code in CODES)
                or (present is not None and code is None), 'OBSERVATION_CODE_INVALID')
        require(len(self.samples) < MAX_SAMPLES, 'SAMPLE_LIMIT')
        state = 'unknown' if present is None else 'present' if present else 'absent'
        row = {'elapsed_ms': elapsed_ms, 'state': state, 'code': code}
        self.samples.append(row)
        self.counts[state] += 1
        if state != self.previous:
            if state == 'unknown':
                kind = 'observation_unavailable'
            elif self.previous == 'unset':
                kind = 'initial_' + state
            elif self.previous == 'unknown':
                kind = 'observation_resumed_' + state
            else:
                kind = 'disconnected_observed' if state == 'absent' else 'reconnected_observed'
            self.events.append({'elapsed_ms': elapsed_ms, 'kind': kind})
        self.previous = state

    def report(self, outcome='completed'):
        require(outcome in ('completed', 'cancelled', 'failed'), 'OUTCOME_INVALID')
        review = outcome == 'failed' or not self.samples or self.counts['unknown'] > 0
        return {'schema': 'outlands-usb-presence/1', 'mode': self.mode,
                'status': 'REVIEW_REQUIRED' if review else 'OK', 'outcome': outcome,
                'requested_seconds': self.settings.seconds, 'interval_seconds': self.settings.interval,
                'selected_device': 'selected-device', 'sample_counts': dict(self.counts),
                'samples': [dict(row) for row in self.samples],
                'events': [dict(row) for row in self.events],
                'scope': 'Sampled Windows PnP presence; missed transitions and physical causes are unknown.',
                'privacy': {'instance_ids': False, 'device_names': False, 'wall_clock': False,
                            'machine_identity': False, 'raw_native_output': False}}


DEMOS = {
    'stable': [True, True, True, True],
    'reconnect': [True, True, False, False, True, True],
    'query-gap': [True, None, False, False, True],
}


def demo(name='reconnect'):
    require(type(name) is str and name in DEMOS, 'DEMO_INVALID')
    session = Session('demo', Settings(seconds=len(DEMOS[name]), interval=1))
    for index, value in enumerate(DEMOS[name]):
        session.observe(index * 1000, value, 'QUERY_FAILED' if value is None else None)
    return session.report()


def replay(value):
    require(type(value) is dict and set(value) == {'schema', 'samples'}
            and value['schema'] == 'outlands-usb-samples/1', 'REPLAY_INVALID')
    rows = value['samples']
    require(type(rows) is list and 1 <= len(rows) <= MAX_SAMPLES, 'REPLAY_INVALID')
    session = Session('replay')
    for row in rows:
        require(type(row) is dict and set(row) == {'elapsed_ms', 'present', 'code'}, 'REPLAY_INVALID')
        session.observe(row['elapsed_ms'], row['present'], row['code'])
    return session.report()


def replay_file(value):
    maximum = 1024 * 1024
    return replay(strict_json(snapshot(value, maximum), maximum, 40000, 1024))


def export_report(value, report):
    """Create one fresh JSON file; no replacement, metadata sidecar or upload."""
    validate_report(report)
    target = local_path(value)
    parent = canonical_directory(target.parent)
    require(target.suffix.lower() == '.json', 'JSON_OUTPUT_REQUIRED')
    require(not target.exists() and not target.is_symlink(), 'OUTPUT_EXISTS')
    data = (json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')
    require(len(data) <= MAX_REPORT, 'REPORT_LIMIT')
    target = parent / target.name
    no_links(parent)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
                 | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    # An interrupted/failed write can leave a partial new file. Never delete it.


def validate_report(report):
    require(type(report) is dict, 'REPORT_INVALID')
    try:
        session = Session(report['mode'], Settings(report['requested_seconds'], report['interval_seconds']))
        require(type(report['samples']) is list and len(report['samples']) <= MAX_SAMPLES, 'REPORT_INVALID')
        for row in report['samples']:
            require(type(row) is dict and set(row) == {'elapsed_ms', 'state', 'code'}, 'REPORT_INVALID')
            require(type(row['state']) is str and row['state'] in ('present', 'absent', 'unknown'), 'REPORT_INVALID')
            present = None if row['state'] == 'unknown' else row['state'] == 'present'
            session.observe(row['elapsed_ms'], present, row['code'])
        require(report == session.report(report['outcome']), 'REPORT_INVALID')
    except (KeyError, TypeError, ValueError):
        raise TextError('REPORT_INVALID') from None
    return report


def monitor(device_id, settings, query, stop=None, on_update=None, clock=time.monotonic):
    """query returns a complete selected-scope snapshot or raises a fixed error."""
    from usb_windows import valid_device_id
    valid_device_id(device_id)
    settings.validate()
    stop = stop if stop is not None else threading.Event()
    session = Session('live', settings)
    start = clock()
    deadline = start + settings.seconds
    outcome = 'completed'
    try:
        while clock() < deadline:
            if stop.is_set():
                outcome = 'cancelled'
                break
            try:
                records = query(stop=stop)
                present = any(row['id'].casefold() == device_id.casefold() for row in records)
                code = None
            except TextError as error:
                code = str(error) if str(error) in CODES else 'QUERY_FAILED'
                if stop.is_set() or code == 'CANCELLED':
                    outcome = 'cancelled'
                    break
                present = None
            elapsed = round((clock() - start) * 1000)
            session.observe(elapsed, present, code)
            if on_update is not None:
                on_update(session.report('completed'))
            remaining = deadline - clock()
            if remaining <= 0:
                break
            if stop.wait(min(settings.interval, remaining)):
                outcome = 'cancelled'
                break
    except Exception:
        outcome = 'failed'
    return session.report(outcome)
