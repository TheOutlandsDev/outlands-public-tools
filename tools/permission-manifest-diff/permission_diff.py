"""Compare declared Android-style filesystem permission metadata; never apply it. MIT."""
from __future__ import annotations
import re
from declaration_diff import cli,inspect_sets,register,unidentified
from inspection_support import issue,text_lines

PATH=re.compile(r'[A-Za-z0-9_.+@=-]+(?:/[A-Za-z0-9_.+@=-]+)*\Z')
CONTEXT=re.compile(r'[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+:[A-Za-z0-9_,:.-]+\Z')


def path_supported(value):
    return len(value)<=512 and PATH.fullmatch(value) is not None and all(p not in {'.','..'} for p in value.split('/'))


def fields_from(words):
    if len(words)<4:return None
    if not all(re.fullmatch(r'[0-9]{1,10}',v) and int(v)<=2**32-1 for v in words[1:3]):return None
    if not re.fullmatch(r'[0-7]{1,4}',words[3]):return None
    result={'uid':int(words[1]),'gid':int(words[2]),'mode_octal':f'{int(words[3],8):04o}','selabel':None,'capabilities':None}
    seen=set()
    for word in words[4:]:
        if '=' not in word:return None
        key,value=word.split('=',1)
        if key in seen or key not in {'selabel','capabilities'}:return None
        seen.add(key)
        if key=='selabel':
            if len(value)>512 or not CONTEXT.fullmatch(value):return None
            result[key]=value
        else:
            if not re.fullmatch(r'0x[0-9A-Fa-f]{1,16}',value):return None
            result[key]=f'0x{int(value,16):x}'
    return result


def parse(data,side,source,report,index):
    for line,raw in text_lines(data):
        value=raw.strip(' \t')
        if not value or value.startswith('#'):continue
        words=re.split(r'[ \t]+',value);path=words[0]
        if not path_supported(path):
            unidentified(report,side,source,line)
            issue(report['coverage_issues'],'UNSUPPORTED_MANIFEST_PATH',source,line);continue
        fields=fields_from(words)
        if fields is None:issue(report['coverage_issues'],'UNSUPPORTED_PERMISSION_DECLARATION',source,line)
        # Keep a known path even if its fields cannot be understood; never invent a removal.
        register(report,index,side,source,line,path,fields)


def inspect(before,after,details=False):
    return inspect_sets(before,after,'Filesystem Permission Manifest Diff',
                        'Selected literal path/UID/GID/mode/optional-label/capability declarations only; no filesystem or policy evaluation.',parse,details)


def main(argv=None):return cli(inspect,__doc__,argv)
if __name__=='__main__':raise SystemExit(main())
