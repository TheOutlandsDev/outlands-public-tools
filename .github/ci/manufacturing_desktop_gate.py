"""Check frozen candidate/private desktop records; never authorize publication."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

POLICY = dict(kind='observed-private-run', filename='manufacturing-review-demo-0.1.0-windows-x64.zip',
    package_sha256='e91917577fad09083a0866d8cd49886337404e85d83fba2e4e2377f45c0864f9',
    receipt_sha256='be9cf739922bc3387311bc5532bd4ca055d45a6b3785a8c43a5253dc3e4c48e1',
    packaging_revision='87d9535d3855fac6fc4cc0d07c12dae762991bc6',
    source_revision='5ace0cacafe0874fa4db816a11c5cc0cf04089d2',
    source_zip_sha256='b7b8fb6ad1e36587bb0a744b7b43468093209dfb06657c254011a576f3d4bdcb',
    runtime='3.14.10', prefix='manufacturing-review-demo-0.1.0-windows-x64/')
PREFLIGHT_SCOPE = 'Command lookup and Python installation registry only; not a whole-disk absence proof.'
NATIVE_CHECKS = frozenset(('bundled_cmd_isolated_no_system_python_or_user_site',
    '36_original_cli_checks_17_expected_reviews', 'independent_receipt_hashes',
    'existing_run_refused_unchanged', 'saved_run_reopen_without_writes',
    'tampered_run_refused_without_writes', 'fresh_default_appdata_run', 'package_tree_unchanged'))
OBSERVATIONS = dict(explorer_extracted_to_new_local_folder=True,
    launcher_started_without_installer=True, offline_report_opened_in_desktop_browser=True,
    capacity_peak_before=3, capacity_peak_after=2, motor_units_reserved=5, motor_lot_stock=4,
    inspection_covered_before=3, inspection_covered_after=4, inspection_expected=4,
    first_pass_good=2, reworked_good=1, scrap=1, cohort=4,
    expected_review_outcomes_visible=True, saved_report_reopened_without_new_run=True)


class GateError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise GateError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def match(actual, expected, code):
    require(type(actual) is type(expected), code)
    if isinstance(expected, dict):
        require(set(expected) <= set(actual), code)
        for key, value in expected.items():
            match(actual[key], value, code)
    elif isinstance(expected, list):
        require(len(actual) == len(expected), code)
        for a, b in zip(actual, expected):
            match(a, b, code)
    else:
        require(actual == expected, code)


def parse(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def invalid(_):
        raise GateError('NONFINITE_JSON_VALUE')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise GateError('INVALID_JSON') from None
    require(type(value) is dict, 'JSON_OBJECT_REQUIRED')
    return value


def relative(name):
    require(type(name) is str and 0 < len(name) <= 240 and
            re.fullmatch(r'[A-Za-z0-9_. /-]+', name) is not None and
            not PurePosixPath(name).is_absolute() and
            all(part not in ('', '.', '..') for part in name.split('/')), 'UNSAFE_MEMBER')
    return name


class Reader:
    """Bounded ordinary local files; stable caller-owned trees, not hostile-FS isolation."""
    def __init__(self):
        self.total = 0
        self.snapshots = {}

    @staticmethod
    def ordinary(path):
        require(path.is_absolute() and '..' not in path.parts and
                not str(path).startswith(('\\\\', '//')) and
                (os.name != 'nt' or ':' not in ''.join(path.parts[1:])), 'ORDINARY_LOCAL_PATH_REQUIRED')
        for p in (path, *path.parents):
            require(not p.is_symlink() and not p.is_junction(), 'ORDINARY_LOCAL_PATH_REQUIRED')

    @staticmethod
    def fingerprint(info):
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    @staticmethod
    def identity(info):
        # Windows ctime is deprecated and path/handle queries can expose
        # different semantics. Compare birth time across queries; retain ctime
        # stability checks separately for each query below.
        # https://docs.python.org/3/library/os.html#os.stat_result.st_birthtime_ns
        stamp = info.st_birthtime_ns if os.name == 'nt' else info.st_ctime_ns
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, stamp)

    def read(self, path, limit=1024*1024):
        path = Path(path)
        self.ordinary(path)
        before = path.stat()
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit,
                'BOUNDED_ORDINARY_FILE_REQUIRED')
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        pin = self.fingerprint(before)
        path_after = path.stat()
        require(self.identity(before) == self.identity(opened) == self.identity(after) == self.identity(path_after)
                and pin == self.fingerprint(path_after)
                and self.fingerprint(opened) == self.fingerprint(after)
                and len(raw) == before.st_size <= limit,
                'EVIDENCE_CHANGED_DURING_READ')
        self.total += len(raw)
        require(self.total <= 96*1024*1024, 'TOTAL_READ_BOUND')
        if path in self.snapshots:
            require(self.snapshots[path] == pin, 'EVIDENCE_CHANGED_DURING_READ')
        self.snapshots[path] = pin
        return raw

    def finish(self):
        for path, pin in self.snapshots.items():
            self.ordinary(path)
            require(pin == self.fingerprint(path.stat()), 'EVIDENCE_CHANGED_DURING_READ')


def candidate(reader, folder, policy):
    raw = reader.read(folder / policy['filename'], 64*1024*1024)
    require(sha(raw) == policy['package_sha256'], 'CANDIDATE_ZIP_MISMATCH')
    receipt = reader.read(folder / 'release-receipt.json')
    require(sha(receipt) == policy['receipt_sha256'], 'CANDIDATE_RECEIPT_MISMATCH')
    match(parse(receipt), dict(schema=1, filename=policy['filename'], sha256=policy['package_sha256'],
          source_revision=policy['source_revision'], packaging_revision=policy['packaging_revision'],
          source_zip_sha256=policy['source_zip_sha256'], runtime=policy['runtime'],
          tools=12, exercises=2, expected_cli_calls=36, expected_review_outcomes=17), 'CANDIDATE_IDENTITY_MISMATCH')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        names = [relative(row.filename) for row in members]
        require(len(names) <= 512 and len({n.casefold() for n in names}) == len(names), 'ZIP_INVENTORY_INVALID')
        require(all(not row.is_dir() and stat.S_IFMT(row.external_attr >> 16) in (0, stat.S_IFREG)
                    and row.file_size <= 32*1024*1024 for row in members)
                and sum(row.file_size for row in members) <= 64*1024*1024, 'ZIP_INVENTORY_INVALID')
        manifest = archive.read(policy['prefix'] + 'PACKAGE-MANIFEST.json')
    match(parse(manifest), dict(source_revision=policy['source_revision'], runtime=policy['runtime'],
          packaging_revision=policy['packaging_revision'], source_zip_sha256=policy['source_zip_sha256']),
          'BUNDLE_MANIFEST_MISMATCH')
    return sha(manifest)


def saved_run(reader, root, policy, manifest_pin):
    manifest_raw = reader.read(root / 'RUN-MANIFEST.json')
    manifest = parse(manifest_raw)
    match(manifest, dict(schema=1, status='PASS', source_revision=policy['source_revision']), 'RUN_MANIFEST_INVALID')
    require(type(manifest.get('files')) is dict and 0 < len(manifest['files']) <= 256, 'RUN_INVENTORY_BOUND')
    actual = {}; directories = [root]; scanned = 0
    while directories:
        folder = directories.pop(); reader.ordinary(folder); scanned += 1
        require(scanned <= 64, 'RUN_DIRECTORY_BOUND')
        for path in folder.iterdir():
            reader.ordinary(path)
            if path.is_dir():
                directories.append(path)
                require(len(directories) <= 64, 'RUN_DIRECTORY_BOUND')
            elif path.name != 'RUN-MANIFEST.json' or path.parent != root:
                name = relative(path.relative_to(root).as_posix())
                actual[name] = reader.read(path, 16*1024*1024)
                require(len(actual) <= 256, 'RUN_INVENTORY_BOUND')
    require(set(actual) == set(manifest['files']), 'RUN_INVENTORY_MISMATCH')
    for name, raw in actual.items():
        relative(name)
        require(set(manifest['files'][name]) == {'bytes', 'sha256'}, 'RUN_FILE_RECORD_INVALID')
        match(manifest['files'][name], dict(bytes=len(raw), sha256=sha(raw)), 'RUN_FILE_HASH_MISMATCH')
    require({'result.json', 'report.html'} <= set(actual), 'RUN_REPORT_REQUIRED')
    result = parse(actual['result.json'])
    match(result, dict(schema=1, status='PASS', mode='FICTIONAL_MANUFACTURING_REVIEW_DEMO', version='0.1.0',
          command_checks=36, expected_review_outcomes=17, operator_review='REQUIRED',
          source_revision=policy['source_revision'], packaging_revision=policy['packaging_revision'],
          bundle_manifest_sha256=manifest_pin, network_required=False,
          physical_operations_performed=False, publication_authorized=False,
          runtime=dict(runtime=policy['runtime'], bundled_runtime=True, isolated=True,
                       user_site_disabled=True, external_import_paths=False, executable='runtime/python.exe')),
          'RUN_RESULT_MISMATCH')
    require(set(result['exercises']) == {'capacity', 'material-quality'}, 'BOTH_EXERCISES_REQUIRED')
    for name, count, reviews in (('capacity', 12, 4), ('material-quality', 24, 13)):
        value = result['exercises'][name]
        match(value, dict(status='PASS', command_checks=count, expected_review_outcomes=reviews,
              operator_review='REQUIRED', original_inputs_unchanged=True, report_hashes_recomputed=True,
              execution_authorized=False, publication_authorized=False), 'EXERCISE_RESULT_MISMATCH')
        require(parse(actual[name + '/observed-results.json']) == value, 'RETAINED_SUMMARY_MISMATCH')
        receipts = value['receipts']
        require(type(receipts) is list and len(receipts) == count, 'RECEIPT_COUNT_MISMATCH')
        seen = set(); failed = 0
        for row in receipts:
            case = row['case']
            require(type(case) is str and re.fullmatch('[a-z0-9-]+', case) is not None
                    and case not in seen and type(row['exit_code']) is int
                    and row['exit_code'] in (0, 1), 'RECEIPT_INVALID')
            seen.add(case); failed += row['exit_code']
            for kind in ('input', 'report'):
                raw = actual[name + '/' + case + '-' + kind + '.json']
                require(sha(raw) == row[kind + '_sha256'], 'RECEIPT_HASH_MISMATCH')
        require(failed == reviews, 'EXPECTED_FAILURES_NOT_RETAINED')
    match(result['exercises']['capacity'], dict(eligible_before=2, eligible_after=3,
          peak_units_before=3, peak_units_after=2, total_closing=21,
          duration_ticks=dict(elapsed_ticks=12, active_ticks=9, hold_ticks=3, hold_count=1)), 'CAPACITY_ORACLE_MISMATCH')
    material = result['exercises']['material-quality']
    match(material, dict(kits=4, motor_requirement=4, filter_requirement=8, overreserved_motor_units=1,
          filter_shortage_before=1, initial_within_limits=2, later_within_limits=3,
          inspection_attempts=5, rework_events=1,
          final_counts=dict(closed_cohort=True, cohort=4, first_pass_good=2, good=3, pending=0, reworked_good=1, scrap=1),
          exact_fractions=dict(eventual_yield='3/4', first_pass_yield='1/2', pending_fraction='0/1', scrap_fraction='1/4')),
          'MATERIAL_ORACLE_MISMATCH')
    require(sha(actual['material-quality/authored-mapping.json']) == material['mapping_sha256'], 'MAPPING_HASH_MISMATCH')
    return sha(manifest_raw), len(actual)


def records(reader, candidate_dir, evidence_dir, policy):
    manifest_pin = candidate(reader, candidate_dir, policy)
    paths = dict(preflight=evidence_dir / 'preflight-private.json',
                 qualification_summary=evidence_dir / 'qualification-summary.json',
                 native_acceptance=evidence_dir / 'packages/acceptance.json')
    raw = {key: reader.read(path) for key, path in paths.items()}
    p, q, a = (parse(raw[key]) for key in ('preflight', 'qualification_summary', 'native_acceptance'))
    match(p, dict(scope=PREFLIGHT_SCOPE, commands=[], registered_interpreters=[], errors=[],
          windows='11', architecture='AMD64', system_python_executed=False, software_removed=False), 'PREFLIGHT_NOT_CLEAR')
    match(q, dict(status='NATIVE_ACCEPTANCE_PASS_AWAITING_OPERATOR_CONFIRMATION',
          package_sha256=policy['package_sha256'], packaging_revision=policy['packaging_revision'],
          native_checks=8, cli_checks=36, expected_review_outcomes=17, browser_tested_here=False,
          clean_windows_provenance='NOT_AUTOMATICALLY_ESTABLISHED', preflight_scope=PREFLIGHT_SCOPE,
          publication_authorized_by_this_file=False, raw_private_runs_uploaded=False), 'NATIVE_SUMMARY_MISMATCH')
    match(a, dict(schema=1, status='PASS', package_sha256=policy['package_sha256'],
          source_revision=policy['source_revision'], packaging_revision=policy['packaging_revision'],
          runtime=policy['runtime'], browser=False, browser_checks=0, cli_checks=36,
          expected_review_outcomes=17, captures={}, video={}, source_files_changed=False,
          system_python_required=False, physical_operations_performed=False, clean_windows_verification_separate=True),
          'NATIVE_ACCEPTANCE_MISMATCH')
    require(type(a.get('checks')) is list and len(a['checks']) == 8 and
            all(type(x) is str for x in a['checks']) and set(a['checks']) == NATIVE_CHECKS, 'ALL_NATIVE_CHECKS_REQUIRED')
    run_pin, files = saved_run(reader, evidence_dir / 'native checks/private/fresh manual run', policy, manifest_pin)
    bindings = {key + '_sha256': sha(value) for key, value in raw.items()}
    bindings['run_manifest_sha256'] = run_pin
    return bindings, files


def check(candidate_dir, evidence_dir, *, policy=POLICY, prepare=False):
    reader = Reader()
    bindings, files = records(reader, Path(candidate_dir), Path(evidence_dir), policy)
    template = dict(schema=1, kind=policy['kind'], package_sha256=policy['package_sha256'],
        packaging_revision=policy['packaging_revision'], bindings=bindings,
        environment=dict(kind=None, fresh_windows_installation_confirmed=None,
                         python_not_installed_before_packet=None, limited_preflight_scope_acknowledged=None),
        observations={key: None for key in OBSERVATIONS}, operator_affirms_personal_observation=None)
    path = Path(evidence_dir) / 'operator-observations.json'
    if prepare:
        reader.finish()
        with path.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(template, indent=2) + '\n')
        return dict(status='OBSERVATIONS_TEMPLATE_CREATED', publication_authorized=False,
                    observations_preapproved=False)
    manual = parse(reader.read(path))
    require(set(manual) == set(template) and set(manual.get('environment', {})) == set(template['environment'])
            and set(manual.get('observations', {})) == set(OBSERVATIONS)
            and set(manual.get('bindings', {})) == set(bindings), 'OPERATOR_RECORD_FIELDS_MISMATCH')
    match(manual, dict(schema=1, kind=policy['kind'], package_sha256=policy['package_sha256'],
          packaging_revision=policy['packaging_revision'], bindings=bindings,
          operator_affirms_personal_observation=True, observations=OBSERVATIONS,
          environment=dict(fresh_windows_installation_confirmed=True, python_not_installed_before_packet=True,
                           limited_preflight_scope_acknowledged=True)), 'OPERATOR_OBSERVATIONS_INCOMPLETE_OR_MISMATCHED')
    require(manual['environment']['kind'] in ('fresh-windows-vm', 'fresh-windows-pc'), 'FRESH_WINDOWS_ENVIRONMENT_REQUIRED')
    reader.finish()
    return dict(schema=1, status='FIXTURE_VALIDATED' if policy['kind'] == 'fictional-fixture' else 'CONSISTENT_REQUIRES_HUMAN_REVIEW',
        evidence_kind=policy['kind'], package_sha256=policy['package_sha256'],
        packaging_revision=policy['packaging_revision'], command_checks=36, expected_review_outcomes=17,
        native_checks=8, saved_files_checked=files, record_bindings=bindings,
        operator_observations='ASSERTED_NOT_INDEPENDENTLY_VERIFIED',
        whole_disk_python_absence_proved=False, execution_authenticity_proved=False,
        publication_authorized=False, raw_private_records_included=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-dir', required=True, type=Path)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    parser.add_argument('--prepare-observations', action='store_true')
    args = parser.parse_args(argv)
    try:
        value = check(args.candidate_dir, args.evidence_dir, prepare=args.prepare_observations)
    except GateError as error:
        print(json.dumps(dict(status='REJECTED', code=str(error), publication_authorized=False)))
        return 2
    except Exception:
        # Never echo exception text, file contents, paths or a traceback publicly.
        print(json.dumps(dict(status='REJECTED', code='INVALID_OR_UNAVAILABLE_EVIDENCE', publication_authorized=False)))
        return 2
    print(json.dumps(value))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
