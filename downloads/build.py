"""Build exact reviewed focused source ZIPs from committed Git blobs; stdlib only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APPS = [('local-site-builder', '1.0.2'), ('resource-monitor', '0.1.1')]

def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)
def sha(data): return hashlib.sha256(data).hexdigest()

def build(output):
    if not output.is_absolute(): raise ValueError('Absolute output required')
    output = output.resolve()
    if output == ROOT or ROOT in output.parents or output.exists(): raise ValueError('New external output required')
    output.mkdir()  # Existing parent required; no overwrite or cleanup.
    revision = git('rev-parse', 'HEAD').decode().strip()
    records = []
    for app, version in APPS:
        prefix = 'tools/' + app + '/'
        tracked = git('ls-tree', '-rz', 'HEAD', '--', prefix).split(b'\0')
        blobs = {}
        for row in filter(None, tracked):
            meta, name = row.split(b'\t', 1); mode, kind, object_id = meta.split()
            if kind != b'blob' or mode not in (b'100644', b'100755'): raise ValueError('Ordinary source files required')
            name = name.decode('utf-8')[len(prefix):]
            if not name or '\\' in name or '..' in name.split('/') or name.startswith('/'): raise ValueError('Unsafe source path')
            data = git('cat-file', 'blob', object_id.decode())
            if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != object_id.decode(): raise ValueError('Git object mismatch')
            if (ROOT / prefix / name).read_bytes() != data: raise ValueError('Commit reviewed app bytes before packaging: ' + name)
            blobs[name] = (data, mode)
        manifest = json.loads(blobs['SOURCE-MANIFEST.json'][0])
        if set(blobs) != {r['path'] for r in manifest['files']} | {'SOURCE-MANIFEST.json'}: raise ValueError('Exact app source allowlist required')
        for row in manifest['files']:
            data = blobs[row['path']][0]
            if len(data) != row['bytes'] or sha(data) != row['sha256']: raise ValueError('App manifest mismatch')
        if app == 'local-site-builder' and json.loads(blobs['package.json'][0])['version'] != version: raise ValueError('Version mismatch')
        if app == 'resource-monitor' and ('__version__ = "' + version + '"').encode() not in blobs['resource_monitor/__init__.py'][0]: raise ValueError('Version mismatch')
        filename = app + '-' + version + '.zip'; target = output / filename
        with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_STORED) as archive:
            for name, (data, mode) in sorted(blobs.items()):
                info = zipfile.ZipInfo(app + '-' + version + '/' + name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3; info.external_attr = int(mode, 8) << 16
                archive.writestr(info, data)
        data = target.read_bytes()
        records.append(dict(app=app, version=version, tag=app + '-v' + version, filename=filename, source_revision=revision,
                            bytes=len(data), sha256=sha(data), files=len(blobs)))
    matrix = (json.dumps(dict(schema=1, applications=records), indent=2) + '\n').encode()
    (output / 'release-matrix.json').write_bytes(matrix)
    checksums = ''.join(sha(p.read_bytes()) + '  ' + p.name + '\n' for p in sorted(output.iterdir()))
    (output / 'SHA256SUMS.txt').write_bytes(checksums.encode())
    print(json.dumps(dict(status='PACKAGED', applications=records)))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', required=True, type=Path)
    build(parser.parse_args().output)
