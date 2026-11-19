"""Exercise readiness JSON as a saved diagnostic for the incident bundle CLI."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def run_cli(source: Path, *args: str) -> bytes:
    result = subprocess.run(
        [sys.executable, '-B', '-m', 'opskit', *args],
        cwd=source, check=True, capture_output=True, timeout=30,
    )
    if result.stderr:
        raise RuntimeError('Unexpected CLI diagnostics during fictional round trip')
    return result.stdout


def check(incident_tool: Path) -> None:
    observation = ROOT / 'examples' / 'pass.json'
    result = run_cli(ROOT, 'doctor', '--observations', str(observation), '--json')
    doctor = json.loads(result)
    if doctor['command'] != 'doctor' or doctor['data']['status'] != 'pass':
        raise RuntimeError('Unexpected readiness result')
    with TemporaryDirectory(dir=Path.cwd()) as directory:
        workspace = Path(directory).resolve()
        saved = workspace / 'doctor.json'
        saved.write_bytes(result)
        fixture_paths = {}
        for name in ('inventory', 'ports'):
            source = incident_tool / 'examples' / f'{name}.json'
            fixture_paths[name] = workspace / source.name
            fixture_paths[name].write_bytes(source.read_bytes())
        bundle = workspace / 'fictional-incident.zip'
        run_cli(
            incident_tool, '--home', str(workspace), 'incident', 'bundle',
            '--doctor', saved.name, '--inventory', fixture_paths['inventory'].name,
            '--ports', fixture_paths['ports'].name, '--output', str(bundle), '--json',
        )
        with ZipFile(bundle) as archive:
            members = {'doctor.json', 'inventory.json', 'ports.json'}
            if len(archive.namelist()) != 4 or set(archive.namelist()) != members | {'manifest.json'}:
                raise RuntimeError('Unexpected fictional incident ZIP layout')
            data = archive.read('doctor.json')
            if json.loads(data) != doctor:
                raise RuntimeError('Saved readiness report did not survive bundling')
            manifest = json.loads(archive.read('manifest.json'))
            recorded = {row['name']: row for row in manifest['files']}
            if recorded.keys() != members or len(manifest['files']) != len(members):
                raise RuntimeError('Fictional incident ZIP manifest is incomplete')
            for name, record in recorded.items():
                member = archive.read(name)
                if record['sha256'] != sha256(member).hexdigest() or record['bytes'] != len(member):
                    raise RuntimeError('Fictional incident ZIP digest did not match the manifest')
        if saved.read_bytes() != result:
            raise RuntimeError('Bundle builder changed the saved doctor report')


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--incident-tool', required=True, type=Path)
    options = parser.parse_args()
    check(options.incident_tool.resolve(strict=True))
    print('Incident evidence bundle round trip passed.')
