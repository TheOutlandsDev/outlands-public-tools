"""Run one family workshop on invented data; no installs or live integrations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ('release-qa', 'files-workflows', 'documents-media', 'android-linux',
            'desktop-diagnostics', 'local-apps', 'data-ai', 'game-utilities')

def call(script, arguments, code=0, module=False, cwd=None):
    command = [sys.executable, '-B']
    command += ['-m', script] if module else [str(ROOT / script)]
    process = subprocess.run(command + list(map(str, arguments)), cwd=cwd or ROOT,
                             capture_output=True, text=True, encoding='utf-8', timeout=60)
    if process.returncode != code:
        raise ValueError('WORKSHOP_COMMAND_FAILED')
    return json.loads(process.stdout)

def file_hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}

def workshop(family, workspace):
    destination = Path(workspace)
    if family not in FAMILIES or not destination.is_absolute() or destination.exists() or not destination.parent.is_dir():
        raise ValueError('NEW_ABSOLUTE_WORKSPACE_REQUIRED')
    destination = destination.resolve()
    if destination.is_relative_to(ROOT): raise ValueError('EXTERNAL_WORKSPACE_REQUIRED')
    destination.mkdir(mode=0o700)
    evidence = {}; checks = 0
    if family == 'release-qa':
        data = call('methodology/worked-examples/run_examples.py', ['--workspace', destination / 'review'])
        if data['examples_passed'] != 3: raise ValueError('EXPECTED_THREE_EXAMPLES')
        evidence = data; checks = 8
    elif family == 'files-workflows':
        tool = 'tools/backup-chain-checker/chain_check.py'; base = ROOT / 'tools/backup-chain-checker/examples'
        good = call(tool, ['--plan', base / 'valid-chain.json'])
        bad = call(tool, ['--plan', base / 'missing-parent.json'], 1)
        if good['status'] != 'DECLARED_CHAIN_CONSISTENT' or bad['status'] != 'REVIEW_REQUIRED':
            raise ValueError('CHAIN_EXPECTATION_FAILED')
        evidence = {'consistent': good['status'], 'missing_parent': bad['status'],
                    'boundary': 'Declared relationships only; no backup bytes or restore was checked.'}; checks = 2
    elif family == 'documents-media':
        base = destination / 'fixtures'
        call('tools/vpd-reference-checker/examples/make_demo.py', ['--destination', base, '--complete'])
        tool = 'tools/vpd-reference-checker/vpd_references.py'
        call(tool, ['--project', base / 'project.vpd', '--output', destination / 'inventory'])
        call(tool, ['--project', base / 'project.vpd', '--mapping', base / 'mapping.json',
                    '--media-root', base / 'copies', '--output', destination / 'mapped'])
        report = json.loads((destination / 'mapped/report.json').read_text(encoding='utf-8'))
        if report['status'] != 'NO_MAPPING_FINDINGS' or report['metadata_check_attempt_count'] != 2:
            raise ValueError('MEDIA_EXPECTATION_FAILED')
        manifest = json.loads((destination / 'mapped/MANIFEST.json').read_text(encoding='utf-8'))
        for entry in manifest['files']:
            body = (destination / 'mapped' / entry['path']).read_bytes()
            if len(body) != entry['bytes'] or hashlib.sha256(body).hexdigest() != entry['sha256']:
                raise ValueError('REPORT_MANIFEST_MISMATCH')
        evidence = {'mapped_report_created': True, 'boundary': 'Empty fictional placeholders establish metadata availability, not playable media.'}; checks = 3
    elif family == 'android-linux':
        base = destination / 'fixtures'; call('tools/fstab-diff/examples/generate.py', ['--output', base])
        tool = 'tools/fstab-diff/fstab_diff.py'
        same = call(tool, ['--before', base / 'linux-before.fstab', '--after', base / 'linux-same.fstab',
                           '--format', 'linux', '--output', destination / 'same'])
        changed = call(tool, ['--before', base / 'linux-before.fstab', '--after', base / 'linux-changed.fstab',
                              '--format', 'linux', '--output', destination / 'changed'], 1)
        if same['status'] != 'NO_SCOPE_FINDINGS' or changed['status'] != 'REVIEW_REQUIRED':
            raise ValueError('FSTAB_EXPECTATION_FAILED')
        evidence = {'comment_only': same['status'], 'changed': changed['status'], 'boundary': 'No configuration was installed or mounted.'}; checks = 3
    elif family == 'desktop-diagnostics':
        data = call('resource_monitor', ['demo'], module=True, cwd=ROOT / 'tools/resource-monitor')
        if data['mode'] != 'demo' or len(data['samples']) != 2 or data['samples'][1]['cpu_percent'] != 24.6:
            raise ValueError('DEMO_EXPECTATION_FAILED')
        (destination / 'fictional-samples.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        evidence = {'fictional_sample_export': True, 'boundary': 'Demo provider only; no machine sampling, server or device was started.'}; checks = 1
    elif family == 'local-apps':
        tool = 'tools/job-quote-tracker/tracker.py'; db = destination / 'demo.sqlite'
        call(tool, ['demo', db]); before = call(tool, ['list', db])
        call(tool, ['backup', db, destination / 'backup'])
        call(tool, ['verify-backup', destination / 'backup'])
        call(tool, ['restore', destination / 'backup', destination / 'restored.sqlite'])
        after = call(tool, ['list', destination / 'restored.sqlite'])
        if before != after: raise ValueError('RESTORED_RECORDS_DIFFER')
        evidence = {'restored_records_match': True, 'boundary': 'Fictional CLI and SQLite recovery; no GUI or customer authorization was tested.'}; checks = 6
    elif family == 'data-ai':
        tool = 'tools/evaluation-metrics-calculator/evaluation_metrics.py'; base = ROOT / 'tools/evaluation-metrics-calculator/examples'
        good = call(tool, ['--counts', base / 'counts.json'])
        bad = call(tool, ['--counts', base / 'undefined-counts.json'], 1)
        if good['status'] != 'METRICS_COMPUTED' or bad['status'] != 'REVIEW_REQUIRED':
            raise ValueError('METRICS_EXPECTATION_FAILED')
        if good['accuracy']['numerator'] != 17 or good['accuracy']['denominator'] != 20 or bad['counts']['undefined_metrics'] != 5:
            raise ValueError('METRICS_ARITHMETIC_FAILED')
        evidence = {'defined': good, 'undefined_status': bad['status'], 'boundary': 'Invented confusion counts; no model was run or evaluated.'}; checks = 2
    else:
        base = destination / 'fixtures'; store = destination / 'profiles'
        call('tools/mod-profile-manager/examples/generate.py', ['--output', base])
        before = file_hashes(base); tool = 'tools/mod-profile-manager/profile_manager.py'
        call(tool, ['init', '--workspace', store])
        call(tool, ['import-profile', '--workspace', store, '--profile', 'orchard', '--source', base / 'orchard'])
        call(tool, ['plan', '--workspace', store, '--action', 'activate', '--profile', 'orchard'])
        call(tool, ['activate', '--workspace', store, '--profile', 'orchard'])
        active = call(tool, ['status', '--workspace', store])
        call(tool, ['deactivate', '--workspace', store])
        inactive = call(tool, ['status', '--workspace', store])
        if active['active_profile'] != 'orchard' or inactive['active_profile'] is not None or inactive['pending'] is not None:
            raise ValueError('PROFILE_STATE_EXPECTATION_FAILED')
        if before != file_hashes(base): raise ValueError('ORIGINAL_FIXTURES_CHANGED')
        evidence = {'originals_preserved': True, 'activation': active, 'deactivation': inactive,
                    'boundary': 'Managed fictional copies only; no game installation, loader or gameplay was used.'}; checks = 8
    receipt = {'schema': 1, 'family': family, 'status': 'PASS', 'command_checks': checks,
               'inputs': 'fictional', 'evidence': evidence}
    (destination / 'observed-results.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'family': family, 'status': 'PASS', 'command_checks': checks}))
    return receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', choices=FAMILIES, required=True)
    parser.add_argument('--workspace', required=True)
    try:
        options = parser.parse_args(); workshop(options.family, options.workspace)
    except (ValueError, OSError, KeyError, subprocess.SubprocessError):
        print(json.dumps({'status': 'ERROR', 'code': 'WORKSHOP_NOT_COMPLETED'})); sys.exit(1)
