"""Inspect literal declarations in selected Android build text; never run a build. MIT."""
from __future__ import annotations
import json
import re
from inspection_support import (Parser, TextError, bounded_append, cli_error, finish,
                                require, source_inputs, source_record, text_lines,
                                write_report)

NAME = re.compile(r'[A-Za-z0-9_.+@-]{1,256}')
IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
MAX_TOKENS = 40000
MAX_DEPTH = 32
BUILD_KINDS = frozenset({'BUILD_SHARED_LIBRARY','BUILD_STATIC_LIBRARY','BUILD_EXECUTABLE',
    'BUILD_PREBUILT','BUILD_JAVA_LIBRARY','BUILD_PACKAGE','BUILD_HOST_EXECUTABLE',
    'BUILD_HOST_SHARED_LIBRARY','BUILD_HOST_STATIC_LIBRARY','BUILD_HOST_JAVA_LIBRARY'})


class GrammarError(Exception):
    def __init__(self, code, line): self.code=code; self.line=line


def result(): return {'records':[], 'issues':[], 'uncertain':False, 'ignored_rows':0}


def issue(parsed, code, source, line):
    parsed['uncertain']=True
    bounded_append(parsed['issues'], {'code':code,'source':source,'line':line})


def lex_bp(data):
    text='\n'.join(value for _,value in text_lines(data)); tokens=[]; i=0; line=1
    def add(kind,value,start):
        require(len(tokens)<MAX_TOKENS,'BP_TOKEN_LIMIT');tokens.append((kind,value,start))
    while i<len(text):
        char=text[i]
        if char in ' \t\n': line+=char=='\n';i+=1;continue
        if text.startswith('//',i):
            end=text.find('\n',i);i=len(text) if end<0 else end;continue
        if text.startswith('/*',i):
            end=text.find('*/',i+2)
            if end<0: raise GrammarError('BP_UNTERMINATED_COMMENT',line)
            line+=text.count('\n',i,end+2);i=end+2;continue
        if char=='"':
            start=i;start_line=line;i+=1
            while i<len(text):
                if text[i]=='\n': raise GrammarError('BP_STRING_UNSUPPORTED',start_line)
                if text[i]=='\\': i+=2;continue
                if text[i]=='"': i+=1;break
                i+=1
            else: raise GrammarError('BP_STRING_UNTERMINATED',start_line)
            try: value=json.loads(text[start:i])
            except (ValueError,UnicodeError): raise GrammarError('BP_STRING_UNSUPPORTED',start_line) from None
            require(len(value)<=1024,'BP_STRING_LIMIT')
            add('string',value,start_line);continue
        match=IDENTIFIER.match(text,i)
        if match:
            require(len(match[0])<=256,'BP_IDENTIFIER_LIMIT');add('id',match[0],line);i=match.end();continue
        add('punct',char,line);i+=1
    return tokens


def bp_body(tokens,start):
    """Read direct properties; nested values are balanced, not semantically evaluated."""
    position=start;properties=[];seen=set();duplicate=False
    while position<len(tokens):
        token=tokens[position]
        if token[0]=='punct' and token[1]=='}': return position+1,properties,duplicate
        if token[0]!='id' or position+1>=len(tokens) or tokens[position+1][:2]!=('punct',':'):
            raise GrammarError('BP_PROPERTY_SYNTAX_UNSUPPORTED',token[2])
        key=token[1]
        if key in seen: duplicate=True
        seen.add(key);position+=2;value=[];stack=[]
        while position<len(tokens):
            item=tokens[position];char=item[1] if item[0]=='punct' else None
            if not stack and char in (',','}'): break
            if char in ('{','['):
                stack.append('}' if char=='{' else ']');require(len(stack)<=MAX_DEPTH,'BP_NESTING_LIMIT')
            elif char in ('}',']'):
                if not stack or char!=stack.pop(): raise GrammarError('BP_DELIMITER_MISMATCH',item[2])
            value.append(item);position+=1
        if stack or position>=len(tokens): raise GrammarError('BP_BLOCK_UNTERMINATED',token[2])
        if not value: raise GrammarError('BP_EMPTY_PROPERTY_VALUE',token[2])
        properties.append((key,value,token[2]))
        if tokens[position][1]==',':position+=1
    raise GrammarError('BP_BLOCK_UNTERMINATED',tokens[start-1][2])


def parse_bp(data,source):
    parsed=result()
    try:
        tokens=lex_bp(data);position=0
        while position<len(tokens):
            token=tokens[position]
            if token[0]!='id' or position+1>=len(tokens) or tokens[position+1][:2]!=('punct','{'):
                issue(parsed,'BP_TOPLEVEL_REMAINDER_UNINSPECTED',source,token[2]);break
            kind=token[1];position,properties,duplicate=bp_body(tokens,position+2)
            if kind in {'soong_namespace','package'}:
                issue(parsed,'BP_SCOPE_DECLARATION_UNEVALUATED',source,token[2]);continue
            names=[value for key,value,_ in properties if key=='name']
            literals=[v[0][1] for v in names if len(v)==1 and v[0][0]=='string' and NAME.fullmatch(v[0][1])]
            name=literals[0] if literals and len(set(literals))==1 else None
            held=duplicate or len(names)!=1 or len(literals)!=1
            if duplicate:issue(parsed,'BP_DUPLICATE_DIRECT_PROPERTY',source,token[2])
            if len(names)!=1 or len(literals)!=1:issue(parsed,'BP_NAME_UNRESOLVED',source,token[2])
            if kind.startswith('soong_config_'):
                issue(parsed,'BP_DYNAMIC_MODULE_KIND_UNEVALUATED',source,token[2]);held=True
            bounded_append(parsed['records'],{'source':source,'line':token[2],
                'syntax':'bp','kind':kind,'name':name,'held':held})
    except GrammarError as error: issue(parsed,error.code,source,error.line)
    return parsed


def make_comment(line):
    for index,char in enumerate(line):
        if char=='#':
            slashes=0;position=index-1
            while position>=0 and line[position]=='\\': slashes+=1;position-=1
            if slashes%2==0:return line[:index]
    return line


def parse_mk(data,source):
    parsed=result();block=None;continuation=False
    def close(line,kind,incomplete=False):
        nonlocal block
        if block is None:return
        values=block['names'];literal=[v for v in values if v is not None]
        name=literal[0] if literal and len(set(literal))==1 else None
        held=block['held'] or incomplete or len(values)!=1 or len(literal)!=1
        if len(values)!=1 or len(literal)!=1:issue(parsed,'MK_NAME_UNRESOLVED',source,block['line'])
        if len(values)>1:issue(parsed,'MK_DUPLICATE_MODULE_ASSIGNMENT',source,block['line'])
        bounded_append(parsed['records'],{'source':source,'line':block['line'],
            'syntax':'mk','kind':kind,'name':name,'held':held});block=None
    for number,raw in text_lines(data):
        line=make_comment(raw).strip(' \t')
        if not line:continue
        trailing=len(line)-len(line.rstrip('\\'));joined=trailing%2==1
        if continuation or joined:
            if not continuation:issue(parsed,'MK_CONTINUATION_UNSUPPORTED',source,number)
            if block is not None:block['held']=True
            continuation=joined;continue
        if raw.startswith('\t'):
            issue(parsed,'MK_RECIPE_REMAINDER_UNINSPECTED',source,number)
            if block is not None:close(number,'unresolved',True)
            break
        if re.match(r'(?:ifeq|ifneq|ifdef|ifndef|else|endif|define|endef|override|export|unexport)\b',line):
            issue(parsed,'MK_DIRECTIVE_REMAINDER_UNINSPECTED',source,number)
            if block is not None:close(number,'unresolved',True)
            break
        include=re.fullmatch(r'include\s+\$\(([A-Z_]+)\)',line)
        if include:
            if include[1]=='CLEAR_VARS':
                if block is not None:
                    issue(parsed,'MK_BLOCK_WITHOUT_BUILD',source,block['line']);close(number,'unresolved',True)
                block={'line':number,'names':[],'held':False}
            elif include[1] in BUILD_KINDS:
                if block is None:issue(parsed,'MK_BUILD_WITHOUT_CLEAR',source,number)
                else:close(number,include[1])
            else:
                issue(parsed,'MK_INCLUDE_UNFOLLOWED',source,number)
                if block is not None:block['held']=True
            continue
        if re.match(r'(?:-?include|sinclude)\b',line):
            issue(parsed,'MK_INCLUDE_UNFOLLOWED',source,number)
            if block is not None:block['held']=True
            continue
        assignment=re.fullmatch(r'(LOCAL_[A-Z0-9_]+)\s*(:=|=|\+=|\?=|::=)\s*(.*)',line)
        if assignment:
            key,operator,value=assignment.groups()
            if key=='LOCAL_MODULE':
                if block is None:issue(parsed,'MK_MODULE_OUTSIDE_BLOCK',source,number);continue
                valid=operator in {':=','='} and NAME.fullmatch(value)
                bounded_append(block['names'],value if valid else None)
                if not valid:
                    block['held']=True;issue(parsed,'MK_MODULE_VALUE_UNSUPPORTED',source,number)
            else:parsed['ignored_rows']+=1
            continue
        issue(parsed,'MK_UNSUPPORTED_REMAINDER_UNINSPECTED',source,number)
        if block is not None:close(number,'unresolved',True)
        break
    if continuation:issue(parsed,'MK_CONTINUATION_UNTERMINATED',source,0)
    if block is not None:
        issue(parsed,'MK_BLOCK_WITHOUT_BUILD',source,block['line']);close(0,'unresolved',True)
    return parsed


def wanted_names(data,source):
    names=[];seen=set();issues=[]
    for number,raw in text_lines(data):
        name=raw.strip(' \t')
        if not name or name.startswith('#'):continue
        require(bool(NAME.fullmatch(name)),'WANTED_NAME_UNSUPPORTED')
        if name in seen:
            bounded_append(issues,{'code':'DUPLICATE_WANTED_NAME','source':source,'line':number})
        else:seen.add(name);bounded_append(names,name)
    require(bool(names),'WANTED_NAMES_REQUIRED')
    return names,issues


def inspect(bp_inputs,mk_inputs,wanted=None,details=False):
    report={'schema_version':1,'tool':'Android Build Module Declaration Inspector',
        'scope':'Literal declarations in explicitly selected build text; no build, namespace or expression evaluation.',
        'details_included':details,'sources':[],'declarations':[],'repeated_names':[],
        'wanted':[],'findings':[],'coverage_issues':[],'unresolved_identity_or_scope':False,'ignored_make_rows':0}
    records=[]
    for syntax,inputs,parser in [('bp',bp_inputs,parse_bp),('mk',mk_inputs,parse_mk)]:
        for source,data in inputs:
            parsed=parser(data,source);report['sources'].append(dict(source_record(source,data),syntax=syntax))
            report['unresolved_identity_or_scope']|=parsed['uncertain'];report['ignored_make_rows']+=parsed['ignored_rows']
            for row in parsed['issues']:bounded_append(report['coverage_issues'],row)
            for row in parsed['records']:bounded_append(records,row)
    by_name={}
    for index,record in enumerate(records,1):
        token=f'declaration-{index:04d}'
        row={'id':token,'source':record['source'],'line':record['line'],
             'syntax':record['syntax'],'identity_known':record['name'] is not None,'held':record['held']}
        if details:row.update(declared_name=record['name'],module_kind=record['kind'])
        bounded_append(report['declarations'],row)
        if record['name'] is not None:by_name.setdefault(record['name'],[]).append((token,record['held']))
    for name,entries in sorted(by_name.items()):
        if len(entries)>1:
            row={'id':f'repeated-{len(report["repeated_names"])+1:04d}','declarations':[x[0] for x in entries],'count':len(entries)}
            if details:row['declared_name']=name
            bounded_append(report['repeated_names'],row)
    if report['repeated_names']:bounded_append(report['findings'],{'code':'REPEATED_DECLARED_NAME_OBSERVED'})
    if wanted is not None:
        source,data=wanted;names,issues=wanted_names(data,source)
        report['sources'].append(dict(source_record(source,data),syntax='wanted'))
        for row in issues:bounded_append(report['coverage_issues'],row)
        for index,name in enumerate(names,1):
            entries=by_name.get(name,[])
            state=('observed_held' if any(x[1] for x in entries) else 'observed_multiple' if len(entries)>1 else 'observed_once') if entries else ('held_incomplete_scope' if report['unresolved_identity_or_scope'] else 'not_observed_selected_supported_scope')
            row={'id':f'wanted-{index:04d}','state':state,'declarations':[x[0] for x in entries]}
            if details:row['declared_name']=name
            bounded_append(report['wanted'],row)
        if any(r['state']=='not_observed_selected_supported_scope' for r in report['wanted']):
            bounded_append(report['findings'],{'code':'WANTED_NAME_NOT_OBSERVED'})
    return finish(report)


def main(argv=None):
    parser=Parser(description=__doc__);parser.add_argument('--bp',action='append',default=[])
    parser.add_argument('--mk',action='append',default=[]);parser.add_argument('--wanted')
    parser.add_argument('--output',required=True);parser.add_argument('--include-details',action='store_true')
    try:
        args=parser.parse_args(argv);require(bool(args.bp or args.mk),'BUILD_INPUT_REQUIRED')
        paths=args.bp+args.mk+([args.wanted] if args.wanted else [])
        inputs=source_inputs(paths);bp=inputs[:len(args.bp)];mk=inputs[len(args.bp):len(args.bp)+len(args.mk)]
        report=inspect(bp,mk,inputs[-1] if args.wanted else None,args.include_details)
        write_report(report,args.output,paths)
        print(json.dumps({'status':report['status'],'declarations':len(report['declarations']),
            'repeated_names':len(report['repeated_names']),'findings':len(report['findings']),
            'coverage_issues':len(report['coverage_issues'])},sort_keys=True))
        return int(report['status']!='NO_SCOPE_FINDINGS')
    except (TextError,OSError,ValueError,RecursionError) as error:return cli_error(error)


if __name__=='__main__':raise SystemExit(main())
