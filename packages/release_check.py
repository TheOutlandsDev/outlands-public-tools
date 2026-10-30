"""Independent checksum, exact member and fixed component review before publication."""
import json
from pathlib import Path
import zipfile
from build import digest,verify_archive,public_tree,SUPPLEMENTS,git

def verify_release(output):
    output=Path(output);plan=json.loads(git('show','HEAD:packages/catalog.json'))
    catalog=json.loads((output/'catalog.json').read_bytes());matrix=json.loads((output/'release-matrix.json').read_bytes());revision=git('rev-parse','HEAD').decode().strip()
    if catalog['source_revision']!=plan['source_revision'] or catalog['packaging_revision']!=revision or catalog['tag']!=plan['tag']:raise ValueError('RELEASE_PIN_MISMATCH')
    if matrix!={k:catalog[k] for k in ('source_revision','packaging_revision','downloads')}:raise ValueError('MATRIX_MISMATCH')
    expected={'catalog.json','release-matrix.json','SHA256SUMS.txt'}|{r['filename'] for r in catalog['downloads']}
    if {p.name for p in output.iterdir()}!=expected or len(catalog['downloads'])!=9:raise ValueError('EXACT_RELEASE_ASSETS_REQUIRED')
    lines=(output/'SHA256SUMS.txt').read_text(encoding='ascii').splitlines()
    listed={}
    for line in lines:
        pin,name=line.split('  ',1)
        if name in listed or name not in expected or name=='SHA256SUMS.txt':raise ValueError('CHECKSUM_LIST_INVALID')
        listed[name]=pin
    if set(listed)!=expected-{'SHA256SUMS.txt'} or any(digest((output/n).read_bytes())!=pin for n,pin in listed.items()):raise ValueError('RELEASE_CHECKSUM_MISMATCH')
    source=public_tree(plan['source_revision']);supplements={p:git('show','HEAD:'+p) for p in SUPPLEMENTS}
    component_paths={'tools/'+n for g in plan['groups'] for n in g['tools']}|{'systems/'+n for n in plan['systems']}
    if len(component_paths)!=119 or len(plan['systems'])!=17:raise ValueError('EXPECTED_119_COMPONENT_SNAPSHOT')
    for record in catalog['downloads']:
        body=(output/record['filename']).read_bytes();manifest=verify_archive(body)
        if len(body)!=record['bytes'] or digest(body)!=record['sha256'] or len(manifest['files'])+1!=record['files']:raise ValueError('ASSET_METADATA_MISMATCH')
        if manifest['source_revision']!=plan['source_revision'] or manifest['packaging_revision']!=revision:raise ValueError('ARCHIVE_PIN_MISMATCH')
        expected_components=component_paths if record['id']=='complete' else {'tools/'+n for g in plan['groups'] if g['id']==record['id'] for n in g['tools']}
        if set(manifest['components'])!=expected_components or len(manifest['components'])!=record['components']:raise ValueError('ARCHIVE_COMPONENT_MISMATCH')
        with zipfile.ZipFile(output/record['filename']) as z:
            prefix=z.namelist()[0].split('/')[0]+'/'
            for name,row in manifest['files'].items():
                raw=z.read(prefix+name)
                if name in supplements:
                    if raw!=supplements[name]:raise ValueError('PACKAGING_BYTE_MISMATCH')
                elif name in source:
                    if raw!=source[name]:raise ValueError('PUBLISHED_SOURCE_BYTE_MISMATCH')
                elif name!='START-HERE.md':raise ValueError('UNREVIEWED_EXTRA_MEMBER')
            if record['id']=='complete' and not set(source)<=set(manifest['files']):raise ValueError('MISSING_SOURCE')
    return dict(status='PASS',components=119,tools=102,systems=17,packages=9,assets=12,source_revision=plan['source_revision'],packaging_revision=revision)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);print(json.dumps(verify_release(p.parse_args().output)))
