"""Generate original SVG text fixtures; never render them or read other artwork."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import svg_inspector as s

CLEAN = '''<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180">
  <title>Fictional inspection example</title>
  <defs><linearGradient id="paint"><stop offset="0" stop-color="blue"/><stop offset="1" stop-color="gold"/></linearGradient></defs>
  <rect x="10" y="10" width="300" height="160" rx="12" fill="url(#paint)"/>
</svg>
'''
REVIEW = '''<svg xmlns="http://www.w3.org/2000/svg" width="auto" height="180" viewBox="0 0 320 180">
  <title>Fictional review markers only</title>
  <!-- Intentionally empty inert declarations. Do not render inspection inputs. -->
  <script type="application/x-outlands-fictional"/>
  <foreignObject/>
  <g id="duplicate"/><g id="duplicate"/>
  <use href="#missing"/>
  <rect onclick="" style="fill:url(#duplicate)"/>
  <image href="data:text/plain,Fictional-empty-placeholder"/>
</svg>
'''


def create(value):
    target = s.local_path(value)
    s.no_links(target.parent)
    s.require(not target.exists() and not target.is_symlink(), 'DESTINATION_EXISTS')
    target.mkdir(mode=0o700)
    s.write_exclusive(target / 'clean.svg', CLEAN.encode('utf-8'))
    s.write_exclusive(target / 'review.svg', REVIEW.encode('utf-8'))
    s.write_exclusive(target / 'README.txt', b'Original fictional markup only. Inspect as text; do not render review.svg or arbitrary inspection inputs.\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    try:
        create(args.destination)
        print(json.dumps({'status': 'FICTIONAL_FIXTURES_CREATED', 'files': 2}))
    except (s.InspectionError, OSError, ValueError):
        print(json.dumps({'status': 'INCOMPLETE', 'error': 'FRESH_TRUSTED_DESTINATION_REQUIRED'}))
        raise SystemExit(2)
