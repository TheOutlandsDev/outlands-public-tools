"""Explicit private CLI; import/trust/run/review/export remain separate actions."""
import json
import sys
from evidence import jobs,runtime as r


def main():
    parser=r.Parser(prog='test-evidence-workbench',allow_abbrev=False);parser.add_argument('--workspace',required=True);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('init','demo','cases','artifacts','backup'):sub.add_parser(name)
    p=sub.add_parser('recover');p.add_argument('--confirm-stopped',action='store_true')
    for name in ('import','save-case','trust','run','review'):p=sub.add_parser(name);p.add_argument('--file',required=True)
    p=sub.add_parser('show');p.add_argument('--case',required=True);p.add_argument('--version',type=int)
    p=sub.add_parser('history');p.add_argument('--case',required=True)
    p=sub.add_parser('artifact');p.add_argument('--id',required=True)
    p=sub.add_parser('compare');p.add_argument('--left',required=True);p.add_argument('--right',required=True)
    p=sub.add_parser('export');p.add_argument('--artifact',required=True)
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=0);args=parser.parse_args()
    if args.command=='recover' and not args.confirm_stopped:raise r.WorkbenchError('STOPPED_ASSERTION_REQUIRED')
    r.configure(args.workspace,create=args.command in ('init','demo'),confirm_stopped=args.command=='recover')
    from evidence import application as app
    if args.command in ('init','demo'):r.initialize()
    if args.command=='init':return dict(status='INITIALIZED',**app.cases())
    if args.command=='demo':return app.demo()
    if args.command=='recover':return dict(status='SESSION_RECOVERED',automatically_replayed=False,**app.cases())
    if args.command=='cases':return app.cases()
    if args.command=='artifacts':return app.artifacts()
    if args.command in ('import','save-case','trust','run','review'):
        raw=r.read_bytes(r.local_path(args.file))
        if args.command=='import':return app.import_bundle(raw)
        if args.command=='save-case':return app.save_case(raw)
        if args.command=='trust':return app.trust(raw)
        if args.command=='review':return app.review(raw)
        return jobs.wait(app.start_run(raw)['job_id'])
    if args.command=='show':return app.case(args.case,args.version)
    if args.command=='history':return app.history(args.case)
    if args.command=='artifact':return app.artifact(args.id)
    if args.command=='compare':return app.compare(args.left,args.right)
    if args.command=='export':return app.export(args.artifact)
    if args.command=='backup':return app.backup()
    from evidence.web import serve
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
