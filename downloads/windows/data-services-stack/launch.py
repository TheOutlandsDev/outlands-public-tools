"""Windows handoff around the unchanged, pinned Data & Services Stack."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import uuid
import webbrowser

ROOT=Path(__file__).resolve().parent

def check_package():
    manifest=json.loads((ROOT/'PACKAGE-MANIFEST.json').read_text(encoding='utf-8'));seen=set()
    for row in manifest['files']:
        name=row['path']
        if name.startswith('/') or ':' in name or '\\' in name or any(x in ('','.','..') for x in name.split('/')) or name.casefold() in seen:raise ValueError('PACKAGE_INVENTORY_INVALID')
        seen.add(name.casefold());p=ROOT/name
        if not p.is_file() or p.is_symlink() or any(x.is_symlink() or getattr(x,'is_junction',lambda:False)() for x in (p,*p.parents)) or p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('PACKAGE_CHANGED_OR_INCOMPLETE')
    if sys.platform!='win32' or sys.version_info[:3]!=(3,14,10) or Path(sys.executable).resolve()!=(ROOT/'runtime/python.exe').resolve() or not sys.flags.isolated:raise ValueError('BUNDLED_ISOLATED_WINDOWS_RUNTIME_REQUIRED')
    return manifest

def private_parent(files):
    if not os.environ.get('LOCALAPPDATA'):raise ValueError('LOCAL_APPLICATION_DATA_UNAVAILABLE')
    parent=Path(os.environ['LOCALAPPDATA'])
    if not parent.is_absolute() or not parent.is_dir():raise ValueError('EXISTING_PRIVATE_PARENT_REQUIRED')
    for name in ('Outlands','DataServicesStack'):
        parent=files.selected(parent/name,output=True)
        if not parent.exists():files.mkdir(parent)
        with files.directory(parent):pass
    return parent

def main():
    p=argparse.ArgumentParser(description='Data & Services Stack portable Windows package',allow_abbrev=False)
    modes=p.add_mutually_exclusive_group();modes.add_argument('--demo',action='store_true');modes.add_argument('--exercise',action='store_true')
    p.add_argument('--workspace',type=Path);p.add_argument('--reports',type=Path)
    p.add_argument('--no-browser',action='store_true');p.add_argument('--check',action='store_true')
    p.add_argument('--cli',nargs=argparse.REMAINDER,help='Original CLI command; stop all journal processes first')
    args=p.parse_args()
    try:
        manifest=check_package();sys.path.insert(0,str(ROOT/'application'))
        from data_services import files
        from data_services.service import Stack
        if args.check:
            print(json.dumps(dict(status='PASS',runtime=sys.version.split()[0],application='0.2.0',package=manifest['package_version'],isolated=sys.flags.isolated==1,bundled_runtime=True)))
            return 0
        if args.exercise and (args.cli is not None or args.reports is not None):raise ValueError('EXERCISE_OPTIONS_CONFLICT')
        workspace=args.workspace
        if workspace is None:
            parent=private_parent(files);workspace=parent/(('exercise-'+uuid.uuid4().hex) if args.exercise else ('fictional-demo' if args.demo else 'workspace'))
        if not workspace.is_absolute() or workspace==ROOT or workspace.is_relative_to(ROOT):raise ValueError('PRIVATE_WORKSPACE_OUTSIDE_PACKAGE_REQUIRED')
        workspace=files.selected(workspace,output=True)
        if args.cli is not None:
            if not args.cli or args.reports is not None:raise ValueError('ORIGINAL_CLI_COMMAND_REQUIRED')
            from data_services.cli import main as original
            return original(['--workspace',str(workspace),*args.cli])
        if args.exercise:
            sys.path.insert(0,str(ROOT));from data_demo import exercise
            print(json.dumps(exercise(workspace),sort_keys=True))
            print('Fictional exercise complete. Private journal and exports: '+str(workspace),flush=True)
            return 0
        create=not workspace.exists()
        if create:Stack.initialize(workspace)
        reports=args.reports or workspace.parent/('reports-'+uuid.uuid4().hex)
        if not reports.is_absolute() or reports==ROOT or reports.is_relative_to(ROOT):raise ValueError('NEW_PRIVATE_REPORT_DIRECTORY_OUTSIDE_PACKAGE_REQUIRED')
        from data_services.workbench import Workbench
        from data_services.web import LocalServer
        with Stack(workspace) as app:
            controller=Workbench(app,reports)
            try:
                server=LocalServer(('127.0.0.1',0),controller)
                try:
                    url='http://127.0.0.1:'+str(server.server_port)+'/'
                    print('Data & Services Stack | FAKE TRANSPORT ONLY',flush=True)
                    print(('Created' if create else 'Reopened')+' private journal: '+str(workspace),flush=True)
                    print('Fresh private report directory: '+str(reports),flush=True)
                    print('Open '+url,flush=True)
                    print('Nothing is configured, run or dispatched automatically. Existing journals are never reseeded.',flush=True)
                    print('Use Stop local UI, or Ctrl+C here, before maintenance. Preserve the complete stopped journal and all prior report directories.',flush=True)
                    if not args.no_browser:
                        try:
                            if not webbrowser.open(url):print('Open the address above in your browser.',flush=True)
                        except OSError:print('Open the address above in your browser.',flush=True)
                    def interrupt(*_):raise KeyboardInterrupt
                    if hasattr(signal,'SIGBREAK'):signal.signal(signal.SIGBREAK,interrupt)
                    try:server.serve_forever(poll_interval=.2)
                    except KeyboardInterrupt:pass
                finally:server.stopping.set();server.server_close()
            finally:controller.close()
        print('Stopped. Saved journal and previous reports remain; browser drafts are not saved.',flush=True)
        return 0
    except Exception as error:
        code=str(error) if isinstance(error,ValueError) else 'OPERATION_REFUSED'
        p.exit(2,'Could not complete: '+code+'\nPreserve the private journal and reports. Read START-HERE.txt; no automatic recovery or replay.\n')

if __name__=='__main__':raise SystemExit(main())
