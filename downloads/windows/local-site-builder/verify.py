"""Independently audit every delivered file against official runtime and locked npm source."""
import argparse
import json
from pathlib import Path
import zipfile
from build import APP_SOURCE,APP_SHA,RUNTIME_VERSION,RUNTIME_SHA,FILENAME,PREFIX,NATIVE,encoded,git,payload,sha,validate_native

def verify(packages,accepted=False):
    r=json.loads((packages/'release-receipt.json').read_bytes());head=git('rev-parse','HEAD').decode().strip()
    assert r['app_source']==APP_SOURCE and r['source_zip_sha256']==APP_SHA and r['packaging_source']==head
    assert r['runtime_version']==RUNTIME_VERSION and r['runtime_sha256']==RUNTIME_SHA and r['dependencies']==86
    body=(packages/FILENAME).read_bytes();assert sha(body)==r['sha256'] and len(body)==r['bytes']
    expected=payload()
    with zipfile.ZipFile(packages/FILENAME) as z:
        native=z.read(PREFIX+NATIVE);validate_native(native);assert sha(native)==r['native']['native_sha256']
        info=json.loads(z.read(PREFIX+'NATIVE-ORIGIN.json'));assert info==r['native'] and info['version']=='13.0.3' and info['node_api']==10 and info['path']==NATIVE
        assert native==expected[NATIVE]
        expected['NATIVE-ORIGIN.json']=encoded(info)
        expected['PACKAGE-MANIFEST.json']=encoded(dict(schema=1,package_version='1.0.2-windows.1',app_source=APP_SOURCE,packaging_source=head,runtime=RUNTIME_VERSION,files=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(expected.items())]))
        names=z.namelist();assert len(names)==len(set(names))==len(expected)==r['files']
        assert set(names)=={PREFIX+n for n in expected}
        for n,b in expected.items():assert z.read(PREFIX+n)==b,n
    if accepted:
        a=json.loads((packages/'acceptance.json').read_bytes());assert a['status']=='PASS' and a['browser'] is True
        assert a['core_tests']==32 and a['core_skips']==0 and len(a['checks'])==16
        assert a['package_sha256']==r['sha256'] and a['packaging_source']==head and a['node']==RUNTIME_VERSION
    print(json.dumps(dict(status='PASS',files=len(expected),dependencies=86,native_binary='unchanged SHA512-locked npm prebuild; PE and exact upstream bytes verified',package_sha256=r['sha256'])))
    return r
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--accepted',action='store_true');a=p.parse_args();verify(a.packages,a.accepted)
