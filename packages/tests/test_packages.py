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
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('toolkit_builder', ROOT / 'packages/build.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

class Packages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='outlands-packaging-',dir=os.environ.get('OUTLANDS_TEST_TEMP'))
        cls.parent = Path(cls.scratch.name)
        cls.output = cls.parent / 'downloads'
        builder.build(cls.output)
        cls.catalog = json.loads((cls.output / 'catalog.json').read_text(encoding='utf-8'))
        cls.source = builder.public_tree(cls.catalog['source_revision'])

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def archive(self, name='release-qa'):
        record = next(x for x in self.catalog['downloads'] if x['id'] == name)
        return (self.output / record['filename']).read_bytes()

    def mutate(self, mutation):
        with zipfile.ZipFile(io.BytesIO(self.archive())) as archive:
            files = {p.split('/', 1)[1]: archive.read(p) for p in archive.namelist()}
        mutation(files)
        return builder.zip_bytes(files, 'fictional-package')

    def test_every_tool_exactly_once_and_all_systems_present(self):
        builder.validate_catalog(self.catalog, self.source)
        names = [n for g in self.catalog['groups'] for n in g['tools']]
        self.assertEqual(110, len(names))
        self.assertEqual(17, len(self.catalog['systems']))
        self.assertEqual('75c65911953af8eb4319f734471dddc9ca256ccd',self.catalog['source_revision'])
        self.assertEqual(127,len(self.catalog['components']))
        self.assertIn('import-migration-workbench',self.catalog['systems'])
        self.assertIn('document-template-workbench',self.catalog['systems'])
        self.assertIn('environment-setup-workbench',self.catalog['systems'])
        self.assertIn('release-update-workbench',self.catalog['systems'])
        self.assertEqual(9, len(self.catalog['downloads']))

    def test_new_workbenches_run_their_complete_fictional_demos_from_fresh_zip(self):
        unpack=self.parent/'new-workbench-unpack';unpack.mkdir()
        with zipfile.ZipFile(io.BytesIO(self.archive('complete'))) as archive:archive.extractall(unpack)
        package=next(unpack.iterdir())
        expected={
            'corpus-model-workbench':dict(benchmark_runs=6,discussion_turns=4,real_inference_verified=False,generated_code_executed=False),
            'environment-setup-workbench':dict(profiles=2,evaluations=2,plans=1,checks=9,blocked_steps_before=3,blocked_steps_after=0,private_report_files=6,plan_only=True,programs_executed=False),
            'release-update-workbench':dict(candidates=2,comparisons=2,plans=1,blockers_before=5,blockers_after=0,private_report_files=8,target_updates_performed=False,programs_executed=False),
            'test-evidence-workbench':dict(cases=4,matched=2,unmatched=2,timeouts=1,private_export_files=13,backup_validated=True,original_operational_checks_executed=False),
            'assessment-evidence-workbench':dict(versions=8,submissions=2,finding_state='Resolved',backup_validated=True,execution_performed=False),
            'reliability-incident-workbench':dict(snapshots=10,private_export_files=9,backup_validated=True,network_probed=False,execution_performed=False),
            'import-migration-workbench':dict(plans=3,imports=1,input_rows=7,accepted_rows=3,duplicate_rows=2,rejected_rows=2,provenance_rows=5,repeat_import_refused=True,conflict_import_refused=True,source_files_changed=False),
            'document-template-workbench':dict(templates=2,previews=2,builds=2,total_quantity=7,document_parts=8,external_relationships=0,existing_documents_overwritten=False),
            'backup-recovery-workbench':dict(snapshots=2,files_per_snapshot=3,snapshot_bytes=39,restored_bytes=39,private_report_files=7,index_backup_verified=True,deletion_performed=False,source_files_changed=False)}
        for name,fields in expected.items():
            source=package/'systems'/name;workspace=self.parent/('fictional-'+name)
            result=subprocess.run([sys.executable,'-B',str(source/'workbench.py'),'--workspace',str(workspace),'demo'],cwd=source,capture_output=True,text=True,encoding='utf-8',timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            self.assertEqual(0,result.returncode,name+': '+result.stderr)
            observed=json.loads(result.stdout)
            for field,value in fields.items():self.assertEqual(value,observed[field],name+': '+field)
            self.assertTrue(observed['mode'].startswith('FICTIONAL_'))

    def test_lifecycle_exercises_use_fresh_complete_zip_and_refuse_existing_state(self):
        unpack=self.parent/'lifecycle-unpack';unpack.mkdir()
        with zipfile.ZipFile(io.BytesIO(self.archive('complete'))) as archive:archive.extractall(unpack)
        package=next(unpack.iterdir());workspace=self.parent/'lifecycle-exercises'
        args=[sys.executable,'-I','-B',str(package/'workshops/lifecycle_exercises.py'),'--workspace',str(workspace)]
        result=subprocess.run(args,cwd=package,capture_output=True,text=True,encoding='utf-8',timeout=240)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr);observed=json.loads(result.stdout)
        self.assertEqual(53,observed['command_checks']);self.assertEqual(2,observed['exercises_passed']);self.assertTrue(observed['fictional_target_unchanged'])
        self.assertEqual([3,0],[observed['exercises']['setup']['blocked_steps_before'],observed['exercises']['setup']['blocked_steps_after']])
        update=observed['exercises']['updates'];self.assertEqual(dict(ADD=1,REMOVE=1,REPLACE=2,UNCHANGED=1),update['file_counts'])
        self.assertTrue(update['revoked_export_refused']);self.assertFalse(update['new_plan_inherits_approval']);self.assertFalse(update['target_updates_performed'])
        before={p.relative_to(workspace):builder.digest(p.read_bytes()) for p in workspace.rglob('*') if p.is_file()}
        repeat=subprocess.run(args,cwd=package,capture_output=True,timeout=30);self.assertEqual(1,repeat.returncode)
        self.assertEqual(before,{p.relative_to(workspace):builder.digest(p.read_bytes()) for p in workspace.rglob('*') if p.is_file()})

    def test_two_system_exercises_run_from_complete_zip_and_refuse_existing_state(self):
        unpack=self.parent/'system-exercises-unpack';unpack.mkdir()
        with zipfile.ZipFile(io.BytesIO(self.archive('complete'))) as archive:archive.extractall(unpack)
        package=next(unpack.iterdir());workspace=self.parent/'two-system-exercises'
        args=[sys.executable,'-I','-B',str(package/'workshops/system_exercises.py'),'--workspace',str(workspace)]
        result=subprocess.run(args,cwd=package,capture_output=True,text=True,timeout=180)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr);observed=json.loads(result.stdout)
        self.assertEqual(2,observed['exercises_passed']);self.assertEqual(33,observed['command_checks'])
        migration=observed['exercises']['imports'];document=observed['exercises']['documents']
        self.assertEqual([3,7,0],migration['quantities']);self.assertEqual(5,migration['provenance_rows'])
        self.assertTrue(migration['conflict_refused']);self.assertTrue(migration['existing_store_unchanged'])
        self.assertEqual(2,document['documents']);self.assertEqual(7,document['total_quantity'])
        self.assertTrue(document['original_document_unchanged']);self.assertTrue(document['unreviewed_build_refused'])
        before={p.relative_to(workspace).as_posix():builder.digest(p.read_bytes()) for p in workspace.rglob('*') if p.is_file()}
        refused=subprocess.run(args,cwd=package,capture_output=True,text=True,timeout=30)
        self.assertEqual(1,refused.returncode)
        self.assertEqual(before,{p.relative_to(workspace).as_posix():builder.digest(p.read_bytes()) for p in workspace.rglob('*') if p.is_file()})

    def test_ingestion_evidence_uses_fresh_zip_and_preserves_existing_workspace(self):
        unpack=self.parent/'ingestion-unpack';unpack.mkdir()
        with zipfile.ZipFile(io.BytesIO(self.archive('complete'))) as archive:archive.extractall(unpack)
        package=next(unpack.iterdir());workspace=self.parent/'ingestion-evidence'
        args=[sys.executable,'-B',str(package/'workshops/ingestion_evidence.py'),'--workspace',str(workspace)]
        result=subprocess.run(args,cwd=package,capture_output=True,text=True,timeout=180)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr);value=json.loads(result.stdout)
        self.assertEqual([23,6,4,2,1,1,9],[value[k] for k in ('command_checks','source_rows','accepted_records','duplicate_rows','matched','unmatched','private_export_files')])
        self.assertTrue(all(value[k] for k in ('mapping_change_requires_review','altered_receipt_pin_caught','missing_coverage_withholds_totals','independent_raw_capture_and_export_hashes','original_inputs_unchanged','review_does_not_change_verdict')))
        self.assertTrue(all(value[k] is False for k in ('import_performed','actual_store_contents_verified','exactly_once_verified','execution_sandbox','descendant_containment','publication_authorized')))
        before={p.relative_to(workspace).as_posix():builder.digest(p.read_bytes()) for p in workspace.rglob('*') if p.is_file()}
        refused=subprocess.run(args,cwd=package,capture_output=True,text=True,timeout=30)
        self.assertEqual(1,refused.returncode)
        self.assertEqual(before,{p.relative_to(workspace).as_posix():builder.digest(p.read_bytes()) for p in workspace.rglob('*') if p.is_file()})

    def test_manufacturing_review_fresh_zip_pins_arithmetic_and_refuses_existing_state(self):
        unpack=self.parent/'manufacturing-unpack';unpack.mkdir()
        with zipfile.ZipFile(io.BytesIO(self.archive('complete'))) as archive:archive.extractall(unpack)
        package=next(unpack.iterdir());workspace=self.parent/'manufacturing-review'
        args=[sys.executable,'-B',str(package/'workshops/manufacturing_review.py'),'--workspace',str(workspace)]
        result=subprocess.run(args,cwd=package,capture_output=True,text=True,encoding='utf-8',timeout=120)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr);value=json.loads(result.stdout)
        self.assertEqual([12,4,2,3,3,2,21],[value[k] for k in ('command_checks','expected_review_outcomes','eligible_before','eligible_after','peak_units_before','peak_units_after','total_closing')])
        self.assertEqual(dict(elapsed_ticks=12,active_ticks=9,hold_ticks=3,hold_count=1),value['duration_ticks'])
        self.assertEqual('REQUIRED',value['operator_review']);self.assertTrue(value['individual_eligibility_does_not_prove_combined_capacity']);self.assertTrue(value['duplicates_do_not_inflate'])
        for receipt in value['receipts']:
            for kind in ('input','report'):self.assertEqual(receipt[kind+'_sha256'],builder.digest((workspace/(receipt['case']+'-'+kind+'.json')).read_bytes()))
        self.assertTrue(all(value[k] is False for k in ('work_assigned','reservations_changed','schedule_optimized','balances_changed','physical_quantities_verified','qualifications_certified','live_clock_used','execution_authorized','publication_authorized')))
        before={p.relative_to(workspace):builder.digest(p.read_bytes()) for p in workspace.rglob('*') if p.is_file()}
        refused=subprocess.run(args,cwd=package,capture_output=True,text=True,timeout=30)
        self.assertEqual(1,refused.returncode);self.assertEqual({'error':'NEW_EXTERNAL_WORKSPACE_REQUIRED'},json.loads(refused.stdout))
        self.assertEqual(before,{p.relative_to(workspace):builder.digest(p.read_bytes()) for p in workspace.rglob('*') if p.is_file()})

    def test_material_quality_review_fresh_zip_independent_receipts_and_preservation(self):
        unpack=self.parent/'material-quality-unpack';unpack.mkdir()
        with zipfile.ZipFile(io.BytesIO(self.archive('complete'))) as archive:archive.extractall(unpack)
        package=next(unpack.iterdir());workspace=self.parent/'material-quality-review'
        args=[sys.executable,'-I','-B',str(package/'workshops/material_quality_review.py'),'--workspace',str(workspace)]
        result=subprocess.run(args,cwd=package,capture_output=True,text=True,encoding='utf-8',timeout=120)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr);value=json.loads(result.stdout)
        self.assertEqual([24,13,4,4,8,1,1,4,2,3,5,1],[value[k] for k in ('command_checks','expected_review_outcomes','kits','motor_requirement','filter_requirement','overreserved_motor_units','filter_shortage_before','accepted_receipt_quantity','initial_within_limits','later_within_limits','inspection_attempts','rework_events')])
        self.assertEqual(dict(eventual_yield='3/4',first_pass_yield='1/2',pending_fraction='0/1',scrap_fraction='1/4'),value['exact_fractions'])
        self.assertEqual('REQUIRED',value['operator_review']);self.assertEqual(4,value['final_counts']['cohort'])
        for receipt in value['receipts']:
            for kind in ('input','report'):self.assertEqual(receipt[kind+'_sha256'],builder.digest((workspace/(receipt['case']+'-'+kind+'.json')).read_bytes()))
        mapping=json.loads((workspace/'authored-mapping.json').read_bytes())
        self.assertEqual(value['mapping_sha256'],builder.digest((workspace/'authored-mapping.json').read_bytes()))
        self.assertEqual(mapping['rework_report_sha256'],builder.digest((workspace/'rework-reviewed-report.json').read_bytes()))
        selected=json.loads((workspace/'inspections-selected-later-input.json').read_bytes())
        pin=builder.digest((workspace/'measurements-selected-later-report.json').read_bytes())
        self.assertTrue(all(row['source_sha256']==pin for row in selected['records']))
        for key in ('orders_created','stock_changed','reservations_changed','transfers_performed','inspections_performed','rework_performed','physical_traceability_verified','quality_target_evaluated','execution_authorized','publication_authorized'):self.assertFalse(value[key])
        before={p.relative_to(workspace):builder.digest(p.read_bytes()) for p in workspace.rglob('*') if p.is_file()}
        repeat=subprocess.run(args,cwd=package,capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(1,repeat.returncode);self.assertEqual({'error':'NEW_EXTERNAL_WORKSPACE_REQUIRED'},json.loads(repeat.stdout))
        self.assertEqual(before,{p.relative_to(workspace):builder.digest(p.read_bytes()) for p in workspace.rglob('*') if p.is_file()})

    def test_independent_release_checker_rejects_changed_outer_asset(self):
        script=ROOT/'packages/release_check.py'
        good=subprocess.run([sys.executable,'-B',str(script),'--output',str(self.output)],capture_output=True,text=True,timeout=60)
        self.assertEqual(0,good.returncode,good.stderr)
        changed=self.parent/'altered-assets';changed.mkdir()
        for p in self.output.iterdir():(changed/p.name).write_bytes(p.read_bytes())
        (changed/'catalog.json').write_bytes((changed/'catalog.json').read_bytes()+b' ')
        bad=subprocess.run([sys.executable,'-B',str(script),'--output',str(changed)],capture_output=True,text=True,timeout=60)
        self.assertNotEqual(0,bad.returncode)
        self.assertIn('RELEASE_CHECKSUM_MISMATCH',bad.stderr)

    def test_missing_and_duplicate_components_refused(self):
        for mode in ('missing', 'duplicate'):
            bad = copy.deepcopy(self.catalog)
            if mode == 'missing': bad['groups'][0]['tools'].pop()
            else: bad['groups'][0]['tools'].append(bad['groups'][0]['tools'][0])
            with self.assertRaisesRegex(ValueError, 'TOOL_COVERAGE_MISMATCH'):
                builder.validate_catalog(bad, self.source)

    def test_all_manifests_and_preserved_public_bytes(self):
        for record in self.catalog['downloads']:
            body = (self.output / record['filename']).read_bytes()
            manifest = builder.verify_archive(body)
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                prefix = archive.namelist()[0].split('/')[0] + '/'
                for path, entry in manifest['files'].items():
                    if entry['origin'] == 'published-source':
                        self.assertEqual(self.source[path], archive.read(prefix + path))
            self.assertEqual(record['sha256'], builder.digest(body))

    def test_complete_contains_every_source_file(self):
        manifest = builder.verify_archive(self.archive('complete'))
        self.assertTrue(set(self.source).issubset(manifest['files']))

    def test_windows_checkout_conversion_cannot_change_source_objects(self):
        original = builder.git
        with patch.object(builder, 'git', side_effect=lambda *args: original('-c', 'core.autocrlf=true', *args)):
            alternate = builder.public_tree(self.catalog['source_revision'])
        self.assertEqual(self.source, alternate)
        with zipfile.ZipFile(io.BytesIO(self.archive('complete'))) as archive:
            prefix = archive.namelist()[0].split('/')[0] + '/'
            modes = {name: mode for name, mode, _ in builder.git_entries(self.catalog['source_revision'])}
            for path, mode in modes.items():
                self.assertEqual(int(mode, 8), archive.getinfo(prefix + path).external_attr >> 16)

    def test_family_does_not_include_other_tool_implementations(self):
        for group in self.catalog['groups']:
            manifest = builder.verify_archive(self.archive(group['id']))
            found = {p.split('/')[1] for p in manifest['files'] if p.startswith('tools/')}
            self.assertEqual(set(group['tools']), found)

    def test_recomputed_crc_cannot_hide_changed_file(self):
        def change(files): files['START-HERE.md'] += b'changed fictional marker\n'
        with self.assertRaisesRegex(ValueError, 'FILE_HASH_MISMATCH'):
            builder.verify_archive(self.mutate(change))

    def test_unlisted_file_refused(self):
        with self.assertRaisesRegex(ValueError, 'INVENTORY_MISMATCH'):
            builder.verify_archive(self.mutate(lambda files: files.update({'unexpected.txt': b'fictional'})))

    def test_missing_file_refused(self):
        with self.assertRaisesRegex(ValueError, 'INVENTORY_MISMATCH'):
            builder.verify_archive(self.mutate(lambda files: files.pop('START-HERE.md')))

    def test_unsafe_paths_refused(self):
        for path in ('../outside', '/absolute', 'a\\b', 'C:/sample', 'a/.git/config', 'a/__pycache__/x'):
            with self.subTest(path=path), self.assertRaises(ValueError): builder.safe_name(path)

    def test_archive_is_deterministic_across_input_order(self):
        one = builder.zip_bytes({'b.txt': b'b', 'a.txt': b'a'}, 'demo')
        two = builder.zip_bytes({'a.txt': b'a', 'b.txt': b'b'}, 'demo')
        self.assertEqual(one, two)
        with zipfile.ZipFile(io.BytesIO(one)) as archive:
            self.assertTrue(all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in archive.infolist()))

    def test_existing_output_refused(self):
        with self.assertRaisesRegex(ValueError, 'NEW_EXTERNAL_OUTPUT_REQUIRED'):
            builder.build(self.output)

    def test_relative_external_output_is_resolved_before_boundary_check(self):
        with tempfile.TemporaryDirectory(prefix='outlands-relative-', dir=ROOT.parent) as scratch:
            destination = Path(scratch) / 'relative-output'
            builder.build(os.path.relpath(destination, ROOT))
            self.assertTrue((destination / 'SHA256SUMS.txt').is_file())

    def test_uncommitted_control_text_is_not_a_package_input(self):
        with patch.object(Path, 'read_text', side_effect=AssertionError('Working-tree text is not a release input')):
            builder.build(self.parent / 'committed-controls-only')

    def test_fresh_archive_runs_actual_fictional_workflows(self):
        for name in ('complete', 'release-qa'):
            unpack = self.parent / ('unpacked-' + name); unpack.mkdir()
            with zipfile.ZipFile(io.BytesIO(self.archive(name))) as archive: archive.extractall(unpack)
            package = next(unpack.iterdir())
            result = subprocess.run([sys.executable, '-I', '-B', str(package / 'methodology/worked-examples/run_examples.py'),
                                     '--workspace', str(self.parent / ('examples-' + name))],
                                    cwd=package, capture_output=True, text=True, timeout=120)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual(3, receipt['examples_passed'])
            self.assertEqual(8, receipt['command_checks'])
            second = subprocess.run([sys.executable, '-I', '-B', str(package / 'methodology/worked-examples/run_examples.py'),
                                     '--workspace', str(self.parent / ('examples-' + name))],
                                    cwd=package, capture_output=True, text=True, timeout=20)
            self.assertEqual(1, second.returncode)

    def test_every_family_runs_its_workshop_from_a_fresh_archive(self):
        total = 0
        for group in self.catalog['groups']:
            family = group['id']; unpack = self.parent / ('workshop-unpack-' + family); unpack.mkdir()
            with zipfile.ZipFile(io.BytesIO(self.archive(family))) as archive: archive.extractall(unpack)
            package = next(unpack.iterdir()); workspace = self.parent / ('workshop-run-' + family)
            result = subprocess.run([sys.executable, '-I', '-B', str(package / 'workshops/run.py'),
                                     '--family', family, '--workspace', str(workspace)],
                                    cwd=package, capture_output=True, text=True, timeout=120)
            self.assertEqual(0, result.returncode, family + ': ' + result.stdout + result.stderr)
            receipt = json.loads((workspace / 'observed-results.json').read_text(encoding='utf-8'))
            self.assertEqual('PASS', receipt['status']); total += receipt['command_checks']
        self.assertEqual(33, total)

if __name__ == '__main__': unittest.main()
