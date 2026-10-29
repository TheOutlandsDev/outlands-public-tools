"""Private release/update planner CLI; no target execution, installation or network adapters."""
import json
import sys
from releases import runtime as r
def main():
    parser=r.Parser(prog='release-update-workbench',allow_abbrev=False);parser.add_argument('--workspace',required=True);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('init','demo','overview','history','backup-index'):sub.add_parser(name)
    p=sub.add_parser('recover');p.add_argument('--confirm-stopped',action='store_true');p.add_argument('--actor',default='local_operator');p.add_argument('--reason',default='Operator asserts all instance processes stopped; review retained output')
    for name in ('capture','compare','make-plan','review','export'):p=sub.add_parser(name);p.add_argument('--file',required=True)
    p=sub.add_parser('inspect');p.add_argument('--kind',choices=('candidate','comparison','plan'),required=True);p.add_argument('--id',required=True)
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=0);args=parser.parse_args()
    if args.command=='recover' and not args.confirm_stopped:raise r.WorkbenchError('STOPPED_ASSERTION_REQUIRED')
    r.configure(args.workspace,create=args.command in ('init','demo'),confirm_stopped=args.command=='recover')
    from releases import application as app
    if args.command in ('init','demo'):r.initialize()
    if args.command=='init':return dict(status='INITIALIZED',**app.overview())
    if args.command=='demo':return app.demo()
    if args.command=='recover':return app.recover(r.encode(dict(actor=args.actor,reason=args.reason)))
    if args.command in ('overview','history'):return getattr(app,args.command)()
    if args.command=='backup-index':return app.backup_index()
    if args.command in ('capture','compare','make-plan','review','export'):
        from releases.contracts import selector
        selector(args.file);return getattr(app,args.command.replace('-','_'))(r.read_bytes(r.local_path(args.file)))
    if args.command=='inspect':return app.inspect(args.kind,args.id)
    from releases.web import serve
    serve(args.port);return dict(status='STOPPED')
if __name__=='__main__':
    code=0;value=None
    try:value=main()
    except r.WorkbenchError as error:code=2;value=dict(error=str(error))
    except KeyboardInterrupt:code=130;value=dict(error='INTERRUPTED_REVIEW_PENDING_JOB')
    except Exception:code=2;value=dict(error='OPERATION_REFUSED')
    finally:
        try:r.close()
        except Exception:code=2;value=dict(error='SESSION_CLEANUP_REFUSED')
    if value is not None:print(json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True))
    sys.exit(code)
