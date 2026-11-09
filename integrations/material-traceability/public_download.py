"""Download seven public material traceability wheel assets and fresh-install them."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from verify_wheels import verify

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / 'integrations/material-traceability/release.json'
PUBLIC_BASE = 'https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/'
HOSTS = {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if target.scheme != 'https' or target.hostname not in HOSTS or target.username or target.password:
            raise ValueError('PUBLIC_ASSET_REDIRECT_REFUSED')
        if any(key.lower() == 'authorization' for key in request.headers):
            raise ValueError('AUTHENTICATED_DOWNLOAD_REFUSED')
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def download(url: str, maximum: int) -> bytes:
    opener = build_opener(ProxyHandler({}), PublicRedirect())
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'outlands-wheel-public-check'})
            with opener.open(request, timeout=45) as response:
                if urlsplit(response.url).hostname not in HOSTS:
                    raise ValueError('PUBLIC_ASSET_HOST_REFUSED')
                body = response.read(maximum + 1)
            if len(body) > maximum:
                raise ValueError('PUBLIC_ASSET_SIZE_LIMIT')
            return body
        except (HTTPError, URLError) as error:
            if attempt == 2 or isinstance(error, HTTPError) and error.code < 500:
                raise
            time.sleep(2 * (attempt + 1))
    raise AssertionError('UNREACHABLE')


def check(workspace: Path) -> dict:
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    assert plan['format'] == 'outlands-material-traceability-wheel-release-v1'
    workspace = workspace.resolve()
    if workspace.exists() or not workspace.parent.is_dir():
        raise ValueError('NEW_PUBLIC_DOWNLOAD_WORKSPACE_REQUIRED')
    workspace.mkdir()
    for name, digest in plan['assets'].items():
        if Path(name).name != name:
            raise ValueError('ASSET_NAME_INVALID')
        maximum = 300_000 if name.endswith('.whl') else 5_000
        raw = download(PUBLIC_BASE + plan['tag'] + '/' + name, maximum)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('PUBLIC_ASSET_DIGEST_MISMATCH')
        (workspace / name).write_bytes(raw)
    result = verify(workspace)
    return {'status': result['status'], 'tag': plan['tag'], 'assets': len(plan['assets']),
            'individual': len(result['individual']), 'collection': result['collection'],
            'anonymous_download': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    print(json.dumps(check(parser.parse_args().workspace)))
