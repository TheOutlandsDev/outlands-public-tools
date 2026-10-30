"""Invented records and a tiny invented ZIP; never clean-Windows acceptance proof."""
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / 'manufacturing_desktop_gate.py'
spec = importlib.util.spec_from_file_location('desktop_gate_fixture_target', SCRIPT)
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


class DesktopEvidenceGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.candidate = self.root / 'candidate'; self.candidate.mkdir()
        self.evidence = self.root / 'evidence'; self.evidence.mkdir()
        self.run = self.evidence / 'native checks/private/fresh manual run'; self.run.mkdir(parents=True)
        self.policy = dict(g.POLICY, kind='fictional-fixture')
        manifest = dict(source_revision=self.policy['source_revision'], runtime=self.policy['runtime'],
                        source_zip_sha256=self.policy['source_zip_sha256'], packaging_revision=self.policy['packaging_revision'])
        manifest_raw = encoded(manifest)
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr(self.policy['prefix'] + 'PACKAGE-MANIFEST.json', manifest_raw)
            z.writestr(self.policy['prefix'] + 'FIXTURE-ONLY.txt', 'Invented fixture. No executable or runtime.')
        raw = archive.getvalue(); self.policy['package_sha256'] = g.sha(raw)
        (self.candidate / self.policy['filename']).write_bytes(raw)
        receipt = dict(schema=1, filename=self.policy['filename'], sha256=g.sha(raw),
            source_revision=self.policy['source_revision'], packaging_revision=self.policy['packaging_revision'],
            source_zip_sha256=self.policy['source_zip_sha256'], runtime=self.policy['runtime'],
            tools=12, exercises=2, expected_cli_calls=36, expected_review_outcomes=17)
        receipt_raw = encoded(receipt); self.policy['receipt_sha256'] = g.sha(receipt_raw)
        (self.candidate / 'release-receipt.json').write_bytes(receipt_raw)
        self.write('preflight-private.json', dict(scope=g.PREFLIGHT_SCOPE, commands=[], registered_interpreters=[],
            errors=[], windows='11', architecture='AMD64', system_python_executed=False, software_removed=False))
        self.write('qualification-summary.json', dict(status='NATIVE_ACCEPTANCE_PASS_AWAITING_OPERATOR_CONFIRMATION',
            package_sha256=self.policy['package_sha256'], packaging_revision=self.policy['packaging_revision'],
            native_checks=8, cli_checks=36, expected_review_outcomes=17, browser_tested_here=False,
            clean_windows_provenance='NOT_AUTOMATICALLY_ESTABLISHED', preflight_scope=g.PREFLIGHT_SCOPE,
            publication_authorized_by_this_file=False, raw_private_runs_uploaded=False))
        self.write('packages/acceptance.json', dict(schema=1, status='PASS', package_sha256=self.policy['package_sha256'],
            source_revision=self.policy['source_revision'], packaging_revision=self.policy['packaging_revision'],
            runtime=self.policy['runtime'], browser=False, browser_checks=0, cli_checks=36, expected_review_outcomes=17,
            captures={}, video={}, source_files_changed=False, system_python_required=False,
            physical_operations_performed=False, clean_windows_verification_separate=True, checks=sorted(g.NATIVE_CHECKS)))
        exercises = {}
        for name, count, reviews in (('capacity', 12, 4), ('material-quality', 24, 13)):
            receipts = []
            for i in range(count):
                case = 'fictional-' + str(i)
                row = dict(case=case, exit_code=int(i < reviews))
                for kind in ('input', 'report'):
                    data = encoded(dict(fictional_fixture_only=True, number=i, kind=kind))
                    p = self.run / name / (case + '-' + kind + '.json'); p.parent.mkdir(exist_ok=True); p.write_bytes(data)
                    row[kind + '_sha256'] = g.sha(data)
                receipts.append(row)
            exercises[name] = dict(status='PASS', command_checks=count, expected_review_outcomes=reviews,
                operator_review='REQUIRED', original_inputs_unchanged=True, report_hashes_recomputed=True,
                execution_authorized=False, publication_authorized=False, receipts=receipts)
        exercises['capacity'].update(eligible_before=2, eligible_after=3, peak_units_before=3,
            peak_units_after=2, total_closing=21, duration_ticks=dict(elapsed_ticks=12, active_ticks=9, hold_ticks=3, hold_count=1))
        mapping = encoded(dict(fictional_fixture_only=True)); (self.run / 'material-quality/authored-mapping.json').write_bytes(mapping)
        exercises['material-quality'].update(kits=4, motor_requirement=4, filter_requirement=8,
            overreserved_motor_units=1, filter_shortage_before=1, initial_within_limits=2, later_within_limits=3,
            inspection_attempts=5, rework_events=1, mapping_sha256=g.sha(mapping),
            final_counts=dict(closed_cohort=True, cohort=4, first_pass_good=2, good=3, pending=0, reworked_good=1, scrap=1),
            exact_fractions=dict(eventual_yield='3/4', first_pass_yield='1/2', pending_fraction='0/1', scrap_fraction='1/4'))
        self.result = dict(schema=1, status='PASS', mode='FICTIONAL_MANUFACTURING_REVIEW_DEMO', version='0.1.0',
            command_checks=36, expected_review_outcomes=17, operator_review='REQUIRED',
            source_revision=self.policy['source_revision'], packaging_revision=self.policy['packaging_revision'],
            bundle_manifest_sha256=g.sha(manifest_raw), network_required=False, physical_operations_performed=False,
            publication_authorized=False, runtime=dict(runtime=self.policy['runtime'], bundled_runtime=True,
                isolated=True, user_site_disabled=True, external_import_paths=False, executable='runtime/python.exe'), exercises=exercises)
        (self.run / 'report.html').write_text('<p>FICTIONAL FIXTURE ONLY. No Windows execution.</p>')
        self.save_result(); self.complete_operator_fixture()

    def write(self, name, value):
        p = self.evidence / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(encoded(value))

    def read(self, name):
        return json.loads((self.evidence / name).read_bytes())

    def save_result(self):
        (self.run / 'result.json').write_bytes(encoded(self.result))
        for name, value in self.result['exercises'].items():
            (self.run / name / 'observed-results.json').write_bytes(encoded(value))
        self.rehash_run()

    def rehash_run(self):
        files = {p.relative_to(self.run).as_posix(): dict(bytes=p.stat().st_size, sha256=g.sha(p.read_bytes()))
                 for p in self.run.rglob('*') if p.is_file() and p.name != 'RUN-MANIFEST.json'}
        (self.run / 'RUN-MANIFEST.json').write_bytes(encoded(dict(schema=1, status='PASS',
            source_revision=self.policy['source_revision'], files=files)))

    def complete_operator_fixture(self):
        reader = g.Reader()
        bindings, _ = g.records(reader, self.candidate, self.evidence, self.policy)
        self.manual = dict(schema=1, kind='fictional-fixture', package_sha256=self.policy['package_sha256'],
            packaging_revision=self.policy['packaging_revision'], bindings=bindings,
            environment=dict(kind='fresh-windows-vm', fresh_windows_installation_confirmed=True,
                python_not_installed_before_packet=True, limited_preflight_scope_acknowledged=True),
            observations=copy.deepcopy(g.OBSERVATIONS), operator_affirms_personal_observation=True)
        self.write('operator-observations.json', self.manual)

    def check(self):
        return g.check(self.candidate, self.evidence, policy=self.policy)

    def test_complete_fictional_records_never_authorize_publication(self):
        result = self.check()
        self.assertEqual(result['status'], 'FIXTURE_VALIDATED')
        self.assertFalse(result['publication_authorized'])
        self.assertFalse(result['whole_disk_python_absence_proved'])
        self.assertFalse(result['execution_authenticity_proved'])
        self.assertEqual(result['operator_observations'], 'ASSERTED_NOT_INDEPENDENTLY_VERIFIED')
        self.assertEqual(result['expected_review_outcomes'], 17)

    def test_production_cli_rejects_fictional_candidate_without_private_path_output(self):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--candidate-dir', str(self.candidate),
                                 '--evidence-dir', str(self.evidence)], capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['code'], 'CANDIDATE_ZIP_MISMATCH')
        self.assertNotIn(str(self.root).encode(), result.stdout + result.stderr)

    def test_changed_zip_and_replaced_declared_receipt_cannot_change_the_pin(self):
        path = self.candidate / self.policy['filename']; path.write_bytes(path.read_bytes() + b'changed')
        receipt = json.loads((self.candidate / 'release-receipt.json').read_bytes()); receipt['sha256'] = g.sha(path.read_bytes())
        (self.candidate / 'release-receipt.json').write_bytes(encoded(receipt))
        with self.assertRaisesRegex(g.GateError, 'CANDIDATE_ZIP_MISMATCH'): self.check()

    def test_changed_receipt_is_refused_even_with_unchanged_zip(self):
        p = self.candidate / 'release-receipt.json'; p.write_bytes(p.read_bytes() + b' ')
        with self.assertRaisesRegex(g.GateError, 'CANDIDATE_RECEIPT_MISMATCH'): self.check()

    def test_preflight_commands_registrations_and_errors_each_block(self):
        original = self.read('preflight-private.json')
        for key in ('commands', 'registered_interpreters', 'errors'):
            with self.subTest(key=key):
                self.write('preflight-private.json', dict(original, **{key: ['FICTIONAL_PRIVATE_VALUE']}))
                with self.assertRaisesRegex(g.GateError, 'PREFLIGHT_NOT_CLEAR'): self.check()

    def test_each_named_native_check_is_required_without_duplicates(self):
        original = self.read('packages/acceptance.json')
        for i in range(8):
            with self.subTest(missing=i):
                value = copy.deepcopy(original); value['checks'][i] = value['checks'][(i + 1) % 8]
                self.write('packages/acceptance.json', value)
                with self.assertRaisesRegex(g.GateError, 'ALL_NATIVE_CHECKS_REQUIRED'): self.check()

    def test_native_summary_revision_and_runtime_must_match(self):
        value = self.read('qualification-summary.json'); value['packaging_revision'] = '0' * 40
        self.write('qualification-summary.json', value)
        with self.assertRaisesRegex(g.GateError, 'NATIVE_SUMMARY_MISMATCH'): self.check()

    def test_changed_report_and_unlisted_file_are_refused(self):
        (self.run / 'report.html').write_text('changed fixture')
        with self.assertRaisesRegex(g.GateError, 'RUN_FILE_HASH_MISMATCH'): self.check()
        (self.run / 'unexpected.txt').write_text('unlisted fixture')
        with self.assertRaisesRegex(g.GateError, 'RUN_INVENTORY_MISMATCH'): self.check()

    def test_recomputed_manifest_cannot_hide_receipt_tampering(self):
        (self.run / 'capacity/fictional-0-report.json').write_text('{"changed":true}')
        self.rehash_run()
        with self.assertRaisesRegex(g.GateError, 'RECEIPT_HASH_MISMATCH'): self.check()

    def test_recomputed_summaries_cannot_remove_expected_failures(self):
        self.result['exercises']['capacity']['receipts'][0]['exit_code'] = 0
        self.save_result()
        with self.assertRaisesRegex(g.GateError, 'EXPECTED_FAILURES_NOT_RETAINED'): self.check()

    def test_recomputed_summaries_cannot_substitute_boolean_for_numeric_outcome(self):
        self.result['exercises']['material-quality']['final_counts']['scrap'] = True
        self.save_result()
        with self.assertRaisesRegex(g.GateError, 'MATERIAL_ORACLE_MISMATCH'): self.check()

    def test_runtime_isolation_claim_is_required(self):
        self.result['runtime']['isolated'] = False; self.save_result()
        with self.assertRaisesRegex(g.GateError, 'RUN_RESULT_MISMATCH'): self.check()

    def test_missing_or_unfilled_observation_is_refused(self):
        for name in g.OBSERVATIONS:
            with self.subTest(observation=name):
                value = copy.deepcopy(self.manual); value['observations'][name] = None
                self.write('operator-observations.json', value)
                with self.assertRaisesRegex(g.GateError, 'OPERATOR_OBSERVATIONS_INCOMPLETE'): self.check()

    def test_environment_and_personal_observation_need_explicit_confirmation(self):
        for name in ('fresh_windows_installation_confirmed', 'python_not_installed_before_packet',
                     'limited_preflight_scope_acknowledged'):
            value = copy.deepcopy(self.manual); value['environment'][name] = False
            self.write('operator-observations.json', value)
            with self.assertRaisesRegex(g.GateError, 'OPERATOR_OBSERVATIONS_INCOMPLETE'): self.check()
        value = copy.deepcopy(self.manual); value['operator_affirms_personal_observation'] = False
        self.write('operator-observations.json', value)
        with self.assertRaisesRegex(g.GateError, 'OPERATOR_OBSERVATIONS_INCOMPLETE'): self.check()

    def test_observations_are_pinned_to_each_original_record(self):
        for name in self.manual['bindings']:
            value = copy.deepcopy(self.manual); value['bindings'][name] = '0' * 64
            self.write('operator-observations.json', value)
            with self.assertRaisesRegex(g.GateError, 'OPERATOR_OBSERVATIONS_INCOMPLETE'): self.check()

    def test_fixture_cannot_be_relabeled_as_observed_evidence(self):
        self.manual['kind'] = 'observed-private-run'; self.write('operator-observations.json', self.manual)
        with self.assertRaisesRegex(g.GateError, 'OPERATOR_OBSERVATIONS_INCOMPLETE'): self.check()

    def test_duplicate_nonfinite_and_unsafe_fields_are_refused(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(g.GateError): g.parse(raw)
        for path in ('../outside', '/absolute', 'a\\b', 'a//b', 'a/../b'):
            with self.assertRaises(g.GateError): g.relative(path)

    def test_hardlinks_size_limits_and_changed_reads_are_refused(self):
        original = self.root / 'ordinary'; original.write_bytes(b'fixture')
        alias = self.root / 'hardlink'; os.link(original, alias)
        with self.assertRaises(g.GateError): g.Reader().read(alias)
        other = self.root / 'other'; other.write_bytes(b'fixture')
        with self.assertRaises(g.GateError): g.Reader().read(other, limit=1)
        reader = g.Reader(); reader.read(other); other.write_bytes(b'changed-length')
        with self.assertRaises(g.GateError): reader.finish()

    def test_template_starts_unconfirmed_and_cannot_overwrite_an_existing_record(self):
        path = self.evidence / 'operator-observations.json'; path.unlink()
        result = g.check(self.candidate, self.evidence, policy=self.policy, prepare=True)
        self.assertEqual(result['status'], 'OBSERVATIONS_TEMPLATE_CREATED')
        value = self.read('operator-observations.json')
        self.assertTrue(all(v is None for v in value['observations'].values()))
        self.assertIsNone(value['operator_affirms_personal_observation'])
        before = path.read_bytes()
        with self.assertRaises(FileExistsError): g.check(self.candidate, self.evidence, policy=self.policy, prepare=True)
        self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
