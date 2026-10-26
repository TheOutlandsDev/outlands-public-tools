"""OUTLANDS Desktop Network Monitor. Original MIT source; explicit collection only."""
from __future__ import annotations
import argparse
import json
import re
import sys
import threading
from monitor_core import MonitorError, demo, export_report, load_replay


class Parser(argparse.ArgumentParser):
    def error(self, _message):raise MonitorError('ARGUMENTS_INVALID')


def main(argv=None):
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest='command')
    demonstration = commands.add_parser('demo', help='Fictional local packet metadata; no capture or lookup')
    demonstration.add_argument('--output')
    replay = commands.add_parser('replay', help='Read neutral IPv4 packet-metadata JSON')
    replay.add_argument('--file', required=True)
    replay.add_argument('--output')
    live = commands.add_parser('capture', help='Explicit, bounded, optional Scapy IPv4 capture')
    live.add_argument('--live', action='store_true', required=True)
    live.add_argument('--interface', required=True)
    live.add_argument('--seconds', type=float, default=30)
    live.add_argument('--output')
    online = commands.add_parser('lookup', help='Explicitly send one public IPv4 address to OTX')
    online.add_argument('--allow-online', action='store_true', required=True)
    online.add_argument('--ip', required=True)
    commands.add_parser('system', help='Explicit local system-counter snapshot; no packet capture')
    commands.add_parser('gui', help='Open the idle desktop')
    try:
        args = parser.parse_args(argv)
        if args.command is None:parser.print_help();return 0
        if args.command == 'gui':
            from monitor_gui import main as desktop
            return desktop()
        if args.command == 'demo':report = demo().report()
        elif args.command == 'replay':report = load_replay(args.file).report()
        elif args.command in ('capture', 'lookup'):
            from monitor_worker import run_isolated
            arguments = (args.interface, args.seconds) if args.command == 'capture' else (args.ip,)
            report = run_isolated(args.command, arguments, threading.Event())
        else:
            from monitor_worker import system_snapshot
            report = {'status': 'OBSERVATION', 'system': system_snapshot()}
        if getattr(args, 'output', None):export_report(args.output, report)
        print(json.dumps(report, sort_keys=True, ensure_ascii=True, allow_nan=False))
        return 1 if report.get('status') == 'REVIEW_REQUIRED' else 0
    except KeyboardInterrupt:
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'INTERRUPTED'}));return 130
    except MonitorError as error:
        code = str(error) if re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}', str(error)) else 'OPERATION_FAILED'
        print(json.dumps({'status': 'INCOMPLETE', 'error': code}));return 2
    except Exception:
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'OPERATION_FAILED'}));return 2


if __name__ == '__main__':raise SystemExit(main())
