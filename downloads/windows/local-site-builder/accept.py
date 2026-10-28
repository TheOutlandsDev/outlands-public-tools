"""Extract a fresh package and qualify it with only its own Node/native modules."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import zipfile
from build import FILENAME,PREFIX,sha

def accept(packages,workspace,browser_module=None):
    if os.name!='nt' or not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_EXTERNAL_WINDOWS_WORKSPACE_REQUIRED')
    r=json.loads((packages/'release-receipt.json').read_bytes());raw=(packages/FILENAME).read_bytes();assert sha(raw)==r['sha256']
    workspace.mkdir()
    with zipfile.ZipFile(packages/FILENAME) as z:
        m=json.loads(z.read(PREFIX+'PACKAGE-MANIFEST.json'));names=z.namelist()
        assert len(names)==len(set(names))==r['files']
        assert set(names)=={PREFIX+x['path'] for x in m['files']}|{PREFIX+'PACKAGE-MANIFEST.json'}
        for row in m['files']:
            n=row['path'];assert not n.startswith('/') and not any(x in ('','..','.') for x in n.split('/')) and ':' not in n and '\\' not in n
            b=z.read(PREFIX+n);assert len(b)==row['bytes'] and sha(b)==row['sha256']
        z.extractall(workspace/'fresh extracted folder')
    root=workspace/'fresh extracted folder'/PREFIX.rstrip('/');private=workspace/'private';private.mkdir()
    command=[str(root/'runtime/node.exe'),str(Path(__file__).with_name('accept.js')),str(root),str(private)]
    if browser_module:command.append(str(browser_module))
    result=subprocess.run(command,cwd=workspace,capture_output=True,timeout=360)
    (private/'acceptance-process.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:
        print(result.stderr.decode('utf-8',errors='replace').strip())
        raise AssertionError('Acceptance failed; private logs retained.')
    accepted=json.loads((private/'observed.json').read_bytes());accepted.update(schema=1,package_sha256=r['sha256'],packaging_source=r['packaging_source'],manual_node_free_pc='not_performed',explorer_and_default_browser='not_manually_verified')
    if browser_module:assert len(accepted['checks'])==16 and accepted['browser']
    (packages/'acceptance.json').write_text(json.dumps(accepted,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(accepted))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser-module',type=Path);a=p.parse_args();accept(a.packages,a.workspace,a.browser_module)
