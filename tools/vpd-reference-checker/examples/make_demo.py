"""Create authored structural JSON and empty placeholders; never real media."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vpd_references as v


def create(destination, *, complete=False):
    target = v.local_path(destination)
    v.no_links(target.parent)
    v.require(not target.exists() and not target.is_symlink(), 'DESTINATION_EXISTS')
    project = {'projinfo': {'projectfile': '/fictional/old-workspace/orchard.vpd'},
               'timeline': {'subitems': [{'subitems': [{'type': 'fictional-block'}]}]},
               'videolist': {'subitems': [{'title': 'Fictional clip A', 'path': '/fictional/old-media/clip-a.mp4'},
                                         {'title': 'Fictional clip B', 'path': '/fictional/old-media/clip-b.mp4'}]},
               'audiolist': {'subitems': []}, 'imagelist': {'subitems': []}, 'subtitlelist': {'subitems': []}}
    data = (json.dumps(project, indent=2) + '\n').encode('utf-8')
    mapping = {'schemaVersion': 1, 'projectSha256': hashlib.sha256(data).hexdigest(),
               'files': [{'referenceId': 'ref-000002', 'relativePath': 'media/clip-a.mp4'},
                         {'referenceId': 'ref-000003', 'relativePath': 'media/clip-b.mp4'}]}
    target.mkdir(mode=0o700)
    v.exclusive_write(target / 'project.vpd', data)
    v.exclusive_write(target / 'mapping.json', (json.dumps(mapping, indent=2) + '\n').encode('utf-8'))
    (target / 'copies' / 'media').mkdir(parents=True, mode=0o700)
    v.exclusive_write(target / 'copies/media/clip-a.mp4', b'')
    if complete:
        v.exclusive_write(target / 'copies/media/clip-b.mp4', b'')
    v.exclusive_write(target / 'README.txt', b'Fictional structural fixture only. Empty .mp4 placeholders are not playable media.\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--complete', action='store_true', help='Create both empty placeholders so mapped metadata checks find no missing file.')
    args = parser.parse_args()
    try:
        create(args.destination, complete=args.complete)
        print(json.dumps({'status': 'FICTIONAL_FIXTURE_CREATED', 'empty_placeholders': 2 if args.complete else 1}))
    except (v.CheckError, OSError, ValueError):
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'DEMO_CREATION_FAILED'}))
        raise SystemExit(2)
