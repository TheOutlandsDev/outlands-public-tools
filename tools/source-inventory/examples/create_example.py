"""Create a fresh fictional input/report workspace. Original MIT example."""
import argparse
import json
from pathlib import Path
import stat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    target = args.destination.absolute()
    try:
        if not args.destination.is_absolute() or '..' in target.parts or target.exists():
            raise ValueError
        for path in (target.parent, *target.parent.parents):
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError
        if not target.parent.is_dir():
            raise ValueError
        target.mkdir(mode=0o700, exist_ok=False)
        for folder in ['input', 'reports', 'input/empty', 'input/docs/deep', 'input/.git', 'input/scratch']:
            (target / folder).mkdir(mode=0o700, parents=True, exist_ok=True)
        fixtures = {'input/app.py': '# Fictional example only.\n',
                    'input/docs/notes.md': '# Fictional notes\n',
                    'input/docs/deep/detail.md': 'Generated demonstration text.\n',
                    'input/.git/placeholder': 'Fictional excluded metadata.\n',
                    'input/scratch/draft.txt': 'Fictional optional exclusion.\n',
                    'input/.env': 'FICTIONAL_EXAMPLE=1\n'}
        for name, text in fixtures.items():
            with (target / name).open('x', encoding='utf-8') as stream:
                stream.write(text)
        print(json.dumps({'result': 'FICTIONAL_EXAMPLE_CREATED', 'input': 'input',
                          'reports': 'reports', 'contains_real_data': False}))
        return 0
    except (OSError, ValueError):
        print(json.dumps({'result': 'INCOMPLETE', 'error': 'FRESH_TRUSTED_DESTINATION_REQUIRED'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
