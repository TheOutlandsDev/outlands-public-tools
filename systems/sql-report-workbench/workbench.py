"""Explicit private CLI; query execution is separate from save/report inspection."""
import json
import sys
from sql_report import jobs,runtime as r


def main():
    parser=r.Parser(prog='sql-report-workbench',allow_abbrev=False);parser.add_argument('--workspace',required=True);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('init','demo','datasets','artifacts','backup'):sub.add_parser(name)
    p=sub.add_parser('recover');p.add_argument('--confirm-stopped',action='store_true')
    for name in ('import','save-query','run','validate-report','review'):
        p=sub.add_parser(name);p.add_argument('--file',required=True)
        if name=='save-query':p.add_argument('--expected')
    p=sub.add_parser('save-report');p.add_argument('--file',required=True);p.add_argument('--source-sha',required=True);p.add_argument('--id',required=True);p.add_argument('--title',required=True);p.add_argument('--expected')
    p=sub.add_parser('list');p.add_argument('--kind',choices=('query','report'),default='query')
    for name in ('show','history'):
        p=sub.add_parser(name);p.add_argument('--kind',choices=('query','report','artifact') if name=='show' else ('query','report'),required=True);p.add_argument('--id',required=True)
        if name=='show':p.add_argument('--version',type=int)
    p=sub.add_parser('compare');p.add_argument('--left',required=True);p.add_argument('--right',required=True)
    p=sub.add_parser('export');p.add_argument('--artifact',required=True)
    p=sub.add_parser('serve');p.add_argument('--port',type=int,default=0);args=parser.parse_args()
    if args.command=='recover' and not args.confirm_stopped:raise r.WorkbenchError('STOPPED_ASSERTION_REQUIRED')
    r.configure(args.workspace,create=args.command in ('init','demo'),confirm_stopped=args.command=='recover')
    from sql_report import application as app,report_xml
    if args.command in ('init','demo'):r.initialize()
    if args.command=='init':return dict(status='INITIALIZED',**app.datasets())
    if args.command=='demo':return app.demo()
    if args.command=='recover':return dict(status='SESSION_RECOVERED',automatically_replayed=False,**app.artifacts())
    if args.command=='import':return app.import_dataset(r.read_bytes(r.local_path(args.file)))
    if args.command=='save-query':return app.save_query(r.encode(dict(definition=r.decode(r.read_bytes(r.local_path(args.file))),expected_sha256=args.expected)))
    if args.command=='save-report':return app.save_report(r.encode(dict(report_id=args.id,title=args.title,xml=report_xml.checked_text(args.file,args.source_sha).decode('utf-8-sig'),expected_sha256=args.expected)))
    if args.command in ('run','validate-report'):
        raw=r.read_bytes(r.local_path(args.file));started=app.start_query(raw) if args.command=='run' else app.start_validation(raw);return jobs.wait(started['job_id'])
    if args.command=='review':return app.review(r.read_bytes(r.local_path(args.file)))
    if args.command=='datasets':return app.datasets()
    if args.command=='artifacts':return app.artifacts()
    if args.command=='list':return app.documents(args.kind)
    if args.command=='show':return app.artifact(args.id) if args.kind=='artifact' else app.document(args.kind,args.id,args.version)
    if args.command=='history':return app.history(args.kind,args.id)
    if args.command=='compare':return app.compare(args.left,args.right)
    if args.command=='export':return app.export(args.artifact)
    if args.command=='backup':return app.backup()
    from sql_report.web import serve
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
