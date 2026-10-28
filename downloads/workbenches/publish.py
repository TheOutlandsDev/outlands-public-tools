"""Publish new focused download tags using identical four-platform accepted assets."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from packages import build as toolkit


def publish(artifacts):
    owner='TheOutlandsDev/outlands-public-tools';source=os.environ['GITHUB_SHA']
    if os.environ.get('GITHUB_REPOSITORY')!=owner or os.environ.get('GITHUB_REF')!='refs/heads/main':raise ValueError('MAIN_PUBLICATION_REQUIRED')
    groups={'workbench-download-'+platform+'-'+python for platform in ['Windows','Linux'] for python in ['3.12','3.13']}
    if {p.name for p in artifacts.iterdir()}!=groups:raise ValueError('ALL_FOUR_PLATFORMS_REQUIRED')
    contents=None
    for group in sorted(groups):
        current={p.name:p.read_bytes() for p in (artifacts/group).iterdir()}
        if contents is None:contents=current
        if current!=contents:raise ValueError('PLATFORM_BYTES_DIFFER')
    matrix=json.loads(contents['release-matrix.json']);expected={'release-matrix.json','SHA256SUMS.txt'}|{a['filename'] for a in matrix['applications']}
    if set(contents)!=expected or {a['app'] for a in matrix['applications']}!={'sql-report-workbench','developer-workspace'}:raise ValueError('EXACT_ASSET_SET_REQUIRED')
    sums=''.join(toolkit.digest(contents[n])+'  '+n+'\n' for n in sorted(expected-{'SHA256SUMS.txt'})).encode()
    if contents['SHA256SUMS.txt']!=sums:raise ValueError('CHECKSUM_LIST_MISMATCH')
    selected=artifacts/sorted(groups)[0]
    for app in matrix['applications']:
        if app['packaging_revision']!=source or toolkit.digest(contents[app['filename']])!=app['sha256']:raise ValueError('REVISION_OR_DIGEST_MISMATCH')
        toolkit.verify_archive(contents[app['filename']])
        prior=subprocess.run(['gh','release','view',app['tag'],'--repo',owner,'--json','url'],capture_output=True)
        if prior.returncode==0:print('Existing focused release retained unchanged: '+app['tag']);continue
        subprocess.run(['gh','release','create',app['tag'],str(selected/app['filename']),str(selected/'SHA256SUMS.txt'),str(selected/'release-matrix.json'),
                        '--repo',owner,'--target',source,'--title',app['app']+' '+app['version']+' - checked download and quick start','--latest=false',
                        '--notes-file',str(ROOT/'downloads/workbenches'/app['app']/'RELEASE.md')],check=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--artifacts',type=Path,required=True);publish(p.parse_args().artifacts)
