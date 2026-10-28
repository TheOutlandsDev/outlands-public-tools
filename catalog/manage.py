"""One public registry: coverage checks, release planning and portfolio projection."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OWNER = 'TheOutlandsDev/outlands-public-tools'
REGISTRY = ROOT / 'catalog/registry.json'
GENERATED = ROOT / 'catalog/generated'

def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + '\n').encode('utf-8')

def read_registry(): return json.loads(REGISTRY.read_text(encoding='utf-8'))
def read_plan(): return json.loads((ROOT / 'packages/catalog.json').read_text(encoding='utf-8'))

def inventory():
    return {p.relative_to(ROOT).as_posix() for parent in ('tools', 'systems')
            for p in (ROOT / parent).iterdir() if p.is_dir() and (p / 'README.md').is_file()}

def validate(registry, actual=None):
    if registry.get('schema') != 1 or registry.get('repository') != OWNER:
        raise ValueError('REGISTRY_IDENTITY_INVALID')
    groups = [g['id'] for g in registry['groups']]
    if len(groups) != len(set(groups)) or not all(re.fullmatch('[a-z0-9-]+', x) for x in groups):
        raise ValueError('GROUPS_INVALID')
    names = []
    for component in registry['components']:
        name = component['path']; names.append(name)
        if not re.fullmatch('(tools|systems)/[a-z0-9-]+', name) or component['id'] != name.split('/')[1]:
            raise ValueError('COMPONENT_PATH_INVALID')
        system = name.startswith('systems/')
        if component['group'] not in groups + ['systems'] or (component['group'] == 'systems') != system:
            raise ValueError('COMPONENT_GROUP_INVALID')
        if component['package'] != ('complete' if system else component['group']):
            raise ValueError('PACKAGE_ASSIGNMENT_INVALID')
        for field in ('title', 'purpose', 'requirements', 'validation'):
            if not isinstance(component.get(field), str) or not 1 <= len(component[field]) <= 1000:
                raise ValueError('COMPONENT_METADATA_REQUIRED')
        if not isinstance(component.get('examples'), list) or not component['examples']:
            raise ValueError('EXAMPLES_REQUIRED')
        for path in [component['validation'], *component['examples']]:
            if not isinstance(path, str) or '..' in path.split('/') or path.startswith('/') or '\\' in path:
                raise ValueError('DOCUMENT_PATH_INVALID')
            if not (ROOT / path.split('#')[0]).is_file(): raise ValueError('DOCUMENT_MISSING')
        focused = component.get('focused_release')
        if focused:
            if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', focused['version']) or focused['tag'] != component['id'] + '-v' + focused['version'] or focused['filename'] != component['id'] + '-' + focused['version'] + '.zip':
                raise ValueError('FOCUSED_RELEASE_INVALID')
            if focused['demo'] != 'https://connor-oshea-outlands.thatrobotguy.chatgpt.site/#download-walkthroughs':
                raise ValueError('FOCUSED_DEMO_INVALID')
            if not (ROOT / name / 'START-HERE.md').is_file(): raise ValueError('FOCUSED_START_GUIDE_REQUIRED')
    if len(names) != len(set(names)): raise ValueError('DUPLICATE_COMPONENT')
    actual = inventory() if actual is None else set(actual)
    if actual != set(names):
        raise ValueError('CATALOG_DRIFT missing=' + ','.join(sorted(actual - set(names))) +
                         ' obsolete=' + ','.join(sorted(set(names) - actual)))
    release = registry['published_toolkit']
    if not re.fullmatch('[0-9a-f]{40}', release['source_revision']) or release['tag'] != 'toolkit-v' + release['version']:
        raise ValueError('RELEASE_IDENTITY_INVALID')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', release['version']): raise ValueError('RELEASE_VERSION_INVALID')

def at_revision(revision):
    raw = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', revision], cwd=ROOT).decode('utf-8')
    return {p.rsplit('/', 1)[0] for p in raw.splitlines() if re.fullmatch('(tools|systems)/[^/]+/README.md', p)}

def model(registry):
    validate(registry)
    release = registry['published_toolkit']; covered = at_revision(release['source_revision'])
    records = []
    for c in registry['components']:
        released = c['path'] in covered
        revision = c['focused_release']['tag'] if c.get('focused_release') else release['source_revision'] if released else 'main'
        records.append(dict(c, summary=c['purpose'], family=c['group'], released=released,
                            guide='https://github.com/' + OWNER + '/blob/' + revision + '/' + c['path'] + '/README.md'))
    groups = registry['groups']; version = release['version']
    downloads = [{'id': 'complete', 'title': 'Complete source collection', 'components': len(covered),
                  'filename': 'outlands-complete-' + version + '.zip'}]
    for g in groups:
        count = sum(c['group'] == g['id'] and c['released'] for c in records)
        downloads.append({'id': g['id'], 'title': g['title'], 'components': count,
                          'filename': 'outlands-' + g['id'] + '-' + version + '.zip'})
    base = 'https://github.com/' + OWNER + '/releases/download/' + release['tag'] + '/'
    for d in downloads: d['url'] = base + d['filename']
    return {'schema': 1, 'source_revision': release['source_revision'], 'release': release,
            'groups': groups, 'tools': records, 'projects': registry['projects'], 'downloads': downloads,
            'pending_packaging': [c['path'] for c in records if not c['released']]}

def render(data):
    esc = lambda s: html.escape(str(s), quote=True)
    github = 'https://github.com/' + OWNER
    groups = [{'id': 'systems', 'title': 'Complete application workbenches'}, *data['groups']]
    blocks = []
    for group in groups:
        entries = [c for c in data['tools'] if c['group'] == group['id']]
        cards = []
        for c in entries:
            badge = '' if c['released'] else '<p class="snapshot-note">Public source · next package pending</p>'
            focused = c.get('focused_release'); actions = ''
            if focused:
                base = github + '/blob/' + focused['tag'] + '/' + c['path']
                actions = '<div class="focused-links"><a href="' + github + '/releases/download/' + esc(focused['tag']) + '/' + esc(focused['filename']) + '">Download v' + esc(focused['version']) + ' ↓</a><a href="' + base + '/START-HERE.md">Quick start ↗</a><a href="' + esc(focused['demo']) + '">Demo ↓</a><a href="' + base + '/docs/PROVENANCE.md">Methodology ↗</a></div>'
            cards.append('<article class="tool-card" data-tool-card data-family="' + esc(group['id']) + '"><h4>' + esc(c['title']) +
                         '</h4><p>' + esc(c['purpose']) + '</p><p class="tool-requirements">' + esc(c['requirements']) + '</p>' + badge +
                         '<a href="' + esc(c['guide']) + '">Guide &amp; requirements ↗</a>' + actions + '</article>')
        blocks.append('<details class="tool-family" data-tool-family open><summary>' + esc(group['title']) + ' <span>' + str(len(entries)) +
                      ' entries</span></summary><div class="tool-grid">' + ''.join(cards) + '</div></details>')
    cards = []
    for p in data['projects']:
        repo = p['repository']
        if not re.fullmatch('[A-Za-z0-9_-]+', repo): raise ValueError('PROJECT_ID_INVALID')
        link = '' if not p['releases'] else '<a href="' + esc(p['releases']) + '">Release downloads ↗</a>'
        cards.append('<article class="tool-card" data-tool-card data-family="projects"><h4>' + esc(p['title']) + '</h4><p>' +
                     esc(p['summary']) + '</p><a href="https://github.com/TheOutlandsDev/' + repo + '">Source &amp; setup ↗</a>' + link + '</article>')
    blocks.append('<details class="tool-family" data-tool-family open><summary>More public projects <span>' + str(len(cards)) +
                  ' projects</span></summary><div class="tool-grid">' + ''.join(cards) + '</div></details>')
    packages = []
    for download in data['downloads'][1:]:
        packages.append('<div class="package-card"><a href="' + esc(download['url']) + '"><strong>' + esc(download['title']) +
                        '</strong><span>' + str(download['components']) + ' tools · source ZIP ↓</span></a><a href="' + github +
                        '/blob/main/workshops/' + download['id'] + '.md">Five-minute workshop ↗</a></div>')
    options = '<option value="all">All categories</option>' + ''.join('<option value="' + g['id'] + '">' + esc(g['title']) + '</option>' for g in groups) + '<option value="projects">More public projects</option>'
    tools = sum(c['kind'] == 'tool' for c in data['tools']); systems = len(data['tools']) - tools
    released_tools = sum(c['kind'] == 'tool' and c['released'] for c in data['tools'])
    released_systems = sum(c['kind'] == 'system' and c['released'] for c in data['tools'])
    values = {'DIRECTORY_GROUPS': ''.join(blocks), 'PACKAGE_CARDS': ''.join(packages), 'FAMILY_OPTIONS': options,
              'TOOL_COUNT': tools, 'SYSTEM_COUNT': systems, 'RELEASE_TOOL_COUNT': released_tools,
              'RELEASE_SYSTEM_COUNT': released_systems, 'ENTRY_COUNT': len(data['tools']) + len(data['projects']),
              'PROJECT_COUNT': len(data['projects']), 'TAG': data['release']['tag'], 'VERSION': data['release']['version'],
              'SNAPSHOT_SHORT': data['source_revision'][:8]}
    text = (ROOT / 'catalog/directory.template.html').read_text(encoding='utf-8')
    for key, value in values.items(): text = text.replace('{{' + key + '}}', str(value))
    if re.search(r'{{[A-Z_]+}}', text): raise ValueError('TEMPLATE_VARIABLE_MISSING')
    return text

def projections(registry):
    data = model(registry); github = 'https://github.com/' + OWNER
    markdown = ['# Public tools and release coverage', '',
                'Generated from [the shared registry](registry.json). Update metadata there, then run `python -B catalog/manage.py generate`.', '',
                '| Component | Requirements | Package state | Examples and validation |', '| --- | --- | --- | --- |']
    for c in data['tools']:
        state = c['package'] if c['released'] else 'Source only; next package pending'
        examples = github + '/blob/main/' + c['examples'][0]; validation = github + '/blob/main/' + c['validation']
        markdown.append('| [' + c['title'].replace('|', '/') + '](' + c['guide'] + ') | ' + c['requirements'].replace('|', '/') +
                        ' | ' + state + ' | [Examples](' + examples + ') · [Validation](' + validation + ') |')
    return {'directory.html': render(data).encode('utf-8'), 'site-data.json': encoded(data),
            'INDEX.md': ('\n'.join(markdown) + '\n').encode('utf-8')}

def generate(check=False):
    expected = projections(read_registry())
    if check:
        if any(not (GENERATED / p).is_file() or (GENERATED / p).read_bytes() != b for p, b in expected.items()):
            raise ValueError('GENERATED_CATALOG_STALE run=python_catalog/manage.py_generate')
    else:
        GENERATED.mkdir(exist_ok=True)
        for p, b in expected.items(): (GENERATED / p).write_bytes(b)
    data = model(read_registry())
    print(json.dumps({'status': 'PASS', 'components': len(data['tools']), 'pending_packaging': data['pending_packaging']}))

def fetch(url, maximum=16 * 1024 * 1024):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Outlands-Catalog-Verification'}), timeout=40) as response:
        body = response.read(maximum + 1)
    if len(body) > maximum: raise ValueError('REMOTE_ASSET_BOUND_EXCEEDED')
    return body

def verify_release(tag):
    if not re.fullmatch(r'toolkit-v[0-9]+\.[0-9]+\.[0-9]+', tag): raise ValueError('TAG_INVALID')
    release = json.loads(fetch('https://api.github.com/repos/' + OWNER + '/releases/tags/' + tag))
    if release['draft'] or release['tag_name'] != tag: raise ValueError('PUBLISHED_RELEASE_REQUIRED')
    index = json.loads(fetch('https://github.com/' + OWNER + '/releases/download/' + tag + '/catalog.json'))
    if index['tag'] != tag: raise ValueError('RELEASE_CATALOG_MISMATCH')
    assets = {a['name']: a for a in release['assets']}
    for d in index['downloads']:
        filename = d['filename']
        if not re.fullmatch('outlands-[a-z-]+-[0-9.]+[.]zip', filename): raise ValueError('ASSET_NAME_INVALID')
        expected_url = 'https://github.com/' + OWNER + '/releases/download/' + tag + '/' + filename
        if d['url'] != expected_url or filename not in assets or assets[filename]['size'] != d['bytes']:
            raise ValueError('RELEASE_ASSET_MISSING')
        digest = assets[filename].get('digest')
        if not digest:
            digest = 'sha256:' + hashlib.sha256(fetch(expected_url)).hexdigest()
        if digest != 'sha256:' + d['sha256']: raise ValueError('RELEASE_ASSET_DIGEST_MISMATCH')
    return index

def apply(site):
    registry = read_registry(); generate(check=True)
    verify_release(registry['published_toolkit']['tag'])
    for component in registry['components']:
        focused = component.get('focused_release')
        if not focused: continue
        release = json.loads(fetch('https://api.github.com/repos/' + OWNER + '/releases/tags/' + focused['tag']))
        if release['draft'] or release['tag_name'] != focused['tag'] or not any(a['name'] == focused['filename'] for a in release['assets']):
            raise ValueError('PUBLISHED_FOCUSED_DOWNLOAD_REQUIRED')
    folder = Path(site).resolve(); page = folder / 'dist/index.html'
    if not (folder / '.openai/hosting.json').is_file(): raise ValueError('EXISTING_SITE_REQUIRED')
    text = page.read_text(encoding='utf-8'); start = text.index('<section class="toolkit shell"'); end = text.index('<section class="approach"', start)
    page.write_text(text[:start] + projections(registry)['directory.html'].decode('utf-8') + text[end:], encoding='utf-8', newline='\n')
    (folder / 'dist/tool-catalog.json').write_bytes(projections(registry)['site-data.json'])
    print(json.dumps({'status': 'APPLIED', 'tag': registry['published_toolkit']['tag']}))

def check_site(site):
    folder = Path(site).resolve(); registry = read_registry(); expected = projections(registry)
    text = (folder / 'dist/index.html').read_text(encoding='utf-8')
    start = text.index('<section class="toolkit shell"'); end = text.index('<section class="approach"', start)
    if text[start:end].encode('utf-8') != expected['directory.html'] or (folder / 'dist/tool-catalog.json').read_bytes() != expected['site-data.json']:
        raise ValueError('PORTFOLIO_PROJECTION_STALE')
    print(json.dumps({'status': 'PASS', 'projection': 'portfolio', 'tag': registry['published_toolkit']['tag']}))

def activate(tag):
    index = verify_release(tag); registry = read_registry()
    registry['published_toolkit'] = {k: index[k] for k in ('version', 'tag', 'source_revision')}
    REGISTRY.write_bytes(encoded(registry)); generate()

def scaffold(options):
    registry = read_registry(); name = options.path
    if name not in inventory(): raise ValueError('PUBLISHED_SOURCE_FOLDER_REQUIRED')
    if any(c['path'] == name for c in registry['components']): raise ValueError('ALREADY_REGISTERED')
    system = name.startswith('systems/')
    entry = {'id': name.split('/')[1], 'path': name, 'title': options.title, 'purpose': options.purpose,
             'kind': 'system' if system else 'tool', 'group': options.group,
             'package': 'complete' if system else options.group, 'requirements': options.requirements,
             'examples': [name + '/README.md'], 'validation': name + '/README.md'}
    registry['components'].append(entry); validate(registry); REGISTRY.write_bytes(encoded(registry)); generate()

def release_plan(version, revision):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version) or not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('EXACT_RELEASE_PLAN_REQUIRED')
    registry = read_registry(); validate(registry); covered = at_revision(revision)
    known = {c['path'] for c in registry['components']}
    if covered - known: raise ValueError('UNREGISTERED_RELEASE_SOURCE')
    plan = {'schema': 1, 'version': version, 'tag': 'toolkit-v' + version, 'source_revision': revision,
            'repository': OWNER, 'groups': [], 'systems': []}
    for group in registry['groups']:
        plan['groups'].append(dict(group, tools=[c['id'] for c in registry['components'] if c['path'] in covered and c['group'] == group['id']]))
    plan['systems'] = [c['id'] for c in registry['components'] if c['path'] in covered and c['kind'] == 'system']
    (ROOT / 'packages/catalog.json').write_bytes(encoded(plan))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check'); sub.add_parser('generate')
    use = sub.add_parser('apply'); use.add_argument('--site', required=True)
    site_check = sub.add_parser('check-site'); site_check.add_argument('--site', required=True)
    promote = sub.add_parser('activate'); promote.add_argument('--tag', required=True)
    verify = sub.add_parser('verify-release'); verify.add_argument('--tag', required=True)
    add = sub.add_parser('scaffold')
    planned = sub.add_parser('release-plan'); planned.add_argument('--version', required=True); planned.add_argument('--source-revision', required=True)
    for field in ('path', 'group', 'title', 'purpose', 'requirements'): add.add_argument('--' + field, required=True)
    options = parser.parse_args()
    if options.command == 'check': generate(check=True)
    elif options.command == 'generate': generate()
    elif options.command == 'apply': apply(options.site)
    elif options.command == 'check-site': check_site(options.site)
    elif options.command == 'activate': activate(options.tag)
    elif options.command == 'scaffold': scaffold(options)
    elif options.command == 'release-plan': release_plan(options.version, options.source_revision)
    else:
        result = verify_release(options.tag); print(json.dumps({'status': 'VERIFIED', 'tag': result['tag'], 'assets': len(result['downloads'])}))
