"""Original MIT demo launcher. No dependency installation or live sampling."""
import sys
from pathlib import Path

def main(args=None):
    if sys.version_info[:2] not in ((3, 12), (3, 13)):
        print('Use Python 3.12 or 3.13 from https://www.python.org/downloads/. See START-HERE.md.', file=sys.stderr)
        return 2
    args = sys.argv[1:] if args is None else args
    if args == ['--check']:
        if not (Path(__file__).parent / 'resource_monitor/static/index.html').is_file():
            print('Extract the complete ZIP into a new folder. See START-HERE.md.', file=sys.stderr)
            return 2
        print('Ready: supported Python; fictional demo needs no pip packages or live sampler.')
        return 0
    from resource_monitor.__main__ import main as monitor
    # Demo is always explicit here; live collection requires the documented CLI.
    return monitor(['serve', '--demo', '--port', '0', *args])

if __name__ == '__main__':
    raise SystemExit(main())
