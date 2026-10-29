"""Windows handoff around the unchanged public Corpus & Model Workbench."""
import argparse,hashlib,json,os,signal,sys,webbrowser
from pathlib import Path
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

def default_workspace(demo,r):
    if not os.environ.get('LOCALAPPDATA'):raise ValueError('Choose --workspace or an existing Windows application-data parent.')
    parent=Path(os.environ['LOCALAPPDATA'])
    if not parent.is_absolute() or not parent.is_dir():raise ValueError('Choose an existing private parent.')
    for name in ('Outlands','CorpusModelWorkbench'):
        with r.io_errors():parent=r.guarded._export_path(parent/name)
        if not parent.exists():r._mkdir(parent)
        if not parent.is_dir():raise ValueError('Private parent is not a directory.')
    return parent/('fictional-demo' if demo else 'workspace')

def portable_handler(base):
    class PortableHandler(base):
        def send(self,value,status=200,content_type='application/json'):
            if content_type=='text/html' and isinstance(value,str):
                value=value.replace('</head>','<style id="outlands-portable-layout">#message{overflow-wrap:anywhere}</style></head>',1)
            return super().send(value,status,content_type)
    return PortableHandler

def main():
    parser=argparse.ArgumentParser(description='Corpus & Model Workbench Windows handoff',allow_abbrev=False)
    modes=parser.add_mutually_exclusive_group();modes.add_argument('--demo',action='store_true');modes.add_argument('--exercise',action='store_true')
    parser.add_argument('--workspace',type=Path);parser.add_argument('--no-browser',action='store_true');parser.add_argument('--check',action='store_true');parser.add_argument('--cli',nargs=argparse.REMAINDER)
    args=parser.parse_args();r=None
    try:
        manifest=check_package();sys.path.insert(0,str(ROOT/'application'))
        from workbench import corpus,runtime as r
        if args.check:
            import sqlite3
            with sqlite3.connect(':memory:') as db:db.execute('CREATE VIRTUAL TABLE fts_probe USING fts5(text)')
            print(json.dumps(dict(status='PASS',runtime=sys.version.split()[0],application='0.1.1',package=manifest['package_version'],isolated=sys.flags.isolated==1,bundled_runtime=True,sqlite_fts5=True)));return
        workspace=args.workspace or default_workspace(args.demo or args.exercise,r)
        if args.exercise and args.workspace is None:
            import uuid
            workspace=workspace.parent/('exercise-'+uuid.uuid4().hex)
        if not workspace.is_absolute() or workspace==ROOT or workspace.is_relative_to(ROOT):raise ValueError('Choose a fully spelled private workspace outside the extracted package.')
        if args.cli is not None:
            if not args.cli:raise ValueError('Supply an original command after --cli.')
            sys.argv=['workbench.py','--workspace',str(workspace),*args.cli];result=corpus.main()
            if result is not None:print(json.dumps(result,ensure_ascii=True,allow_nan=False,sort_keys=True))
            return
        if args.exercise:
            sys.path.insert(0,str(ROOT));from corpus_demo import exercise
            print(json.dumps(exercise(workspace),sort_keys=True));print('Fictional exercise complete. Private records: '+str(workspace),flush=True);return
        created=not workspace.exists();r.configure(workspace,create=created)
        if created:corpus.initialize()
        corpus.status()
        if args.demo:
            from workbench.demo import FictionalClient
            r.set_client(FictionalClient())
        from workbench import web
        web.STOPPING=False
        print('Corpus & Model Workbench | '+('FICTIONAL MODELS' if args.demo else 'PRIVATE WORKSPACE'),flush=True)
        print(('Created' if created else 'Reopened')+' private workspace: '+str(workspace),flush=True)
        print('No automatic import, approval, comparison, embedding or discussion. Existing instances are not reseeded.',flush=True)
        with web.LocalServer(('127.0.0.1',0),portable_handler(web.Handler)) as server:
            url='http://127.0.0.1:'+str(server.server_port)+'/'
            print('Open '+url,flush=True)
            if not args.no_browser:
                try:webbrowser.open(url)
                except OSError:print('Open the address above in your browser.',flush=True)
            def interrupt(*_):raise KeyboardInterrupt
            if hasattr(signal,'SIGBREAK'):signal.signal(signal.SIGBREAK,interrupt)
            try:server.serve_forever(poll_interval=.2)
            except KeyboardInterrupt:pass
            finally:
                with web.LOCK:web.STOPPING=True
        web.drain_jobs()
        print('Stopped. Saved records remain. Unsaved browser drafts are not persisted.',flush=True)
    except Exception as exc:
        code=str(exc) if isinstance(exc,ValueError) else 'OPERATION_REFUSED'
        parser.exit(2,'Could not complete: '+code+'\nPreserve the workspace. Read START-HERE.txt before maintenance.\n')
    finally:
        # Preserve ownership until every original background worker has stopped.
        if r is not None:
            if 'workbench.web' in sys.modules:sys.modules['workbench.web'].drain_jobs()
            r.close()

if __name__=='__main__':main()
