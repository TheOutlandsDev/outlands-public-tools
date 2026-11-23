"""Build the static tool library from the public catalog and verified release assets."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from zipfile import ZipFile

from manage import GENERATED, OWNER, ROOT, encoded, fetch, read_registry


GITHUB = f'https://github.com/{OWNER}'
PAGES_URL = 'https://theoutlandsdev.github.io/outlands-public-tools/'
MAX_BUNDLE_BYTES = 16 * 1024 * 1024
MAX_WHEEL_BYTES = 2 * 1024 * 1024
STATIC_FILES = ('index.html', 'styles.css', 'app.js', 'zip.js')


def release_url(asset):
    return f"{GITHUB}/releases/download/{asset['tag']}/{asset['filename']}"


def read_bundle(asset, local_path):
    if local_path is None:
        raw = fetch(release_url(asset), MAX_BUNDLE_BYTES)
    else:
        with local_path.open('rb') as source:
            raw = source.read(MAX_BUNDLE_BYTES + 1)
    if len(raw) > MAX_BUNDLE_BYTES or hashlib.sha256(raw).hexdigest() != asset['sha256']:
        raise ValueError('Active install bundle exceeds the size limit or has a different SHA-256')
    return raw


def select_wheels(data, bundle, raw):
    """Return individual wheels and add their published interface contracts to the catalog."""
    tools = {tool['id']: tool for tool in data['tools'] if tool.get('install_bundle')}
    tool_ids = bundle['tools']
    if len(tool_ids) != len(set(tool_ids)) or set(tools) != set(tool_ids):
        raise ValueError('Install bundle and catalog tool IDs differ')

    wheels = {}
    with ZipFile(io.BytesIO(raw)) as archive:
        members = archive.namelist()
        if len(members) != len(set(members)):
            raise ValueError('Install bundle contains duplicate member names')
        index = archive.getinfo('COMPONENTS.json')
        if index.file_size > MAX_WHEEL_BYTES:
            raise ValueError('Install bundle component index exceeds the size limit')
        records = json.loads(archive.read(index))['components']
        contracts = {record['id']: record for record in records}
        if len(records) != len(contracts) or set(contracts) != set(tool_ids):
            raise ValueError('Install bundle component index and catalog tool IDs differ')

        total_bytes = 0
        for tool_id, tool in tools.items():
            wheel = tool['wheel_package']
            name = wheel['filename']
            contract = contracts[tool_id]
            if (not re.fullmatch(r'outlands_[a-z0-9_]+-[0-9.]+-py3-none-any\.whl', name)
                or name in wheels or name != contract['filename']
                or wheel['sha256'] != contract['sha256']):
                raise ValueError(f'Invalid wheel mapping for {tool_id}')
            member = archive.getinfo(f'wheels/{name}')
            total_bytes += member.file_size
            if member.file_size > MAX_WHEEL_BYTES or total_bytes > MAX_BUNDLE_BYTES:
                raise ValueError(f'Wheel payload exceeds the size limit at {tool_id}')
            payload = archive.read(member)
            if hashlib.sha256(payload).hexdigest() != wheel['sha256']:
                raise ValueError(f'Wheel SHA-256 differs from the release plan for {tool_id}')
            wheels[name] = payload
            tool['interface'] = {
                key: value for key, value in contract.items()
                if key not in {'id', 'purpose', 'group', 'filename', 'sha256'}
            }
    return wheels


def add_collection_wheels(data, wheels):
    """Mirror verified collection wheels outside the frozen install bundle."""
    tools = {tool['id']: tool for tool in data['tools']}
    for collection in data['installable_collections']:
        members = [tools[row['id']] for row in collection['tools'] if not tools[row['id']]['install_bundle']]
        if not members:
            continue
        path = (ROOT / collection['plan']).with_name('components.json')
        contracts = {row['id']: row for row in json.loads(path.read_bytes())['components']}
        for tool in members:
            wheel = tool['wheel_package']
            name = wheel['filename']
            payload = fetch(release_url(wheel), MAX_WHEEL_BYTES)
            if name in wheels or hashlib.sha256(payload).hexdigest() != wheel['sha256']:
                raise ValueError(f"Invalid collection wheel for {tool['id']}")
            wheels[name] = payload
            tool['interface'] = {key: value for key, value in contracts[tool['id']].items()
                                 if key not in {'id', 'purpose', 'group', 'filename', 'sha256'}}


def llm_index(data, bundle, base):
    lines = [
        '# OUTLANDS Public Tools',
        '',
        '> An open source catalog of local applications and engineering tools. Use the catalog to pick',
        '> a tool by task, check its runtime requirements and read its example and validation notes.',
        '',
        '## Find a tool',
        '',
        f'- [Searchable library]({base}): browse by category and download type.',
        f'- [Tool catalog JSON]({base}tool-catalog.json): structured index for every registered tool and workbench.',
        f'- [GitHub index]({GITHUB}/blob/main/catalog/generated/INDEX.md): documentation, examples and validation.',
        f'- [Open source license and scope]({GITHUB}/blob/main/LICENSING.md): terms and included notices.',
        '',
        'In the JSON, use each tool’s `id`, `purpose` and `requirements` to select a tool. Open',
        '`guide`, `examples` and `validation` before use. Resolve repository paths against',
        f'`{GITHUB}/blob/main/`. `wheel_package` identifies a published individual wheel with its',
        'filename, release tag, runtime and SHA-256. `interface` records the exact Python and CLI',
        'entry points, input and result formats, fictional inputs and result limits for those wheels.',
        f'For wheel downloads, append `wheels/<filename>` to `{base}`.',
        'Use `standalone_release.download` for a direct source ZIP or independently published Python wheel.',
        'It includes a SHA-256 digest and links to its checksums, guide and validation.',
        'See `source_bundle`, `focused_release`, `windows_release` and `downloads` for additional archives.',
        '',
        '## Python packages',
        '',
        f"- [Active install bundle {bundle['version']}]({release_url(bundle)}): published wheel archive for {bundle['runtime']}.",
        f"- [Offline install and verification guide]({GITHUB}/blob/main/{bundle['guide']}): wheel and bundle installation.",
    ]
    for collection in data['installable_collections']:
        path = Path(collection['plan']).with_name('README.md').as_posix()
        lines.append(f"- [{collection['title']}]({GITHUB}/blob/main/{path}): APIs, examples and result limits.")
    return '\n'.join(lines) + '\n'


def build(output, bundle_path, base_url):
    parsed_url = urlsplit(base_url)
    if (parsed_url.scheme not in {'http', 'https'} or not parsed_url.hostname
        or parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment):
        raise ValueError('Use an HTTP(S) site URL without credentials, query or fragment')
    base_url = base_url.rstrip('/') + '/'
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f'Output directory already exists: {output}')

    data = json.loads((GENERATED / 'site-data.json').read_text(encoding='utf-8'))
    registry = read_registry()
    if (data['installable_bundles'] != registry['installable_bundles']
        or data['installable_collections'] != registry['installable_collections']):
        raise ValueError('Generate the catalog before building the library')
    bundle, = data['installable_bundles']
    wheels = select_wheels(data, bundle, read_bundle(bundle, bundle_path))
    add_collection_wheels(data, wheels)

    files = {name: (ROOT / 'catalog' / 'library' / name).read_bytes() for name in STATIC_FILES}
    files['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
    files['tool-catalog.json'] = encoded(data)
    files['llms.txt'] = llm_index(data, bundle, base_url).encode('utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.library-', dir=output.parent) as temporary:
        staging = Path(temporary) / 'site'
        staging.mkdir()
        for name, content in files.items():
            (staging / name).write_bytes(content)
        (staging / 'wheels').mkdir()
        for name, content in wheels.items():
            (staging / 'wheels' / name).write_bytes(content)
        staging.rename(output)
    return len(data['tools']), len(wheels)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='new directory for the static site')
    parser.add_argument('--bundle', type=Path, help='local copy of the active release ZIP')
    parser.add_argument('--base-url', default=PAGES_URL, help='site URL used in the AI navigation index')
    args = parser.parse_args()
    tool_count, wheel_count = build(args.output, args.bundle, args.base_url)
    print(f'Built catalog with {tool_count} components and {wheel_count} verified individual wheels.')
