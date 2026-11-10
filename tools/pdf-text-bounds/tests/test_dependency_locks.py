"""Validate lock-to-wheel provenance and exact installed test/runtime contracts."""
from pathlib import Path
import importlib.metadata
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DependencyLocks(unittest.TestCase):
    def test_exact_runtime_and_dev_hashes_match_reviewed_pypi_wheels(self):
        wheel_record = json.loads((ROOT / 'docs/WHEELS.json').read_text())
        dependency_record = json.loads((ROOT / 'docs/DEPENDENCIES.json').read_text())
        self.assertEqual(len(wheel_record['packages']), 9)
        records = {row['name']: row for row in dependency_record['packages']}
        for row in wheel_record['packages']:
            with self.subTest(package=row['name']):
                self.assertEqual(row['version'], records[row['name']]['version'])
                self.assertEqual(importlib.metadata.version(row['name']), row['version'])
                lock = 'requirements.lock.txt' if row['scope'] == 'runtime' else 'requirements-dev.lock.txt'
                text = (ROOT / lock).read_text()
                section = text.split(row['name'] + '==' + row['version'] + ' ', 1)[1].split('\n\n', 1)[0]
                hashes = re.findall(r'--hash=sha256:([a-f0-9]{64})', section)
                self.assertEqual(set(hashes), {f['sha256'] for f in row['files']})
                self.assertEqual(len(hashes), len(set(hashes)))

if __name__ == '__main__': unittest.main()
