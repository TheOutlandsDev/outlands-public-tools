"""CLI for private planning instances and the complete fictional application."""
import argparse
import json
import sys
from planning import runtime


class Parser(argparse.ArgumentParser):
    def error(self,message):raise runtime.WorkbenchError('ARGUMENTS_INVALID')


def main():
    parser=Parser(prog='production-planning-workbench',allow_abbrev=False)
    parser.add_argument('--workspace',required=True)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('init','demo','list','backup'):sub.add_parser(name)
    recovery=sub.add_parser('recover');recovery.add_argument('--confirm-stopped',action='store_true')
    for name in ('show','plan','history','export'):
        p=sub.add_parser(name);p.add_argument('--project',required=True)
    importer=sub.add_parser('import');importer.add_argument('--file',required=True);importer.add_argument('--expected')
    revision=sub.add_parser('revise-order');revision.add_argument('--project',required=True);revision.add_argument('--file',required=True);revision.add_argument('--expected',required=True)
    action=sub.add_parser('action');action.add_argument('--file',required=True)
    server=sub.add_parser('serve');server.add_argument('--port',type=int,default=0)
    args=parser.parse_args()
    if args.command=='recover' and not args.confirm_stopped:raise runtime.WorkbenchError('STOPPED_ASSERTION_REQUIRED')
    runtime.configure(args.workspace,create=args.command in {'init','demo'},confirm_stopped=args.command=='recover')
    from planning import application as app
    if args.command in {'init','demo'}:runtime.initialize()
    if args.command=='init':return dict(status='INITIALIZED',**app.projects())
    if args.command=='demo':return app.demo()
    if args.command=='recover':return dict(status='SESSION_RECOVERED',automatically_replayed=False,**app.projects())
    if args.command=='list':return app.projects()
    if args.command=='import':return app.import_file(args.file,args.expected)
    if args.command=='revise-order':return app.revise_order(args.project,args.file,args.expected)
    if args.command=='action':return app.apply_action(runtime.read_bytes(runtime.local_path(args.file)))
    if args.command=='backup':return app.backup()
    if args.command=='serve':
        from planning.web import serve
        serve(args.port);return dict(status='STOPPED')
    return getattr(app,args.command)(args.project)


if __name__=='__main__':
    code=0;result=None
    try:result=main()
    except runtime.WorkbenchError as error:code=2;result=dict(error=str(error))
    except KeyboardInterrupt:code=130;result=dict(error='INTERRUPTED')
    except Exception:code=2;result=dict(error='OPERATION_REFUSED')
    finally:
        try:runtime.close()
        except Exception:code=2;result=dict(error='SESSION_CLEANUP_REFUSED')
    if result is not None:print(json.dumps(result,ensure_ascii=True,allow_nan=False,sort_keys=True))
    sys.exit(code)
