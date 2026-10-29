"""Explicit CLI lifecycle; init opens no real store unless --from-store is supplied."""
import argparse
from .application import Workbench,decode,read,recover,Refused
class Parser(argparse.ArgumentParser):
    def error(self,message):raise Refused('ARGUMENTS_INVALID')

def main():
    parser=Parser(allow_abbrev=False);parser.add_argument('--workspace',required=True);sub=parser.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init');init.add_argument('--from-store')
    sub.add_parser('demo');sub.add_parser('status');serve=sub.add_parser('serve');serve.add_argument('--port',type=int,default=0)
    recovery=sub.add_parser('recover');recovery.add_argument('--confirm-stopped',action='store_true')
    for name in ('import','review','export','backup'):
        command=sub.add_parser(name);command.add_argument('--request',required=True)
    args=parser.parse_args()
    if args.command=='recover':recover(args.workspace,args.confirm_stopped);return dict(status='SESSION_RECOVERED',automatically_replayed=False)
    if args.command=='init':return Workbench.initialize(args.workspace,args.from_store)
    if args.command=='demo':Workbench.initialize(args.workspace)
    with Workbench(args.workspace) as app:
        if args.command=='serve':
            from .web import serve
            serve(app,args.port);return dict(status='STOPPED')
        if args.command=='status':return app.state()
        if args.command=='demo':
            app.mutate('import',dict(expected=app.state()['head'],file='inbox/sample-records.jsonl'));row=next(r for r in app.state()['records'] if r['split']=='train');detail=app.detail(row['id']);app.mutate('review',dict(expected=detail['head'],id=row['id'],decision='approved',actor='sample_reviewer',note='Fictional review assertions only',checks={k:True for k in ('quality','privacy','rights','context')}));exported=app.mutate('export',dict(expected=app.state()['head']));backup=app.mutate('backup',dict(expected=app.state()['head']));state=app.state();return dict(mode='FICTIONAL_DATASET_REVIEW_DEMO',records=state['total'],approved=state['counts']['approved'],exported=exported['result']['manifest']['records'],backup_validated=backup['result']['bytes']>0,public_release_authorized=False,external_system_writes=False)
        return app.mutate(args.command,decode(read(app.local(args.request))))
