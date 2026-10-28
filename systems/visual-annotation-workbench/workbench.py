"""Explicit private instances; fictional demo and local visual review commands."""
import json
import sys
from visual_workbench import runtime


def main():
    parser=runtime.Parser(prog='visual-annotation-workbench',allow_abbrev=False);parser.add_argument('--workspace',required=True)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('init','demo','list','backup'):sub.add_parser(name)
    p=sub.add_parser('recover');p.add_argument('--confirm-stopped',action='store_true')
    for name in ('create','add-view','correct','review'):
        p=sub.add_parser(name);p.add_argument('--file',required=True)
    for name in ('views','show','history','evaluate','export'):
        p=sub.add_parser(name);p.add_argument('--dataset',required=True)
        if name in ('show','history','evaluate'):
            p.add_argument('--specimen',required=True);p.add_argument('--view',required=True)
        if name=='show':p.add_argument('--version',type=int)
        if name=='export':p.add_argument('--mode',choices=('training','evaluation'),required=True)
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=0)
    args=parser.parse_args()
    if args.command=='recover' and not args.confirm_stopped:raise runtime.WorkbenchError('STOPPED_ASSERTION_REQUIRED')
    runtime.configure(args.workspace,create=args.command in ('init','demo'),confirm_stopped=args.command=='recover')
    from visual_workbench import application as app
    if args.command in ('init','demo'):runtime.initialize()
    if args.command=='init':return dict(status='INITIALIZED',**app.datasets())
    if args.command=='demo':return app.demo()
    if args.command=='recover':return dict(status='SESSION_RECOVERED',automatically_replayed=False,**app.datasets())
    if args.command=='list':return app.datasets()
    if args.command in ('create','add-view','correct','review'):return getattr(app,args.command.replace('-','_'))(runtime.read_bytes(runtime.local_path(args.file)))
    if args.command=='backup':return app.backup()
    if args.command=='views':return app.views(args.dataset)
    if args.command=='export':return app.export(args.dataset,args.mode)
    if args.command in ('history','evaluate'):return getattr(app,args.command)(args.dataset,args.specimen,args.view)
    if args.command=='show':return app.show(args.dataset,args.specimen,args.view,args.version)
    from visual_workbench.web import serve
    serve(args.port);return dict(status='STOPPED')


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
