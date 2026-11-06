"""Generate a truthful, checked install-readiness plan for every public tool."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'catalog/registry.json'
MAP = ROOT / 'docs/TOOL-TO-SYSTEM-MAP.md'
OUTPUT = ROOT / 'integrations/install-plan.json'
SOURCE_COMMIT = '50b33f2bdf7ec5a8b6f75404d860df1bfb14ee71'
COMMAND = re.compile(r'(?:python(?:3(?:\.\d+)?)?|py)\s+-B\s+([A-Za-z0-9_-]+\.py)')


def source_entry(component):
    folder = ROOT / component['path']
    readme = (folder / 'README.md').read_text(encoding='utf-8')
    candidates = []
    for name in COMMAND.findall(readme):
        if name != 'source_check.py' and (folder / name).is_file() and name not in candidates:
            candidates.append(name)
    return candidates[0] if len(candidates) == 1 else None


def system_links():
    mapping = {}
    systems = {p.name for p in (ROOT / 'systems').iterdir() if p.is_dir()}
    for line in MAP.read_text(encoding='utf-8').splitlines():
        if not line.startswith('| ') or '../tools/' not in line:
            continue
        tools = re.findall(r'\.\./tools/([a-z0-9-]+)/README\.md', line.split('|')[2])
        related = re.findall(r'\.\./systems/([a-z0-9-]+)/README\.md', line.split('|')[3])
        if not set(related) <= systems:
            raise ValueError('SYSTEM_MAP_TARGET_MISSING')
        for tool in tools:
            mapping[tool] = related
    return mapping


def generate():
    registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
    components = [c for c in registry['components'] if c['kind'] == 'tool']
    source_bundles = {tool: bundle for bundle in registry['source_bundles'] for tool in bundle['tools']}
    wheels = {tool['id']: (collection, tool) for collection in registry.get('installable_collections', [])
              for tool in collection['tools']}
    bundles = {tool: bundle for bundle in registry.get('installable_bundles', []) for tool in bundle['tools']}
    related = system_links()
    records = []
    for c in components:
        tool = c['id']; folder = ROOT / c['path']
        example = c['path'] + '/examples/input.json'
        if not (ROOT / example).is_file():
            example = None
        entry = source_entry(c)
        install = []
        if tool in wheels:
            collection, member = wheels[tool]
            install.append({'kind': 'individual_wheel', 'tag': collection['tag'], 'filename': member['filename']})
            install.append({'kind': 'collection_wheel', 'tag': collection['tag'],
                            'filename': collection['collection_filename']})
        if tool in bundles:
            bundle = bundles[tool]
            install.append({'kind': 'collection_install_zip', 'tag': bundle['tag'],
                            'filename': bundle['filename'], 'sha256': bundle['sha256']})
        if tool in source_bundles:
            bundle = source_bundles[tool]
            install.append({'kind': 'source_zip', 'tag': bundle['tag'], 'filename': bundle['filename']})
        if c.get('focused_release'):
            release = c['focused_release']
            install.append({'kind': 'focused_source_zip', 'tag': release['tag'], 'filename': release['filename']})
        if c.get('windows_release'):
            release = c['windows_release']
            install.append({'kind': 'windows_portable', 'tag': release['tag'], 'filename': release['filename']})
        records.append({
            'id': tool, 'title': c['title'], 'purpose': c['purpose'], 'group': c['group'],
            'runtime_and_dependency_guide': c['requirements'],
            'source_entry': entry, 'source_entry_status': 'readme_observed' if entry else 'needs_review',
            'example_input': example, 'example_guide': c['examples'][0],
            'result_meaning_guide': c['validation'],
            'install_options': install,
            'individual_install_status': 'released_wheel' if tool in wheels else 'needs_package_review',
            'related_systems': related.get(tool, []),
            'relationship_status': 'documented_use_case_only' if tool in related else 'needs_mapping',
            'source_guide': c['path'] + '/README.md',
        })
    if len(records) != len({r['id'] for r in records}) or len(records) != len(components):
        raise ValueError('TOOL_COVERAGE_DRIFT')
    if any(not (ROOT / r['example_guide']).is_file() or not (ROOT / r['result_meaning_guide']).is_file()
           or r['example_input'] and not (ROOT / r['example_input']).is_file() for r in records):
        raise ValueError('GUIDE_OR_EXAMPLE_MISSING')
    summary = {
        'tools': len(records),
        'readme_observed_source_entries': sum(r['source_entry'] is not None for r in records),
        'fictional_input_files': sum(r['example_input'] is not None for r in records),
        'released_individual_wheels': sum(r['individual_install_status'] == 'released_wheel' for r in records),
        'documented_system_use_cases': sum(bool(r['related_systems']) for r in records),
    }
    return {'format': 'outlands-install-readiness-plan-v1', 'repository': registry['repository'],
            'source_commit': SOURCE_COMMIT,
            'scope': 'Public tools only; pointers and review states are not package qualification',
            'summary': summary, 'tools': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('generate', 'check'))
    args = parser.parse_args()
    raw = (json.dumps(generate(), indent=2, ensure_ascii=True) + '\n').encode('utf-8')
    if args.command == 'generate':
        OUTPUT.write_bytes(raw)
    elif not OUTPUT.is_file() or OUTPUT.read_bytes() != raw:
        raise ValueError('INSTALL_PLAN_STALE')
    print(json.dumps({'status': 'PASS', 'summary': json.loads(raw)['summary']}))


if __name__ == '__main__':
    main()
