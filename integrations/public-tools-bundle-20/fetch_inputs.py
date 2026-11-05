"""Download the twenty-five previously released wheel inputs without credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
PLANS = ('integrations/model-routing/release.json',
         'integrations/ai-decision-contracts/release.json',
         'integrations/probability-integrity/release.json',
         'integrations/cache-retry/release.json',
         'integrations/review-change/release.json')
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


def expected():
    result = {}
    for path in PLANS:
        plan = json.loads((ROOT / path).read_text(encoding='utf-8'))
        wheels = {name: digest for name, digest in plan['assets'].items() if name.endswith('.whl')}
        if len(wheels) != 5:
            raise ValueError('FIVE_WHEELS_PER_RELEASE_REQUIRED')
        for name, digest in wheels.items():
            if Path(name).name != name or name in result:
                raise ValueError('INPUT_WHEEL_NAME_INVALID')
            result[name] = (plan['tag'], digest)
    return result


def download(url):
    opener = build_opener(ProxyHandler({}), PublicRedirect())
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'outlands-combined-wheel-check'})
            with opener.open(request, timeout=45) as response:
                if urlsplit(response.url).hostname not in HOSTS:
                    raise ValueError('PUBLIC_ASSET_HOST_REFUSED')
                raw = response.read(300_001)
            if len(raw) > 300_000:
                raise ValueError('PUBLIC_WHEEL_SIZE_LIMIT')
            return raw
        except (HTTPError, URLError):
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise AssertionError('UNREACHABLE')


def fetch(output):
    output = output.resolve()
    if not output.is_dir() or any(output.iterdir()) or ROOT == output or ROOT in output.parents:
        raise ValueError('EMPTY_EXTERNAL_INPUT_DIRECTORY_REQUIRED')
    items = expected()
    for name, (tag, digest) in items.items():
        raw = download(BASE + tag + '/' + name)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('PUBLIC_WHEEL_DIGEST_MISMATCH')
        (output / name).write_bytes(raw)
    return {'status': 'PASS', 'anonymous_download': True, 'wheels': len(items)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    print(json.dumps(fetch(parser.parse_args().output)))
