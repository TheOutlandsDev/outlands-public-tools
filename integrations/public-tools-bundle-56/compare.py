"""Compare exact ZIP and checksum assets across four hosted platform builds."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def compare(artifacts):
    plan = json.loads((HERE / 'release.json').read_text(encoding='utf-8'))
    folders = sorted(path for path in artifacts.iterdir() if path.is_dir())
    if len(folders) != 4:
        raise ValueError('FOUR_PLATFORM_BUILDS_REQUIRED')
    for folder in folders:
        if {path.name for path in folder.iterdir() if path.is_file()} != set(plan['assets']):
            raise ValueError('ASSET_MEMBERS_MISMATCH')
        for name, sha in plan['assets'].items():
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != sha:
                raise ValueError('PLATFORM_ASSET_DIGEST_MISMATCH')
    return {'status': 'PASS', 'platform_builds': 4, 'assets': 2, 'exact_bytes_match': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', required=True, type=Path)
    print(json.dumps(compare(parser.parse_args().artifacts)))
