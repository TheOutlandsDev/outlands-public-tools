"""Compare a literal selected Android .prop snapshot subset without applying it. MIT."""
from __future__ import annotations
import re
from declaration_diff import cli,inspect_sets,register,unidentified
from inspection_support import issue,text_lines

KEY=re.compile(r'[A-Za-z0-9_.-]{1,128}\Z')


def parse(data,side,source,report,index):
    for line,raw in text_lines(data):
        value=raw.strip(' \t')
        if not value or value.startswith('#'):continue
        if re.match(r'import[ \t]',value):
            unidentified(report,side,source,line)
            issue(report['coverage_issues'],'PROPERTY_IMPORT_NOT_FOLLOWED',source,line);continue
        if '=' not in value:
            unidentified(report,side,source,line)
            issue(report['coverage_issues'],'UNSUPPORTED_PROPERTY_LINE',source,line);continue
        key,field=value.split('=',1);key=key.strip(' \t');field=field.strip(' \t')
        if not KEY.fullmatch(key):
            unidentified(report,side,source,line)
            issue(report['coverage_issues'],'UNSUPPORTED_PROPERTY_KEY',source,line);continue
        register(report,index,side,source,line,key,{'value':field})


def inspect(before,after,details=False):
    return inspect_sets(before,after,'Android Property Configuration Diff',
                        'Literal unique selected key/value declarations only; no import/override/order/permission/runtime evaluation.',parse,details)


def main(argv=None):return cli(inspect,__doc__,argv)
if __name__=='__main__':raise SystemExit(main())
