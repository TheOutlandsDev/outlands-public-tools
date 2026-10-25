"""Original bounded reader for a documented UTF-8 XML subset, not general XML. MIT."""
from __future__ import annotations
import re
import unicodedata
from inspection_support import TextError, require, text_lines

NAME=re.compile(r'[A-Za-z_][A-Za-z0-9_.:-]{0,255}')
SPACE=' \t\n'
ENTITIES={'amp':'&','lt':'<','gt':'>','apos':"'",'quot':'"'}


class Node:
    """Small data object; no external parser, entity loader or resource behavior."""
    def __init__(self,tag,attributes):
        self.tag=tag;self.attrib=attributes;self.text='';self.tail='';self.children=[]
    def __len__(self):return len(self.children)
    def __iter__(self):return iter(self.children)
    def get(self,name,default=None):return self.attrib.get(name,default)
    def findall(self,name):return [child for child in self.children if child.tag==name]
    def iter(self):
        pending=[self]
        while pending:
            node=pending.pop();yield node;pending.extend(reversed(node.children))


def decode(value):
    """Decode predefined/numeric references once, with explicit character bounds."""
    result=[];cursor=0
    while True:
        start=value.find('&',cursor)
        if start<0:result.append(value[cursor:]);break
        result.append(value[cursor:start]);end=value.find(';',start+1)
        require(end>=0 and end-start<=12,'INVALID_XML_REFERENCE')
        token=value[start+1:end]
        if token in ENTITIES:character=ENTITIES[token]
        else:
            if re.fullmatch(r'#[0-9]{1,7}',token):number=int(token[1:])
            elif re.fullmatch(r'#x[0-9A-Fa-f]{1,6}',token):number=int(token[2:],16)
            else:raise TextError('INVALID_XML_REFERENCE')
            require(number in {9,10,13} or 0x20<=number<=0xd7ff or 0xe000<=number<=0xfffd or 0x10000<=number<=0x10ffff,'INVALID_XML_REFERENCE')
            character=chr(number)
            require(not unicodedata.category(character).startswith('C') or character in '\t\n','XML_REFERENCE_CONTROL_UNSUPPORTED')
            require(character not in '\u2028\u2029','XML_REFERENCE_CONTROL_UNSUPPORTED')
        result.append(character);cursor=end+1
    decoded=''.join(result);require(len(decoded)<=8192,'XML_TEXT_LIMIT');return decoded


def attributes(value):
    """Read bounded quoted attributes; reject duplicate names and missing separators."""
    result={};position=0
    while position<len(value):
        start=position
        while position<len(value) and value[position] in SPACE:position+=1
        if position==len(value):break
        require(position>start,'INVALID_XML_ATTRIBUTES')
        match=NAME.match(value,position);require(match is not None,'INVALID_XML_ATTRIBUTES')
        name=match[0];position=match.end()
        while position<len(value) and value[position] in SPACE:position+=1
        require(position<len(value) and value[position]=='=','INVALID_XML_ATTRIBUTES');position+=1
        while position<len(value) and value[position] in SPACE:position+=1
        require(position<len(value) and value[position] in '\"\'','INVALID_XML_ATTRIBUTES')
        quote=value[position];position+=1;end=value.find(quote,position)
        require(end>=0 and '<' not in value[position:end],'INVALID_XML_ATTRIBUTES')
        require(name not in result,'DUPLICATE_XML_ATTRIBUTE')
        require(len(result)<16,'XML_ATTRIBUTE_LIMIT')
        # Literal XML attribute whitespace is normalized before reference decoding.
        raw=value[position:end].replace('\t',' ').replace('\n',' ')
        require(len(raw)<=8192,'XML_TEXT_LIMIT')
        decoded=decode(raw);require(len(decoded)<=1024,'XML_ATTRIBUTE_LIMIT')
        result[name]=decoded;position=end+1
    return result


def parse(data,on_instruction):
    """Parse balanced literal tags/attributes, comments and restricted references."""
    text='\n'.join(value for _line,value in text_lines(data))
    require(not re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b',text,re.I),'XML_DECLARATIONS_REJECTED')
    position=0;stack=[];root=None;positions={};count=0
    def add_text(raw):
        require(']]>' not in raw,'INVALID_XML')
        if not stack:require(not raw.strip(SPACE),'INVALID_XML');return
        value=decode(raw)
        parent=stack[-1]
        if parent.children:
            child=parent.children[-1];require(len(child.tail)+len(value)<=8192,'XML_TEXT_LIMIT');child.tail+=value
        else:
            require(len(parent.text)+len(value)<=8192,'XML_TEXT_LIMIT');parent.text+=value
    while position<len(text):
        if text[position]!='<':
            end=text.find('<',position)
            if end<0:end=len(text)
            add_text(text[position:end]);position=end;continue
        if text.startswith('<!--',position):
            end=text.find('-->',position+4);require(end>=0,'INVALID_XML')
            comment=text[position+4:end];require('--' not in comment and not comment.endswith('-'),'INVALID_XML')
            position=end+3;continue
        if text.startswith('<?',position):
            end=text.find('?>',position+2);require(end>=0,'INVALID_XML')
            content=text[position+2:end];match=NAME.match(content);require(match is not None,'INVALID_XML')
            target=match[0];rest=content[match.end():]
            require(not rest or rest[0] in SPACE,'INVALID_XML')
            if target.lower()=='xml':
                require(target=='xml' and position==0,'INVALID_XML')
                require('&' not in rest,'INVALID_XML_DECLARATION')
                values=attributes(rest)
                require(list(values) in (['version'],['version','encoding'],['version','standalone'],['version','encoding','standalone']),'INVALID_XML_DECLARATION')
                require(values['version']=='1.0' and values.get('standalone','yes') in {'yes','no'},'INVALID_XML_DECLARATION')
                require(values.get('encoding','utf-8').lower() in {'utf-8','utf8'},'XML_UTF8_DECLARATION_REQUIRED')
            else:on_instruction()
            position=end+2;continue
        require(not text.startswith('<!',position),'XML_MARKUP_UNSUPPORTED')
        cursor=position+1;quote=None
        while cursor<len(text):
            character=text[cursor]
            if quote:
                if character==quote:quote=None
            elif character in '\"\'':quote=character
            elif character=='>':break
            elif character=='<':raise TextError('INVALID_XML')
            cursor+=1
        require(cursor<len(text) and quote is None,'INVALID_XML')
        body=text[position+1:cursor];position=cursor+1
        if body.startswith('/'):
            require(bool(stack) and re.fullmatch(r'/[A-Za-z_][A-Za-z0-9_.:-]{0,255}[ \t\n]*',body) is not None,'INVALID_XML')
            require(stack[-1].tag==body[1:].rstrip(SPACE),'INVALID_XML');stack.pop();continue
        empty=body.endswith('/')
        if empty:body=body[:-1]
        match=NAME.match(body);require(match is not None,'INVALID_XML')
        count+=1;require(count<=8000 and len(stack)<32,'XML_STRUCTURE_LIMIT')
        node=Node(match[0],attributes(body[match.end():]));positions[id(node)]=count
        if stack:stack[-1].children.append(node)
        else:require(root is None,'INVALID_XML');root=node
        if not empty:stack.append(node)
    require(root is not None and not stack,'INVALID_XML')
    return root,positions
