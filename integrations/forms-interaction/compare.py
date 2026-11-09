"""Compare exact wheel asset bytes across hosted OS and Python builds."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / 'integrations/forms-interaction/release.json'


def compare(artifacts: Path) -> dict:
    planned = json.loads(PLAN.read_text(encoding='utf-8'))['assets']
    folders = sorted(path for path in artifacts.iterdir() if path.is_dir())
    if len(folders) != 4:
        raise ValueError('FOUR_PLATFORM_BUILDS_REQUIRED')
    for folder in folders:
        names = {path.name for path in folder.iterdir() if path.is_file()}
        if names != set(planned):
            raise ValueError('ARTIFACT_MEMBERS_MISMATCH')
        for name, digest in planned.items():
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
                raise ValueError('PLATFORM_ASSET_DIGEST_MISMATCH')
    return {'status': 'PASS', 'platform_builds': len(folders), 'asset_count': len(planned),
            'exact_bytes_match': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', required=True, type=Path)
    print(json.dumps(compare(parser.parse_args().artifacts)))
