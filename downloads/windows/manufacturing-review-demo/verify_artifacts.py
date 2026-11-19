"""Verify the two CI builds and the Windows native and browser evidence."""

import argparse
import json
from pathlib import Path
import zipfile

from build import (
    FILENAME,
    PREFIX,
    RUNTIME,
    RUNTIME_SHA,
    SOURCE,
    SOURCE_SHA,
    TAG,
    encoded,
    git,
    payload,
    sha,
    verify,
)

CAPTURES = {
    f'manufacturing-{section}.jpg'
    for section in ('overview', 'capacity', 'materials', 'inspection', 'outcomes', 'evidence', 'narrow')
}
COMMON = {FILENAME, 'release-receipt.json', 'SHA256SUMS.txt'}
MEDIA = {'manufacturing-review-walkthrough.mp4', 'manufacturing-review-walkthrough.vtt'}
RELEASE_ASSETS = COMMON | MEDIA | CAPTURES | {'acceptance.json'}


def validate(artifacts):
    windows = artifacts / 'manufacturing-demo-Windows'
    linux = artifacts / 'manufacturing-demo-Linux'
    assert {path.name for path in artifacts.iterdir()} == {windows.name, linux.name}
    assert {path.name for path in windows.iterdir()} == RELEASE_ASSETS
    assert {path.name for path in linux.iterdir()} == COMMON
    for name in COMMON:
        assert (windows / name).read_bytes() == (linux / name).read_bytes(), name

    head = git('rev-parse', 'HEAD').decode().strip()
    receipt = json.loads((windows / 'release-receipt.json').read_bytes())
    acceptance = json.loads((windows / 'acceptance.json').read_bytes())
    raw_package = (windows / FILENAME).read_bytes()
    assert receipt['tag'] == TAG and receipt['filename'] == FILENAME
    assert receipt['source_zip_sha256'] == SOURCE_SHA and receipt['runtime_sha256'] == RUNTIME_SHA
    assert receipt['tools'] == 12 and receipt['exercises'] == 2
    assert receipt['packaging_revision'] == acceptance['packaging_revision'] == head
    assert receipt['source_revision'] == acceptance['source_revision'] == SOURCE
    assert receipt['sha256'] == acceptance['package_sha256'] == sha(raw_package)
    assert acceptance['status'] == 'PASS' and acceptance['runtime'] == RUNTIME
    assert acceptance['browser'] is True and acceptance['browser_checks'] == 9
    assert acceptance['cli_checks'] == 36 and acceptance['expected_review_outcomes'] == 17

    assert set(acceptance['captures']) == CAPTURES
    for name, capture in acceptance['captures'].items():
        raw_capture = (windows / name).read_bytes()
        assert len(raw_capture) == capture['bytes'] and sha(raw_capture) == capture['sha256'], name
    video = acceptance['video']
    assert video['seconds'] == 60 and video['actual_windows_bundle_report'] is True
    assert sha((windows / video['filename']).read_bytes()) == video['sha256']
    assert sha((windows / video['captions']).read_bytes()) == video['captions_sha256']

    expected = payload()
    expected['PACKAGE-MANIFEST.json'] = encoded(dict(
        schema=1,
        version='0.1.0-windows.1',
        source_revision=SOURCE,
        source_zip_sha256=receipt['source_zip_sha256'],
        packaging_revision=head,
        runtime=RUNTIME,
        files=[
            dict(path=name, bytes=len(raw), sha256=sha(raw))
            for name, raw in sorted(expected.items())
        ],
    ))
    verify(raw_package)
    with zipfile.ZipFile(windows / FILENAME) as archive:
        names = archive.namelist()
        assert set(names) == {PREFIX + name for name in expected}
        assert len(names) == len(expected) == receipt['files']
        for name, raw in expected.items():
            assert archive.read(PREFIX + name) == raw, name
    return windows, receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, required=True)
    args = parser.parse_args()
    validate(args.artifacts)
    print('PASS: identical platform builds and verified Windows native and browser evidence')
