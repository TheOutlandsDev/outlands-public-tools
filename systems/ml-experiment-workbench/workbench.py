"""Explicit private experiment CLI and fictional complete workflow."""
import json
import sys
from ml_workbench import runtime as r


def main():
    parser=r.Parser(prog='ml-experiment-workbench',allow_abbrev=False);parser.add_argument('--workspace',required=True);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('init','demo','list','datasets','backup'):sub.add_parser(name)
    p=sub.add_parser('recover');p.add_argument('--confirm-stopped',action='store_true')
    for name in ('import','prepare','review'):
        p=sub.add_parser(name);p.add_argument('--file',required=True)
    p=sub.add_parser('example');p.add_argument('--dataset',required=True)
    for name in ('show','evaluate','export'):
        p=sub.add_parser(name);p.add_argument('--experiment',required=True)
        if name=='evaluate':p.add_argument('--expected',required=True)
    p=sub.add_parser('compare');p.add_argument('--left',required=True);p.add_argument('--right',required=True)
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=0);args=parser.parse_args()
    if args.command=='recover' and not args.confirm_stopped:raise r.WorkbenchError('STOPPED_ASSERTION_REQUIRED')
    r.configure(args.workspace,create=args.command in ('init','demo'),confirm_stopped=args.command=='recover')
    from ml_workbench import application as app
    if args.command in ('init','demo'):r.initialize()
    if args.command=='init':return dict(status='INITIALIZED',**app.experiments())
    if args.command=='demo':return app.demo()
    if args.command=='recover':return dict(status='SESSION_RECOVERED',automatically_replayed=False,**app.experiments())
    if args.command=='import':return app.import_dataset(r.read_bytes(r.local_path(args.file)))
    if args.command in ('prepare','review'):return getattr(app,args.command)(r.read_bytes(r.local_path(args.file)))
    if args.command=='list':return app.experiments()
    if args.command=='datasets':return app.datasets()
    if args.command=='example':return app.example_file(args.dataset)
    if args.command=='evaluate':return app.evaluate(r.encode(dict(experiment_id=args.experiment,expected_sha256=args.expected)))
    if args.command in ('show','export'):return getattr(app,args.command)(args.experiment)
    if args.command=='compare':return app.compare(args.left,args.right)
    if args.command=='backup':return app.backup()
    from ml_workbench.web import serve
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
