"""Anonymously download the combined ZIP and test fresh offline installs."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from verify import verify
from build import ROOT, HERE, ZIP_NAME

BASE = 'https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/'
HOSTS = {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if target.scheme != 'https' or target.hostname not in HOSTS or target.username or target.password:
            raise ValueError('PUBLIC_ASSET_REDIRECT_REFUSED')
        if any(key.lower() == 'authorization' for key in request.headers):
            raise ValueError('AUTHENTICATED_DOWNLOAD_REFUSED')
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def check(workspace):
    workspace = workspace.resolve()
    if workspace.exists() or not workspace.parent.is_dir() or workspace == ROOT or ROOT in workspace.parents:
        raise ValueError('NEW_EXTERNAL_WORKSPACE_REQUIRED')
    workspace.mkdir()
    plan = json.loads((HERE / 'release.json').read_text(encoding='utf-8'))
    if plan['tag'] != 'public-tools-install-bundle-v1.11.0' or set(plan['assets']) != {ZIP_NAME, 'SHA256SUMS.txt'}:
        raise ValueError('RELEASE_PLAN_INVALID')
    opener = build_opener(ProxyHandler({}), PublicRedirect())
    for name, sha in plan['assets'].items():
        url = BASE + plan['tag'] + '/' + name
        with opener.open(Request(url, headers={'User-Agent': 'outlands-bundle-public-check'}), timeout=45) as response:
            if urlsplit(response.url).hostname not in HOSTS:
                raise ValueError('PUBLIC_ASSET_HOST_REFUSED')
            raw = response.read((4_000_000 if name == ZIP_NAME else 5_000) + 1)
        if len(raw) > (4_000_000 if name == ZIP_NAME else 5_000) or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('PUBLIC_ASSET_DIGEST_MISMATCH')
        (workspace / name).write_bytes(raw)
    result = verify(workspace / ZIP_NAME, workspace / 'SHA256SUMS.txt')
    return {'status': result['status'], 'tag': plan['tag'], 'anonymous_download': True,
            'archive_sha256': result['archive_sha256'], 'fresh_installs': result['fresh_installs']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    print(json.dumps(check(parser.parse_args().workspace)))
