"""Exercise actual CLIs, retained failures, exact hashes and immutable prior runs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('software_quality', ROOT / 'workshops/software_quality_review.py')
workshop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workshop)


class SoftwareQuality(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='software-quality-')
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name) / 'run'

    def test_actual_ten_calls_keep_five_reviews_and_exact_bytes(self):
        result = workshop.run(self.target)
        self.assertEqual((result['status'], result['command_checks'], result['expected_review_outcomes']),
                         ('PASS', 10, 5))
        self.assertEqual(sum(r['observed_status'] == 'REVIEW_REQUIRED' for r in result['results']), 5)
        self.assertTrue(result['original_sources_unchanged'])
        self.assertFalse(result['browser_application_tested'])
        for row in result['results']:
            for folder, key in [('inputs', 'input_sha256'), ('reports', 'report_sha256')]:
                self.assertEqual(workshop.digest((self.target / folder / (row['id'] + '.json')).read_bytes()), row[key])
        before = {p.relative_to(self.target).as_posix(): p.read_bytes()
                  for p in self.target.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError, 'NEW_ABSOLUTE_EXTERNAL_WORKSPACE_REQUIRED'):
            workshop.run(self.target)
        self.assertEqual(before, {p.relative_to(self.target).as_posix(): p.read_bytes()
                                for p in self.target.rglob('*') if p.is_file()})

    def test_unexpected_child_verdict_preserves_report_without_success(self):
        name, kind, payload, _ = workshop.fixtures()[0]
        with patch.object(workshop, 'fixtures', return_value=[(name, kind, payload, True)]):
            with self.assertRaisesRegex(ValueError, 'CLI_CHECK_FAILED'):
                workshop.run(self.target)
        self.assertFalse((self.target / 'result.json').exists())
        report = json.loads((self.target / 'reports' / (name + '.json')).read_bytes())
        self.assertEqual(report['status'], 'REVIEW_REQUIRED')

    def test_stale_hash_cannot_count_as_an_expected_type_failure(self):
        name, kind, payload, good = workshop.fixtures()[0]
        payload['submissions'][0]['form_sha256'] = '0' * 64
        with patch.object(workshop, 'fixtures', return_value=[(name, kind, payload, good)]):
            with self.assertRaisesRegex(ValueError, 'ASSESSMENT_WITHHELD'):
                workshop.run(self.target)
        self.assertFalse((self.target / 'result.json').exists())
        self.assertTrue((self.target / 'reports' / (name + '.json')).is_file())

    def test_source_destination_and_relative_destination_are_refused(self):
        for path in [ROOT / 'not-created-workshop', Path('not-created-workshop')]:
            with self.subTest(path=str(path)), self.assertRaises(ValueError):
                workshop.run(path)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
