"""Manage verified mod-profile copies in one explicit private workspace. MIT."""
from __future__ import annotations
import argparse
import json
import re
import sys


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise ValueError('ARGUMENTS_INVALID')


def parser():
    result=Parser(prog='profile-manager',description=__doc__)
    commands=result.add_subparsers(dest='command')
    descriptions={
        'init':'Create a new managed workspace.',
        'import-profile':'Copy a selected source into a new named profile.',
        'status':'Review active copy, profiles and pending work.',
        'list':'List managed profile and operation metadata.',
        'plan':'Read-only preview; reserves nothing.',
        'activate':'Stage and activate a verified managed profile copy.',
        'deactivate':'Retain the active copy and record no active profile.',
        'recover':'Review and recover one interrupted managed operation.',
        'gui':'Open the optional desktop interface explicitly.',
    }
    for name,description in descriptions.items():
        command=commands.add_parser(name,help=description,description=description)
        command.add_argument('--workspace',required=name!='gui')
        if name in ('import-profile','activate'):
            command.add_argument('--profile',required=True)
        if name=='import-profile':command.add_argument('--source',required=True)
        if name=='plan':
            command.add_argument('--action',choices=('activate','deactivate'),required=True)
            command.add_argument('--profile')
    return result


def main(argv=None):
    engine=None
    try:
        arguments=parser();args=arguments.parse_args(argv)
        if args.command is None:
            arguments.print_help();return 0
        if args.command=='gui':
            from profile_gui import main as desktop
            return desktop(args.workspace)
        import profile_engine as engine
        if args.command=='init':value=engine.initialize(args.workspace)
        elif args.command=='import-profile':value=engine.import_profile(args.workspace,args.profile,args.source)
        elif args.command in ('status','list'):value=engine.status(args.workspace)
        elif args.command=='plan':value=engine.plan(args.workspace,args.action,args.profile)
        elif args.command=='activate':value=engine.activate(args.workspace,args.profile)
        elif args.command=='deactivate':value=engine.deactivate(args.workspace)
        else:value=engine.recover(args.workspace)
        print(json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False))
        return 1 if value.get('status')=='REVIEW_REQUIRED' else 0
    except KeyboardInterrupt:
        print(json.dumps({'status':'INCOMPLETE','error':'INTERRUPTED_REVIEW_RECOVERY'}));return 130
    except Exception as error:
        if engine is not None and isinstance(error,engine.ProfileError):
            code=str(error)
            if re.fullmatch(r'[A-Z][A-Z0-9_]{0,100}',code) is None:code='PROFILE_OPERATION_REFUSED'
        elif isinstance(error,ValueError) and str(error)=='ARGUMENTS_INVALID':code='ARGUMENTS_INVALID'
        elif isinstance(error,ImportError):code='RUNTIME_UNAVAILABLE'
        elif isinstance(error,(OSError,ValueError,UnicodeError)):code='IO_OR_INPUT_ERROR'
        else:code='INTERNAL_ERROR'
        print(json.dumps({'status':'INCOMPLETE','error':code},sort_keys=True));return 2


if __name__=='__main__':raise SystemExit(main())
