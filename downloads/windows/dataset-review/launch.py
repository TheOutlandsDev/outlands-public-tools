"""Original portable handoff around the unchanged Offline Dataset Review Workbench runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import webbrowser

ROOT=Path(__file__).resolve().parent


def check_package():
    manifest=json.loads((ROOT/'PACKAGE-MANIFEST.json').read_text(encoding='utf-8'));seen=set()
    for row in manifest['files']:
        name=row['path']
        if name.startswith('/') or ':' in name or '\\' in name or any(x in ('','.','..') for x in name.split('/')) or name.casefold() in seen:raise ValueError('Invalid package inventory.')
        seen.add(name.casefold());p=ROOT/name
        if not p.is_file() or p.is_symlink() or any(x.is_symlink() or getattr(x,'is_junction',lambda:False)() for x in (p,*p.parents)) or p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Package changed or incomplete. Extract a new verified ZIP.')
    if sys.platform!='win32' or sys.version_info[:3]!=(3,14,10) or Path(sys.executable).resolve()!=(ROOT/'runtime/python.exe').resolve() or not sys.flags.isolated:raise ValueError('Use the supplied Windows CMD launcher and bundled isolated runtime.')
    return manifest

def default_workspace(demo,a):
    if not os.environ.get('LOCALAPPDATA'):raise ValueError('Choose an existing local application-data parent or --workspace.')
    parent=Path(os.environ['LOCALAPPDATA'])
    if not parent.is_absolute() or not parent.is_dir():raise ValueError('Choose an existing local application-data parent.')
    for name in ('Outlands','DatasetReviewWorkbench'):
        parent=a.core._export_path(parent/name)
        if not parent.exists():a.mkdir(parent)
        if not parent.is_dir():raise ValueError('The default private parent is not a directory.')
    return parent/('fictional-demo' if demo else 'workspace')

def main():
    p=argparse.ArgumentParser(description='Offline Dataset Review Workbench portable Windows package',allow_abbrev=False)
    modes=p.add_mutually_exclusive_group();modes.add_argument('--demo',action='store_true');modes.add_argument('--exercise',action='store_true')
    p.add_argument('--workspace',type=Path);p.add_argument('--no-browser',action='store_true');p.add_argument('--check',action='store_true');p.add_argument('--cli',nargs=argparse.REMAINDER)
    args=p.parse_args()
    try:
        manifest=check_package();sys.path.insert(0,str(ROOT/'application'))
        from dataset_workbench import application as a
        if args.check:
            print(json.dumps(dict(status='PASS',runtime=sys.version.split()[0],application='0.1.0',package=manifest['package_version'],isolated=sys.flags.isolated==1,bundled_runtime=True)));return
        workspace=args.workspace or default_workspace(args.demo or args.exercise,a)
        if args.exercise and args.workspace is None:
            import uuid
            workspace=workspace.parent/('exercise-'+uuid.uuid4().hex)
        if not workspace.is_absolute() or workspace==ROOT or workspace.is_relative_to(ROOT):raise ValueError('Choose a fully spelled private workspace outside the extracted package.')
        if args.cli is not None:
            if not args.cli:raise ValueError('Supply an original CLI command after --cli.')
            from dataset_workbench import cli
            sys.argv=['workbench.py','--workspace',str(workspace),*args.cli];result=cli.main()
            if result is not None:print(json.dumps(result,ensure_ascii=True,allow_nan=False,sort_keys=True))
            return
        if args.exercise:
            sys.path.insert(0,str(ROOT));from review_demo import exercise
            print(json.dumps(exercise(workspace),sort_keys=True));print('Fictional exercise complete. Private records: '+str(workspace),flush=True);return
        create=not workspace.exists()
        if create:a.Workbench.initialize(workspace)
        from dataset_workbench import web
        with a.Workbench(workspace) as controller,web.LocalServer(('127.0.0.1',0),controller) as server:
            url='http://127.0.0.1:'+str(server.server_port)+'/'
            print('Offline Dataset Review Workbench | '+('DEMO WORKSPACE' if args.demo else 'PRIVATE WORKSPACE'),flush=True)
            print(('Created' if create else 'Reopened')+' private workspace: '+str(workspace),flush=True);print('Open '+url,flush=True)
            print('No automatic import or approval. A new instance includes the original fictional inbox sample. Existing instances are never reseeded.',flush=True)
            print('Use Stop local UI, or Ctrl+C here, before maintenance.',flush=True)
            if not args.no_browser:
                try:
                    if not webbrowser.open(url):print('Open the address above in your browser.',flush=True)
                except OSError:print('Open the address above in your browser.',flush=True)
            def interrupt(*_):raise KeyboardInterrupt
            if hasattr(signal,'SIGBREAK'):signal.signal(signal.SIGBREAK,interrupt)
            try:server.serve_forever(poll_interval=.2)
            except KeyboardInterrupt:pass
        print('Stopped. Saved records remain; unsaved browser drafts are not persisted.',flush=True)
    except Exception as exc:
        code=str(exc) if isinstance(exc,ValueError) else 'OPERATION_REFUSED'
        p.exit(2,'Could not complete: '+code+'\nPreserve the workspace. Read START-HERE.txt; no automatic reset or stale-lock recovery.\n')

if __name__=='__main__':main()
