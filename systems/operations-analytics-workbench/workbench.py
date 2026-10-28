"""CLI for explicit private analytics scenarios and a fictional full workflow."""
import json
import sys
from operations_analytics import runtime


def main():
    parser=runtime.Parser(prog='operations-analytics-workbench',allow_abbrev=False);parser.add_argument('--workspace',required=True)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('init','demo','list','backup'):sub.add_parser(name)
    recover=sub.add_parser('recover');recover.add_argument('--confirm-stopped',action='store_true')
    for name in ('show','plan','history','export'):
        p=sub.add_parser(name);p.add_argument('--project',required=True)
        if name in ('show','plan'):p.add_argument('--revision',type=int)
    p=sub.add_parser('import');p.add_argument('--file',required=True);p.add_argument('--expected')
    for name in ('ingest','attach-planning'):
        p=sub.add_parser(name);p.add_argument('--project',required=True);p.add_argument('--file' if name=='ingest' else '--directory',required=True);p.add_argument('--expected',required=True)
    p=sub.add_parser('review');p.add_argument('--file',required=True)
    p=sub.add_parser('compare');p.add_argument('--project',required=True);p.add_argument('--left',required=True,type=int);p.add_argument('--right',required=True,type=int)
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=0)
    args=parser.parse_args()
    if args.command=='recover' and not args.confirm_stopped:raise runtime.WorkbenchError('STOPPED_ASSERTION_REQUIRED')
    runtime.configure(args.workspace,create=args.command in ('init','demo'),confirm_stopped=args.command=='recover')
    from operations_analytics import application as app
    if args.command in ('init','demo'):runtime.initialize()
    if args.command=='init':return dict(status='INITIALIZED',**app.projects())
    if args.command=='demo':return app.demo()
    if args.command=='list':return app.projects()
    if args.command=='recover':return dict(status='SESSION_RECOVERED',automatically_replayed=False,**app.projects())
    if args.command=='import':return app.import_file(args.file,args.expected)
    if args.command=='ingest':return app.ingest(args.project,args.file,args.expected)
    if args.command=='attach-planning':return app.attach_planning(args.project,args.directory,args.expected)
    if args.command=='compare':return app.compare(args.project,args.left,args.right)
    if args.command=='review':return app.review(runtime.read_bytes(runtime.local_path(args.file)))
    if args.command=='backup':return app.backup()
    if args.command in ('show','plan'):return getattr(app,args.command)(args.project,args.revision)
    if args.command=='serve':
        from operations_analytics.web import serve
        serve(args.port);return dict(status='STOPPED')
    return getattr(app,args.command)(args.project)


if __name__=='__main__':
    code=0;value=None
    try:value=main()
    except runtime.WorkbenchError as error:code=2;value=dict(error=str(error))
    except KeyboardInterrupt:code=130;value=dict(error='INTERRUPTED')
    except Exception:code=2;value=dict(error='OPERATION_REFUSED')
    finally:
        try:runtime.close()
        except Exception:code=2;value=dict(error='SESSION_CLEANUP_REFUSED')
    if value is not None:print(json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True))
    sys.exit(code)
