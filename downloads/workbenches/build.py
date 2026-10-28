"""Package two fixed, reviewed application trees with separate handoff guides."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from packages import build as toolkit

PLAN = 'downloads/workbenches/catalog.json'


def build(output):
    if not output.is_absolute() or output.exists() or output.is_relative_to(ROOT) or not output.parent.is_dir():
        raise ValueError('NEW_EXTERNAL_OUTPUT_REQUIRED')
    revision = toolkit.git('rev-parse', 'HEAD').decode().strip()
    plan = json.loads(toolkit.git('show', revision + ':' + PLAN))
    if plan['repository'] != 'TheOutlandsDev/outlands-public-tools' or {a['id'] for a in plan['applications']} != {'sql-report-workbench', 'developer-workspace'}:
        raise ValueError('EXACT_APPLICATION_PLAN_REQUIRED')
    source = toolkit.public_tree(plan['source_revision']); records = []
    output.mkdir()
    for app in plan['applications']:
        name = app['id']; prefix = 'systems/' + name + '/'
        original = {p[len(prefix):]: raw for p, raw in source.items() if p.startswith(prefix)}
        manifest = json.loads(original['SOURCE-MANIFEST.json'])
        if manifest['format'] != 'outlands-source-inventory-v1' or set(original) != set(manifest['files']) | {'SOURCE-MANIFEST.json'}:
            raise ValueError('EXACT_APPLICATION_INVENTORY_REQUIRED')
        for path, row in manifest['files'].items():
            if row != dict(bytes=len(original[path]), sha256=toolkit.digest(original[path])):
                raise ValueError('APPLICATION_SOURCE_PIN_MISMATCH')
            original[path].decode('utf-8')
        version = app['package_version']; stem = name + '-' + version
        files = {'application/' + p: b for p, b in original.items()}
        for guide in ('START-HERE.md', 'PROVENANCE.md'):
            files[guide] = toolkit.git('show', revision + ':downloads/workbenches/' + name + '/' + guide)
        pinned = dict(schema=1, package=name, package_version=version, application_version=app['application_version'],
                      source_revision=plan['source_revision'], packaging_revision=revision,
                      files={p: dict(bytes=len(b), sha256=toolkit.digest(b)) for p, b in sorted(files.items())})
        files['PACKAGE-MANIFEST.json'] = toolkit.encode(pinned)
        data = toolkit.zip_bytes(files, stem); toolkit.verify_archive(data)
        filename=stem+'.zip'; (output/filename).write_bytes(data)
        records.append(dict(app=name,version=version,application_version=app['application_version'],tag=name+'-v'+version,
                            source_revision=plan['source_revision'],packaging_revision=revision,filename=filename,bytes=len(data),sha256=toolkit.digest(data),files=len(files)))
    (output/'release-matrix.json').write_bytes(toolkit.encode(dict(schema=1,applications=records)))
    (output/'SHA256SUMS.txt').write_bytes(''.join(toolkit.digest(p.read_bytes())+'  '+p.name+'\n' for p in sorted(output.iterdir())).encode())
    print(json.dumps(dict(status='PACKAGED',applications=records)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    build(p.parse_args().output)
