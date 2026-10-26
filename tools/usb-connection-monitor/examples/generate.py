"""Write two invented neutral sample files in a new explicit directory. MIT."""
from pathlib import Path
import json
import os
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inspection_support import Parser, canonical_directory, cli_error, local_path, require


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument('--output', required=True)
    try:
        args = parser.parse_args(argv)
        target = local_path(args.output)
        parent = canonical_directory(target.parent)
        require(not target.exists() and not target.is_symlink(), 'OUTPUT_EXISTS')
        target = parent / target.name
        target.mkdir(mode=0o700, exist_ok=False)
        for name, states in [('reconnect', [True, False, True]), ('query-gap', [True, None, False, True])]:
            value = {'schema': 'outlands-usb-samples/1', 'samples': [
                {'elapsed_ms': i * 1000, 'present': present,
                 'code': 'QUERY_FAILED' if present is None else None} for i, present in enumerate(states)]}
            data = (json.dumps(value, indent=2) + '\n').encode()
            fd = os.open(target/(name+'.json'), os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                         getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0), 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
        print(json.dumps({'status': 'FICTIONAL_EXAMPLES_CREATED', 'files': 2}))
        return 0
    except Exception as error:
        return cli_error(error)


if __name__ == '__main__':
    raise SystemExit(main())
