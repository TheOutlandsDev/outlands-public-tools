"""Adapt authored nonexecuting extension dispatch; diagnostics never echo source."""
import ast
from pathlib import PurePosixPath
import re
import time
import xml.etree.ElementTree as ET
from . import contracts as c,preflight,runtime as r


def validate_content(path,content):
    # Retain the authored Python AST branch and extension-based dispatch.
    # Other branches use strict bounded handlers and neutral diagnostic codes.
    suffix=PurePosixPath(path).suffix.casefold()
    if suffix in ('.py','.pyw'):
        tree=ast.parse(content,filename=str(path))
        if sum(1 for _ in ast.walk(tree))>10000:raise r.WorkbenchError('PYTHON_NODE_LIMIT')
        return 'PYTHON_SYNTAX_VALID'
    if suffix=='.json':r.decode(content.encode('utf-8'));return 'JSON_SYNTAX_VALID'
    if suffix in ('.xml','.rdl'):
        if re.search(r'<!\s*(DOCTYPE|ENTITY)\b',content,re.I):raise r.WorkbenchError('XML_DECLARATION_REFUSED')
        root=ET.fromstring(content);stack=[(root,0)];count=0
        while stack:
            node,depth=stack.pop();count+=1
            if count>5000 or depth>40 or len(node.attrib)>16 or len(node.text or '')>16384:raise r.WorkbenchError('XML_STRUCTURE_LIMIT')
            stack.extend((child,depth+1) for child in node)
        return 'XML_SYNTAX_VALID'
    if suffix=='.sql':
        try:preflight._check_query(content)
        except (ValueError,RuntimeError):raise r.WorkbenchError('SQL_PREFLIGHT_REFUSED') from None
        return 'SQL_PREFLIGHT_VALID'
    return 'NOT_CHECKED'


def check_project(value):
    project=c.project(r.encode(value));results=[];deadline=time.monotonic()+2
    for file in project['files']:
        if time.monotonic()>deadline:return dict(status='budget_exceeded',reason='VALIDATION_TIME_LIMIT',files_checked=len(results),checks=results,code_executed=False)
        try:
            code=validate_content(file['path'],file['content']);row=dict(path=file['path'],sha256=r.digest(file['content'].encode()),status='unchecked' if code=='NOT_CHECKED' else 'pass',code=code,line=None,column=None)
        except (SyntaxError,ET.ParseError,r.WorkbenchError,ValueError,RecursionError) as error:
            line=column=None
            if isinstance(error,SyntaxError):code='PYTHON_SYNTAX_INVALID';line=error.lineno;column=error.offset
            elif isinstance(error,ET.ParseError):code='XML_SYNTAX_INVALID';line,column=error.position
            else:code=str(error) if isinstance(error,r.WorkbenchError) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}',str(error)) else 'SOURCE_CHECK_REFUSED'
            row=dict(path=file['path'],sha256=r.digest(file['content'].encode()),status='fail',code=code,line=line,column=column)
        results.append(row)
    counts={status:sum(row['status']==status for row in results) for status in ('pass','fail','unchecked')}
    return dict(status='completed',files_checked=len(results),checks=results,counts=counts,passed=counts['fail']==0,all_files_checked=counts['unchecked']==0,code_executed=False,scope='Python syntax, strict JSON, bounded XML syntax and conservative SQL preflight only; other text is unchecked')


def main():
    import sys
    try:result=check_project(r.decode(sys.stdin.buffer.read(r.MAX_INPUT+1)))
    except Exception:result=dict(status='refused',reason='VALIDATION_REFUSED',code_executed=False)
    sys.stdout.buffer.write(r.encode(result));sys.stdout.buffer.flush()
