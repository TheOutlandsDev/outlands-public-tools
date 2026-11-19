"""Verify GitHub Pages serves the tool library built by the current workflow."""

import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from secrets import token_hex
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from build_library import MAX_WHEEL_BYTES, PAGES_URL
from manage import GENERATED


ASSETS = {
    'index.html': ('text/html',),
    'styles.css': ('text/css',),
    'app.js': ('text/javascript', 'application/javascript'),
    'zip.js': ('text/javascript', 'application/javascript'),
    'llms.txt': ('text/plain',),
    'tool-catalog.json': ('application/json',),
    'LICENSE.txt': ('text/plain',),
}
WHEEL_TYPES = ('application/octet-stream', 'application/zip')
WHEEL_NAME = r'outlands_[a-z0-9_]+-[0-9.]+-py3-none-any\.whl'
MAX_SITE_ASSET_BYTES = 8 * 1024 * 1024
ENVIRONMENT_VARIABLE = 'OUTLANDS_LIBRARY_EXPECTED'


class LibraryMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()
        self.modules = set()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if 'id' in fields:
            self.ids.add(fields['id'])
        if tag == 'link':
            self.links.add((fields.get('rel'), fields.get('type'), fields.get('href')))
        if tag == 'script' and fields.get('type') == 'module':
            self.modules.add(fields.get('src'))


class RefuseRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def trusted_base(url):
    if url in {PAGES_URL, PAGES_URL.rstrip('/')}:
        return PAGES_URL
    parsed = urlsplit(url)
    if (parsed.scheme == 'http' and parsed.hostname == '127.0.0.1'
        and parsed.port and parsed.netloc == f'127.0.0.1:{parsed.port}'
        and parsed.path in {'', '/'} and not parsed.query and not parsed.fragment):
        return f'http://127.0.0.1:{parsed.port}/'
    raise ValueError('Use the OUTLANDS project Pages URL or http://127.0.0.1:<port>/')


def digest(body):
    return hashlib.sha256(body).hexdigest()


def check_catalog(body):
    """Check the live tool IDs and release records against this checkout's registry projection."""
    expected = json.loads((GENERATED / 'site-data.json').read_bytes())
    data = json.loads(body)
    for key, value in expected.items():
        if key != 'tools' and data.get(key) != value:
            raise ValueError(f'Catalog {key} differs from the repository projection')

    live = {tool['id']: tool for tool in data['tools']}
    if len(live) != len(data['tools']) or live.keys() != {tool['id'] for tool in expected['tools']}:
        raise ValueError('Catalog tool IDs differ from the repository projection')

    wheels = {}
    for record in expected['tools']:
        tool_id = record['id']
        tool = live[tool_id]
        if any(tool.get(key) != value for key, value in record.items()):
            raise ValueError(f'Catalog tool details differ for {tool_id}')
        wheel = tool['wheel_package']
        if wheel is None:
            continue
        contract = tool.get('interface') or {}
        required = ('package', 'command', 'python_api', 'input_format', 'result_format', 'example_input')
        if not all(isinstance(contract.get(key), str) and contract[key].strip() for key in required):
            raise ValueError(f'Incomplete Python interface for {tool_id}')
        wheels[tool_id] = wheel
    if not wheels:
        raise ValueError('No individual wheels in the catalog')
    return len(live), len(wheels), wheels[min(wheels)]


def check_navigation(bodies, base):
    markup = LibraryMarkup()
    markup.feed(bodies['index.html'].decode('utf-8'))
    markup.close()
    links = {
        ('stylesheet', None, 'styles.css'),
        ('alternate', 'application/json', 'tool-catalog.json'),
        ('alternate', 'text/plain', 'llms.txt'),
    }
    if not (links <= markup.links and 'app.js' in markup.modules and {'catalog', 'bundle', 'ai'} <= markup.ids):
        raise ValueError('Library HTML is missing its stylesheet, app module or catalog navigation')
    app = bodies['app.js'].decode('utf-8')
    if not (re.search(r'\bfrom\s+[\'"]\./zip\.js[\'"]', app)
        and re.search(r'\bfetch\(\s*[\'"]tool-catalog\.json[\'"]', app)):
        raise ValueError('Library app does not load its ZIP module and JSON catalog')
    ai_index = bodies['llms.txt'].decode('utf-8')
    if not ai_index.startswith('# OUTLANDS Public Tools\n') or f']({base}tool-catalog.json)' not in ai_index:
        raise ValueError('AI index does not point to the current library catalog')


def expected_manifest(site, base):
    bodies = {name: (site / name).read_bytes() for name in ASSETS}
    check_navigation(bodies, base)
    _, _, wheel = check_catalog(bodies['tool-catalog.json'])
    name = wheel['filename']
    if not re.fullmatch(WHEEL_NAME, name):
        raise ValueError('Invalid published wheel filename')
    if digest((site / 'wheels' / name).read_bytes()) != wheel['sha256']:
        raise ValueError('Built sample wheel does not match its published SHA-256')
    return {'assets': {name: digest(body) for name, body in bodies.items()}, 'wheel': wheel}


def fetch_asset(opener, base, path, nonce, mime_types, maximum=MAX_SITE_ASSET_BYTES):
    request_url = f'{base}{path}?smoke={nonce}'
    request = Request(request_url, headers={
        'Cache-Control': 'no-cache',
        'User-Agent': 'OUTLANDS-Library-Smoke',
    })
    with opener.open(request, timeout=12) as response:
        if response.status != 200 or response.geturl() != request_url:
            raise ValueError(f'Unexpected response URL or status for {path or "library root"}')
        if response.headers.get_content_type() not in mime_types:
            raise ValueError(f'Unexpected content type for {path or "library root"}')
        body = response.read(maximum + 1)
    if not body or len(body) > maximum:
        raise ValueError(f'Unexpected size for {path or "library root"}')
    return body


def check_site(base, expected):
    opener = build_opener(ProxyHandler({}), RefuseRedirects())
    nonce = token_hex(8)
    bodies = {}
    for name, mime_types in ASSETS.items():
        path = '' if name == 'index.html' else name
        body = fetch_asset(opener, base, path, nonce, mime_types)
        if digest(body) != expected['assets'][name]:
            raise ValueError(f'Served {name} differs from the current build')
        bodies[name] = body
    check_navigation(bodies, base)
    components, wheel_count, wheel = check_catalog(bodies['tool-catalog.json'])
    name = wheel['filename']
    if wheel != expected['wheel'] or not re.fullmatch(WHEEL_NAME, name):
        raise ValueError('Served sample wheel differs from the current build manifest')
    payload = fetch_asset(opener, base, 'wheels/' + name, nonce, WHEEL_TYPES, MAX_WHEEL_BYTES)
    if digest(payload) != wheel['sha256']:
        raise ValueError(f'Served sample wheel has a different SHA-256: {name}')
    return components, wheel_count, name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=PAGES_URL, help='exact project Pages URL or loopback fixture URL')
    parser.add_argument('--attempts', type=int, choices=range(1, 7), default=4)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--expected-site', type=Path, help='compare against this local build output')
    source.add_argument('--print-expected', type=Path, help='print the manifest for this build output and exit')
    args = parser.parse_args()

    base = trusted_base(args.url)
    if args.print_expected is not None:
        print(json.dumps(expected_manifest(args.print_expected, base), separators=(',', ':')))
        return

    if args.expected_site is not None:
        expected = expected_manifest(args.expected_site, base)
    else:
        manifest = os.getenv(ENVIRONMENT_VARIABLE)
        if not manifest:
            parser.error(f'Provide --expected-site or set {ENVIRONMENT_VARIABLE} from the build job')
        expected = json.loads(manifest)

    for attempt in range(1, args.attempts + 1):
        try:
            components, wheels, name = check_site(base, expected)
        except (URLError, TimeoutError, ValueError) as exc:
            if attempt == args.attempts:
                raise SystemExit(f'Library smoke check failed: {exc}') from None
            print(f'Library smoke attempt {attempt} failed: {exc}', flush=True)
            time.sleep(3 * 2 ** (attempt - 1))
        else:
            print(f'Verified Pages catalog for {components} components, {wheels} wheel contracts and {name}.')
            break


if __name__ == '__main__':
    main()
