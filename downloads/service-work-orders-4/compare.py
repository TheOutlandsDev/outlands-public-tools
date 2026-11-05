"""Confirm four hosted platform builds produced the exact same pinned assets."""
import argparse
import hashlib
import json
from pathlib import Path

from build import plan
from verify import verify


def compare(root):
    value = plan()
    root = Path(root)
    outputs = []
    for system in ('Linux', 'Windows'):
        for python in ('3.12', '3.13'):
            directory = root / ('service-work-orders-' + system + '-' + python)
            archive = directory / ('outlands-service-work-orders-4-' + value['version'] + '.zip')
            checksums = directory / 'SHA256SUMS.txt'
            outputs.append((archive.read_bytes(), checksums.read_bytes()))
            verify(archive, checksums)
    if len({archive for archive, _ in outputs}) != 1 or len({checksums for _, checksums in outputs}) != 1:
        raise ValueError('PLATFORM_BYTES_DIFFER')
    return {'status': 'PASS', 'platform_builds': 4,
            'sha256': hashlib.sha256(outputs[0][0]).hexdigest(), 'byte_equal': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', required=True)
    args = parser.parse_args()
    print(json.dumps(compare(args.artifacts), sort_keys=True))
