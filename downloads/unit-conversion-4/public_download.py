"""Fetch public release assets without credentials and exercise a fresh download."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from accept import accept
from build import plan

OWNER = 'TheOutlandsDev'
REPO = 'outlands-public-tools'
TAG = 'unit-conversion-4-v1.0.0'


def allowed(url):
    target = urlsplit(url)
    return target.scheme == 'https' and (target.hostname == 'github.com' or
                                           (target.hostname or '').endswith('.githubusercontent.com'))


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if not allowed(newurl):
            raise ValueError('PUBLIC_DOWNLOAD_HOST_REFUSED')
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def download(name, maximum):
    url = 'https://github.com/' + OWNER + '/' + REPO + '/releases/download/' + TAG + '/' + name
    request = Request(url, headers={'User-Agent': 'outlands-unit-conversion-public-check'})
    with build_opener(SafeRedirect()).open(request, timeout=45) as response:
        if not allowed(response.url):
            raise ValueError('PUBLIC_DOWNLOAD_HOST_REFUSED')
        body = response.read(maximum + 1)
    if len(body) > maximum:
        raise ValueError('PUBLIC_DOWNLOAD_LIMIT')
    return body


def check(workspace):
    value = plan()
    workspace = Path(workspace).resolve()
    if workspace.exists() or not workspace.parent.is_dir():
        raise ValueError('NEW_DOWNLOAD_WORKSPACE_REQUIRED')
    workspace.mkdir()
    name = 'outlands-unit-conversion-4-' + value['version'] + '.zip'
    archive = workspace / name
    checksum = workspace / 'SHA256SUMS.txt'
    archive.write_bytes(download(name, 6_000_000))
    checksum.write_bytes(download('SHA256SUMS.txt', 1024))
    result = accept(archive, checksum)
    return {'status': 'PASS', 'sha256': result['sha256'],
            'source_checks': result['source_checks'],
            'fictional_demos': result['fictional_demos'],
            'actual_public_assets': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.workspace), sort_keys=True))
