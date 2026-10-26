"""USB Connection Monitor: explicit Windows queries, fictional demos and private reports."""
from __future__ import annotations
import json
import sys
from inspection_support import Parser, TextError, cli_error


def main(argv=None):
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest='command')
    demonstration = commands.add_parser('demo', help='Fictional timeline; no hardware or Windows query')
    demonstration.add_argument('--scenario', choices=['stable', 'reconnect', 'query-gap'], default='reconnect')
    demonstration.add_argument('--output')
    replay = commands.add_parser('replay', help='Read the documented neutral sample JSON format')
    replay.add_argument('--file', required=True)
    replay.add_argument('--output')
    devices = commands.add_parser('devices', help='Explicit Windows query; IDs/names printed privately')
    devices.add_argument('--live', action='store_true', required=True)
    watch = commands.add_parser('watch', help='Explicit Windows monitoring of one exact USB instance')
    watch.add_argument('--live', action='store_true', required=True)
    watch.add_argument('--device-id', required=True)
    watch.add_argument('--seconds', type=float, default=60)
    watch.add_argument('--interval', type=float, default=2)
    watch.add_argument('--output')
    commands.add_parser('gui', help='Open idle desktop; scanning and monitoring are explicit')
    try:
        args = parser.parse_args(argv)
        if args.command is None:
            parser.print_help()
            return 0
        if args.command == 'gui':
            from usb_gui import main as desktop
            return desktop()
        from usb_core import Settings, demo, export_report, monitor, replay_file
        if args.command == 'demo':
            result = demo(args.scenario)
        elif args.command == 'replay':
            result = replay_file(args.file)
        elif args.command == 'devices':
            from usb_windows import query_devices
            result = {'status': 'OK', 'scope': 'Private local selection list; do not publish.',
                      'devices': query_devices()}
        else:
            from usb_windows import query_devices, valid_device_id, powershell_path
            valid_device_id(args.device_id)
            settings = Settings(args.seconds, args.interval).validate()
            powershell_path()  # Refuse unsupported platform before starting a session.
            result = monitor(args.device_id, settings, query_devices)
        if getattr(args, 'output', None):
            export_report(args.output, result)
        print(json.dumps(result, sort_keys=True, ensure_ascii=True, allow_nan=False))
        return 1 if result['status'] == 'REVIEW_REQUIRED' else 0
    except (TextError, OSError, ValueError) as error:
        return cli_error(error)
    except KeyboardInterrupt:
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'INTERRUPTED',
                          'note': 'No automatic report is saved.'}))
        return 130
    except Exception:
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'OPERATION_FAILED'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
