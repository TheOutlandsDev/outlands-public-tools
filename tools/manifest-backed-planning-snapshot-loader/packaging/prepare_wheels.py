"""Download the reviewed wheels for this exact Windows or Linux Python ABI."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import re
import sys
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DEPENDENCIES = (
    'openpyxl', 'et-xmlfile', 'defusedxml', 'annotated-types', 'pydantic', 'pydantic-core', 'typing-extensions', 'typing-inspection',
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, url):
        return None


def select_wheels(lock):
    if lock['schema'] != 1 or lock['index'] != 'https://pypi.org/simple':
        raise ValueError('Unexpected dependency lock')
    minor = sys.version_info[:2]
    if (
        sys.implementation.name != 'cpython'
        or minor not in {(3, 12), (3, 15)}
        or platform.machine().lower() not in {'x86_64', 'amd64'}
        or sys.platform not in {'win32', 'linux'}
    ):
        raise ValueError('Use x64 CPython 3.12 or 3.15 on Windows or Linux.')
    tag = f'cp{minor[0]}{minor[1]}'
    wheel_platform = (
        'win_amd64' if sys.platform == 'win32' else 'manylinux2014_x86_64.manylinux_2_17_x86_64'
    )
    packages = {}
    names = set()
    for name, package in sorted(lock['packages'].items()):
        if name == 'colorama' and sys.platform != 'win32':
            continue
        if name == 'pydantic-core':
            expected = f"pydantic_core-{package['version']}-{tag}-{tag}-{wheel_platform}.whl"
            records = [row for row in package['wheels'] if row['filename'] == expected]
        else:
            records = package['wheels']
        if len(records) != 1:
            raise ValueError('Expected one pinned wheel for this Python profile.')
        wheel = records[0]
        filename = wheel['filename']
        url = urlsplit(wheel['url'])
        if (
            not re.fullmatch(r'[0-9A-Za-z_.-]+\.whl', filename)
            or filename in names
            or not re.fullmatch(r'[0-9a-f]{64}', wheel['sha256'])
            or type(wheel['bytes']) is not int
            or not 0 < wheel['bytes'] <= 8 * 1024 * 1024
            or url.scheme != 'https'
            or url.netloc != 'files.pythonhosted.org'
            or not url.path.startswith('/packages/')
            or url.path.rsplit('/', 1)[-1] != filename
            or url.query
            or url.fragment
        ):
            raise ValueError('Invalid wheel identity in the dependency lock.')
        names.add(filename)
        packages[name] = {**wheel, 'version': package['version']}
    if not set(RUNTIME_DEPENDENCIES) <= packages.keys():
        raise ValueError('Missing runtime wheel in the dependency lock.')
    return packages


def prepare(destination):
    if (
        not destination.is_absolute()
        or not destination.parent.is_dir()
        or os.path.lexists(destination)
        or destination.resolve().is_relative_to(ROOT)
    ):
        raise ValueError('Choose a fresh absolute wheelhouse outside the source directory.')
    lock = json.loads((ROOT / 'WHEEL-LOCK.json').read_bytes())
    packages = select_wheels(lock)
    opener = build_opener(NoRedirect())
    payloads = {}
    for name, wheel in packages.items():
        with opener.open(wheel['url'], timeout=30) as response:
            data = response.read(wheel['bytes'] + 1)
        if len(data) != wheel['bytes'] or sha256(data).hexdigest() != wheel['sha256']:
            raise ValueError(f'Pinned wheel bytes differ for {name}.')
        payloads[wheel['filename']] = data

    destination.mkdir()
    for filename, data in payloads.items():
        with (destination / filename).open('xb') as stream:
            stream.write(data)
    return {
        name: {key: wheel[key] for key in ('version', 'filename', 'sha256')}
        for name, wheel in packages.items()
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.out)))
