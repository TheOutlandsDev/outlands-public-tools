"""Original portable handoff around the unchanged Developer Workspace runtime."""
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
    manifest=json.loads((ROOT/'PACKAGE-MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        path=ROOT/row['path']
        if not path.is_file() or path.is_symlink() or path.stat().st_size!=row['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Package changed or is incomplete. Preserve your workspace and extract a fresh download.')
    if Path(sys.executable).resolve()!=(ROOT/'runtime/python.exe').resolve():
        raise ValueError('Use one of the supplied CMD launchers so the bundled runtime is used.')
    return manifest


def default_workspace(demo,r):
    if not os.environ.get('LOCALAPPDATA'):raise ValueError('Windows local application-data folder is unavailable; choose --workspace.')
    parent=Path(os.environ['LOCALAPPDATA'])
    if not parent.is_absolute() or not parent.is_dir():raise ValueError('Choose an existing local application-data parent.')
    for name in ('Outlands','DeveloperWorkspace'):
        parent=parent/name
        with r.io_errors():parent=r.guarded._export_path(parent)
        if not parent.exists():r.mkdir(parent)
        if not parent.is_dir():raise ValueError('The default private parent is not a directory.')
    return parent/('fictional-demo' if demo else 'workspace')


def main():
    p=argparse.ArgumentParser(description='Developer Workspace portable Windows package',allow_abbrev=False)
    p.add_argument('--demo',action='store_true',help='Create/reopen the separate fictional tutorial workspace')
    p.add_argument('--workspace',type=Path,help='Existing private workspace or a new path with an existing parent')
    p.add_argument('--no-browser',action='store_true')
    p.add_argument('--check',action='store_true')
    p.add_argument('--cli',nargs=argparse.REMAINDER,help='Advanced original CLI command; stop the server first')
    args=p.parse_args();r=None;jobs=None
    try:
        manifest=check_package()
        sys.path.insert(0,str(ROOT/'application'))
        from developer import application as app,runtime as r,jobs
        if args.check:
            print(json.dumps(dict(status='PASS',runtime=sys.version.split()[0],application='0.1.0',package=manifest['package_version'],isolated=sys.flags.isolated==1,bundled_runtime=True)))
            return
        workspace=args.workspace
        if workspace is None:workspace=default_workspace(args.demo,r)
        if not workspace.is_absolute() or workspace==ROOT or workspace.is_relative_to(ROOT):
            raise ValueError('Choose a fully spelled private workspace outside the extracted package.')
        if args.cli is not None:
            if not args.cli:raise ValueError('Supply an original CLI command after --cli.')
            import workbench
            sys.argv=['workbench.py','--workspace',str(workspace),*args.cli]
            result=workbench.main()
            if result is not None:print(json.dumps(result,ensure_ascii=True,allow_nan=False,sort_keys=True))
            return
        create=not workspace.exists()
        r.configure(workspace,create=create)
        if create:
            r.initialize()
            if args.demo:
                app.import_project(r.read_bytes(r.SOURCE/'examples/sample-project.json'))
        app.projects() # Validate the existing store before opening the browser.
        from developer import web
        with web.LocalServer(('127.0.0.1',0),web.Handler) as server:
            url='http://127.0.0.1:'+str(server.server_port)+'/'
            print('Developer Workspace | '+('DEMO WORKSPACE' if args.demo else 'PRIVATE WORKSPACE'),flush=True)
            print(('Created' if create else 'Reopened')+' private workspace: '+str(workspace),flush=True)
            print('Open '+url,flush=True)
            print('Demo starting data is invented. Later inputs stay private. Existing workspaces are never reseeded.',flush=True)
            print('Use Stop local server in the page, or Ctrl+C here, before maintenance.',flush=True)
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
        # Core errors use fixed public codes. No SQL, source, token or credentials are printed.
        code=str(exc) if isinstance(exc,ValueError) else 'OPERATION_REFUSED'
        p.exit(2,'Could not complete: '+code+'\nPreserve the workspace. Read START-HERE.txt; no automatic reset or stale-lock recovery.\n')
    finally:
        try:
            if jobs is not None:jobs.close()
        finally:
            if r is not None:r.close()


if __name__=='__main__':main()
