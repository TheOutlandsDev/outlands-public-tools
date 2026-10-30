"""Generate the shared task chooser without changing applications or releases."""
import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://github.com/TheOutlandsDev/outlands-public-tools'
BEGIN = '<!-- START-HERE:BEGIN -->'
END = '<!-- START-HERE:END -->'
SITE_BEGIN = '<!-- START-HERE-SITE:BEGIN -->'
SITE_END = '<!-- START-HERE-SITE:END -->'


def model():
    data = json.loads((ROOT / 'catalog/start-here.json').read_text(encoding='utf-8'))
    registry = json.loads((ROOT / 'catalog/registry.json').read_text(encoding='utf-8'))
    components = {c['id']: c for c in registry['components']}
    assert data['schema'] == 1 and len(data['routes']) == 3
    for route in data['routes']:
        for item in (route, route['next']):
            if item.get('component'):
                c = components[item['component']]
                release = c['windows_release'] if item.get('windows') else c['focused_release']
                item['download'] = f"{BASE}/releases/download/{release['tag']}/{release['filename']}"
                guide = release.get('start_guide', c['path'] + '/START-HERE.md')
                item['guide'] = f"{BASE}/blob/{release['tag']}/{guide}"
                item['evidence'] = f"{BASE}/blob/{release['tag']}/{release.get('provenance', c['path'] + '/docs/PROVENANCE.md')}"
        for field in ('title', 'requirements', 'exercise', 'expected', 'limits'):
            assert route[field], field
    return data


def markdown(data, compact=False):
    lines = ['## Choose a tool for your task', '',
             'Start with one focused download and its fictional exercise. Windows downloads marked Python included or Node included supply that runtime. Source ZIPs need the runtime documented in their guide.', '']
    if compact:
        for r in data['routes']:
            lines += [f"### {r['title']}", '',
                      f"**[{r['app']}]({r['download']}) · Runtime included.**",
                      f"[Quick start]({r['guide']}) · [Exercise, requirements and limits]({BASE}/blob/main/docs/START-HERE.md#{r['id']})", '']
            if r.get('alternatives'):
                alternatives = ' · '.join('['+('Source ZIP (runtime required)' if 'source ZIP' in a['label'] else a['label'])+']('+a['url']+')' for a in r['alternatives'])
                lines += ['Source alternative: '+alternatives, '']
        lines += [f'[Read the complete starting guide]({BASE}/blob/main/docs/START-HERE.md) · [Portfolio guide](https://connor-oshea-outlands.thatrobotguy.chatgpt.site/#start-here)', '']
    else:
        lines += ['Compare the ZIP SHA-256 with SHA256SUMS.txt from the same release before extracting into a new folder. Keep generated data outside the source folder where the guide requires it. All exercises use invented inputs; keep future real data private.', '']
        for r in data['routes']:
            lines += [f'<a id="{r["id"]}"></a>', f"### {r['title']}", '', f"**Start with {r['app']}.** [Download ZIP]({r['download']}) · [Quick start]({r['guide']}) · [Evidence and methodology]({r['evidence']})", '']
            if r.get('alternatives'):
                lines += ['Alternatives: ' + ' · '.join('['+a['label']+']('+a['url']+')' for a in r['alternatives']), '']
            for label, field in [('Requirements', 'requirements'), ('Try this', 'exercise'), ('Expected result', 'expected'), ('Limits', 'limits')]:
                lines += [f"**{label}:** {r[field]}", '']
            n = r['next']
            lines += [f"**Then try [{n['label']}]({n['guide']}):** {n['exercise']}" + (f" [Download ZIP]({n['download']})." if n.get('download') else ''), '']
        lines += ['These are versioned demonstrations with documented platform checks, not a claim of production deployment. Observed evidence is linked above; reproduce the exercise before treating an expected result as a local test result.', '',
                  f'[Complete catalog]({BASE}/blob/main/catalog/generated/INDEX.md) · [Methodology examples]({BASE}/tree/main/methodology/worked-examples) · [All family workshops]({BASE}/tree/main/workshops)', '']
    return '\n'.join(lines)


def site_html(data):
    e = html.escape
    parts = [SITE_BEGIN, '<section class="start-here shell" id="start-here" aria-labelledby="start-here-title">',
             '<div class="section-heading"><p class="eyebrow">CHOOSE YOUR FIRST WORKFLOW</p><h2 id="start-here-title">What would you like to build?</h2><p>Choose one focused download. Try its fictional exercise, compare the result and inspect the limits. Windows downloads marked Python included or Node included supply that runtime. Source ZIPs need their documented runtime installed separately.</p></div>',
             '<div class="start-route-grid">']
    for i, r in enumerate(data['routes'], 1):
        parts += [f'<article class="start-route" aria-labelledby="route-{e(r["id"])}"><span class="detail-label">0{i} / {e(r["app"])}</span><h3 id="route-{e(r["id"])}">{e(r["title"])}</h3>',
                  f'<p class="route-result"><strong>Expected result</strong>{e(r["expected"])}</p>',
                  f'<p><strong>Requirements</strong>{e(r["requirements"])}</p>',
                  f'<div class="actions"><a class="button light" href="{e(r["download"])}">Download {e(r["app"])} ↓</a><a class="text-link" href="{e(r["guide"])}">Quick start ↗</a></div>',
                  '<details><summary>Try the exercise and see its limits</summary>', f'<p><strong>Try this</strong>{e(r["exercise"])}</p>', f'<p><strong>Limits</strong>{e(r["limits"])}</p>',
                  f'<p><a href="{e(r["evidence"])}">Evidence and methodology ↗</a></p>', '</details>']
        if r.get('alternatives'):
            parts += ['<p class="route-alternatives">' + ' · '.join('<a href="'+e(a['url'])+'">'+e(a['label'])+' ↗</a>' for a in r['alternatives']) + '</p>']
        n = r['next']
        parts += [f'<details><summary>Then: {e(n["label"])}</summary><p>{e(n["exercise"])}</p><a href="{e(n["guide"])}">Follow the guide ↗</a>' + (f' <a href="{e(n["download"])}">Download ZIP ↓</a>' if n.get('download') else '') + '</details>', '</article>']
    parts += ['</div>', '<p class="start-scope">Verify the ZIP against SHA256SUMS.txt from its release before extraction. Use a fresh folder and private scratch data. Expected results are a comparison target, not evidence that you ran a check.</p>',
              f'<a class="text-link" href="{BASE}/blob/main/docs/START-HERE.md">Same guide on GitHub ↗</a>', '</section>', SITE_END, '']
    return '\n'.join(parts)


def replace_region(text, begin, end, body, before):
    if begin in text:
        start = text.index(begin); stop = text.index(end, start) + len(end)
        return text[:start] + body.rstrip() + text[stop:]
    return text.replace(before, body.rstrip() + '\n\n' + before, 1)


def run(check=False, site=None, profile=None):
    data = model()
    files = {ROOT / 'docs/START-HERE.md': '<!-- Generated from catalog/start-here.json and registry.json. -->\n\n' + markdown(data),
             ROOT / 'catalog/generated/start-here.html': site_html(data)}
    snippet = BEGIN + '\n' + markdown(data, True) + END
    targets = [(ROOT / 'README.md', '## Try the two newest complete workbenches')]
    if profile: targets.append((Path(profile) / 'README.md', '## Start here'))
    for path, before in targets:
        current = path.read_text(encoding='utf-8')
        assert BEGIN in current or before in current, 'README insertion point missing'
        files[path] = replace_region(current, BEGIN, END, snippet, before)
    if site:
        path = Path(site) / 'dist/index.html'; current = path.read_text(encoding='utf-8')
        marker = '<div class="section-rule shell"><span>SELECTED WORK</span>'
        assert SITE_BEGIN in current or marker in current, 'Site insertion point missing'
        files[path] = replace_region(current, SITE_BEGIN, SITE_END, site_html(data), marker)
    for path, body in files.items():
        expected = body.encode('utf-8')
        if check:
            if not path.exists() or path.read_text(encoding='utf-8') != body:
                raise ValueError('START_HERE_STALE ' + path.name)
        else:
            path.write_bytes(expected)
    print(json.dumps({'status': 'PASS' if check else 'GENERATED', 'routes': len(data['routes']), 'projections': len(files)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--site')
    parser.add_argument('--profile')
    args = parser.parse_args()
    run(args.check, args.site, args.profile)
