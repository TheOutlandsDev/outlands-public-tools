"""Explicit file-based CLI for private project revisions and static checks."""
import json
import sys
from developer import jobs,runtime as r


def main():
    parser=r.Parser(prog='developer-workspace',allow_abbrev=False);parser.add_argument('--workspace',required=True);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('init','demo','projects','artifacts','backup'):sub.add_parser(name)
    p=sub.add_parser('recover');p.add_argument('--confirm-stopped',action='store_true')
    for name in ('import','edit','validate','review'):p=sub.add_parser(name);p.add_argument('--file',required=True)
    p=sub.add_parser('show');p.add_argument('--project',required=True);p.add_argument('--version',type=int)
    p=sub.add_parser('history');p.add_argument('--project',required=True)
    p=sub.add_parser('artifact');p.add_argument('--id',required=True)
    p=sub.add_parser('compare');p.add_argument('--project',required=True);p.add_argument('--left',required=True,type=int);p.add_argument('--right',required=True,type=int)
    p=sub.add_parser('export');p.add_argument('--artifact',required=True)
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=0);args=parser.parse_args()
    if args.command=='recover' and not args.confirm_stopped:raise r.WorkbenchError('STOPPED_ASSERTION_REQUIRED')
    r.configure(args.workspace,create=args.command in ('init','demo'),confirm_stopped=args.command=='recover')
    from developer import application as app
    if args.command in ('init','demo'):r.initialize()
    if args.command=='init':return dict(status='INITIALIZED',**app.projects())
    if args.command=='demo':return app.demo()
    if args.command=='recover':return dict(status='SESSION_RECOVERED',automatically_replayed=False,**app.projects())
    if args.command=='projects':return app.projects()
    if args.command=='artifacts':return app.artifacts()
    if args.command in ('import','edit','validate','review'):
        raw=r.read_bytes(r.local_path(args.file))
        if args.command=='import':return app.import_project(raw)
        if args.command=='edit':return app.edit(raw)
        if args.command=='review':return app.review(raw)
        return jobs.wait(app.validate(raw)['job_id'])
    if args.command=='show':return app.project(args.project,args.version)
    if args.command=='history':return app.history(args.project)
    if args.command=='artifact':return app.artifact(args.id)
    if args.command=='compare':return app.compare(args.project,args.left,args.right)
    if args.command=='export':return app.export(args.artifact)
    if args.command=='backup':return app.backup()
    from developer.web import serve
    serve(args.port);return dict(status='STOPPED')


if __name__=='__main__':
    code=0;value=None
    try:value=main()
    except r.WorkbenchError as error:code=2;value=dict(error=str(error))
    except KeyboardInterrupt:code=130;value=dict(error='INTERRUPTED')
    except Exception:code=2;value=dict(error='OPERATION_REFUSED')
    finally:
        try:jobs.close();r.close()
        except Exception:code=2;value=dict(error='SESSION_CLEANUP_REFUSED')
    if value is not None:print(json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True))
    sys.exit(code)
