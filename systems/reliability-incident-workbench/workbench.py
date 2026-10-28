"""Explicit private-instance CLI for supplied health observations only."""
import json
import sys
from reliability import runtime as r

def main():
    parser=r.Parser(prog='reliability-incident-workbench',allow_abbrev=False);parser.add_argument('--workspace',required=True);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('init','demo','list','backup'):sub.add_parser(name)
    p=sub.add_parser('recover');p.add_argument('--confirm-stopped',action='store_true')
    for name in ('create','import','act','export'):p=sub.add_parser(name);p.add_argument('--file',required=True)
    for name in ('show','history','compare'):
        p=sub.add_parser(name);p.add_argument('--case',required=True)
        if name=='show':p.add_argument('--version',type=int)
        if name=='compare':p.add_argument('--left',type=int,required=True);p.add_argument('--right',type=int,required=True)
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=0);args=parser.parse_args()
    if args.command=='recover' and not args.confirm_stopped:raise r.WorkbenchError('STOPPED_ASSERTION_REQUIRED')
    r.configure(args.workspace,create=args.command in ('init','demo'),confirm_stopped=args.command=='recover')
    from reliability import application as app
    if args.command in ('init','demo'):r.initialize()
    if args.command=='init':return dict(status='INITIALIZED',**app.cases())
    if args.command=='demo':return app.demo()
    if args.command=='recover':return dict(status='SESSION_RECOVERED',automatically_replayed=False,**app.cases())
    if args.command=='list':return app.cases()
    if args.command in ('create','import','act','export'):
        raw=r.read_bytes(r.local_path(args.file))
        return app.create(raw,imported=args.command=='import') if args.command in ('create','import') else getattr(app,args.command)(raw)
    if args.command=='show':return app.case(args.case,args.version)
    if args.command=='history':return app.history(args.case)
    if args.command=='compare':return app.compare(args.case,args.left,args.right)
    if args.command=='backup':return app.backup()
    from reliability.web import serve
    serve(args.port);return dict(status='STOPPED')

if __name__=='__main__':
    code=0;value=None
    try:value=main()
    except r.WorkbenchError as error:code=2;value=dict(error=str(error))
    except KeyboardInterrupt:code=130;value=dict(error='INTERRUPTED')
    except Exception:code=2;value=dict(error='OPERATION_REFUSED')
    finally:
        try:r.close()
        except Exception:code=2;value=dict(error='SESSION_CLEANUP_REFUSED')
    if value is not None:print(json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True))
    sys.exit(code)
