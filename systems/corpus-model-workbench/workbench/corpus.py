"""Portable coding/DevOps corpus database. Python 3.10+, standard library only."""
import argparse
import gzip
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import uuid
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,build_opener,ProxyHandler

APP=Path(__file__).resolve().parent
ROOT=None
DB=None
def now(): return datetime.now(timezone.utc).isoformat()
def encode(value): return json.dumps(value,ensure_ascii=False,separators=(',',':'))
def digest(value): return hashlib.sha256(value.encode('utf-8')).hexdigest()
def file_hash(path):
    from .runtime import read_bytes
    return hashlib.sha256(read_bytes(local_path(path))).hexdigest()
def local_path(value,must_exist=True):
    from .runtime import local_path as selected
    return selected(value,must_exist)
def connect():
    from .runtime import connect as selected
    return selected()
def event(con,action,detail): con.execute('INSERT INTO events(action,detail_json,created_utc) VALUES(?,?,?)',(action,encode(detail),now()))
def initialize():
    from .runtime import initialize_database
    return initialize_database()
def iter_jsonl(path):
    from .runtime import jsonl
    yield from jsonl(path)
def register_source(con,path,collection,license_note,raw=None):
    path=local_path(path)
    relative=path.relative_to(ROOT).as_posix()
    from .runtime import read_bytes
    if raw is None:raw=read_bytes(path)
    sha=hashlib.sha256(raw).hexdigest()
    source_id=digest(relative+'\0'+sha)
    con.execute('INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?,?,?)',
                (source_id,relative,sha,len(raw),collection,license_note,now()))
    return source_id
def assign_group(con,group,split):
    if split not in {'train','validation','test'}: raise ValueError('Invalid split')
    row=con.execute('SELECT split FROM groups WHERE group_id=?',(group,)).fetchone()
    if row:
        rank={'train':0,'validation':1,'test':2}
        if rank[split]>rank[row[0]]: con.execute('UPDATE groups SET split=? WHERE group_id=?',(split,group))
    else: con.execute('INSERT INTO groups VALUES(?,?)',(group,split))
def normalize_messages(messages):
    normalized=[]
    if type(messages) is not list or not 1<=len(messages)<=128: raise ValueError('MESSAGES_INVALID')
    for row in messages:
        if type(row) is not dict or set(row)!={'role','content'}: raise ValueError('MESSAGE_INVALID')
        role=row.get('role')
        text=row.get('content')
        if role not in {'system','user','assistant'} or not isinstance(text,str): raise ValueError('Only public text chat messages are accepted')
        if text.strip(): normalized.append(dict(role=role,content=text.replace('\r\n','\n').strip()))
    if not normalized or normalized[-1]['role']!='assistant' or not any(x['role']=='user' for x in normalized):
        raise ValueError('Example requires a user prompt and final assistant answer')
    return normalized
def classify(text,labels=None):
    sample=text.casefold()
    ops=bool(re.search(r'\b(devops|docker|kubernetes|ansible|terraform|systemd|ssh|ci/cd|deployment|nginx|ubuntu|linux|powershell|backup|pipeline|observability)\b',sample))
    coding=bool(re.search(r'\b(python|javascript|typescript|php|sql|coding|code|function|pytest|unittest|compiler|csharp|api|refactor|bug|debug|software|programming)\b',sample))
    languages=(labels or {}).get('languages',[])
    if languages: coding=True
    return ('mixed' if ops and coding else 'devops' if ops else 'coding' if coding else 'other'),','.join(str(x) for x in languages)
def sensitive_flags(text):
    checks=[('private_key',r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
            ('credential_pattern',r'\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b'),
            ('credential_assignment',r'(?i)\b(?:password|api_key|access_token|secret_key)\s*[=:]\s*[\x22\x27][^\x22\x27\s]{8,}[\x22\x27]')]
    return [name for name,pattern in checks if re.search(pattern,text)]
def add_record(con,source_id,source_row,source_key,record):
    if type(record) is not dict: raise ValueError('RECORD_INVALID')
    kind=record.get('kind','example')
    if kind not in {'example','document','evaluation'}: raise ValueError('Invalid record kind')
    metadata=dict(record.get('metadata',{}))
    messages=normalize_messages(record['messages']) if kind=='example' else []
    text='\n\n'.join(x['role']+':\n'+x['content'] for x in messages) if messages else str(record.get('text','')).strip()
    if not text: raise ValueError('Empty content')
    canonical=encode(messages) if messages else text.replace('\r\n','\n')
    # Exact dedup is independent of source row, title, group and split.
    content_hash=digest(canonical)
    identifier=content_hash
    group=str(record.get('group_id') or record.get('conversation_group') or 'content:'+content_hash)
    split=record.get('split','test' if kind=='evaluation' else 'train')
    if kind=='evaluation': split='test'
    if messages:
        user_prompts={item['content'].strip() for item in messages if item['role']=='user'}
        heldout=next((row for row in con.execute('SELECT id,prompt FROM benchmark_cases') if row['prompt'].strip() in user_prompts),None)
        if heldout:
            split='test';group='benchmark:'+heldout['id'];metadata['matched_heldout_case']=heldout['id']
    assign_group(con,group,split)
    existing=con.execute('SELECT id,group_id FROM records WHERE content_hash=?',(content_hash,)).fetchone()
    if existing:
        if existing['group_id']!=group:
            left,right=sorted((existing['group_id'],group))
            con.execute('INSERT OR IGNORE INTO group_links VALUES(?,?)',(left,right))
        identifier=existing['id']
    else:
        domain,language=classify(text,metadata.get('labels'))
        domain=record.get('domain',domain)
        if domain not in {'coding','devops','mixed','other'}: raise ValueError('Invalid domain')
        flags=list(dict.fromkeys(record.get('flags',[])+sensitive_flags(text)))
        title=str(record.get('title') or next((x['content'] for x in messages if x['role']=='user'),text)).replace('\n',' ')[:180]
        metadata.setdefault('outcome','unknown')
        stamp=now()
        con.execute('''INSERT INTO records(id,content_hash,kind,title,domain,language,group_id,text,messages_json,
                       metadata_json,flags_json,created_utc,updated_utc) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (identifier,content_hash,kind,title,domain,record.get('language',language),group,text,encode(messages),
                     encode(metadata),encode(flags),stamp,stamp))
    con.execute('INSERT OR IGNORE INTO provenance VALUES(?,?,?,?)',(identifier,source_id,source_row,str(source_key)))
    return not bool(existing)
def reconcile_groups(con):
    # Duplicate-linked conversation families share a split; holdouts win over train.
    parent={row['group_id']:row['group_id'] for row in con.execute('SELECT * FROM groups')}
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    for left,right in con.execute('SELECT * FROM group_links'):
        a,b=find(left),find(right)
        if a!=b: parent[max(a,b)]=min(a,b)
    rank={'train':0,'validation':1,'test':2}
    components={}
    for group,split in con.execute('SELECT * FROM groups'):
        root=find(group)
        components[root]=max(components.get(root,'train'),split,key=lambda x:rank[x])
    for group in parent:
        root=find(group)
        con.execute('UPDATE groups SET split=? WHERE group_id=?',(components[root],group))
        con.execute('UPDATE records SET group_id=? WHERE group_id=?',(root,group))
def import_jsonl(path,collection='user-import',license_note='User-supplied; review intended use'):
    path=local_path(path)
    from .runtime import read_bytes,jsonl_bytes
    raw=read_bytes(path)
    counts=Counter()
    with connect() as con:
        source=register_source(con,path,collection,license_note,raw)
        for number,row in jsonl_bytes(raw,compressed=str(path).endswith('.gz')):
            created=add_record(con,source,number,row.get('id',number),row)
            counts['inserted' if created else 'duplicate_provenance']+=1
        reconcile_groups(con)
        event(con,'import_jsonl',dict(path=path.relative_to(ROOT).as_posix(),counts=dict(counts)))
    return dict(counts)
def status():
    with connect() as con:
        result=dict(schema_version=con.execute('SELECT value FROM meta WHERE key=?',('schema_version',)).fetchone()[0])
        for column in ['status','kind','domain']:
            result[column]=dict(con.execute('SELECT '+column+',COUNT(*) FROM records GROUP BY '+column))
        result['split']=dict(con.execute('SELECT g.split,COUNT(*) FROM records r JOIN groups g USING(group_id) GROUP BY g.split'))
        result['records']=con.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        result['sources']=con.execute('SELECT COUNT(*) FROM sources').fetchone()[0]
        result['provenance_links']=con.execute('SELECT COUNT(*) FROM provenance').fetchone()[0]
        result['embeddings']=con.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0]
        result['embedding_models']=[dict(row) for row in con.execute('SELECT model,model_digest,COUNT(*) AS chunks FROM embeddings GROUP BY model,model_digest')]
        result['training_ready_examples']=con.execute("SELECT COUNT(*) FROM records WHERE kind='example' AND status='approved' AND quality_reviewed=1 AND privacy_reviewed=1 AND rights_reviewed=1 AND context_reviewed=1").fetchone()[0]
    return result
def list_records(query='',domain='',kind='',review_status='',split='',limit=25,offset=0):
    where=[]; params=[]
    join=''
    if query.strip():
        words=re.findall(r'[\w]+',query,flags=re.UNICODE)
        if words:
            expression=' AND '.join('"'+word.replace('"','""')+'"' for word in words[:12])
            join=' JOIN record_fts f ON f.rowid=r.rowid'
            where.append('record_fts MATCH ?');params.append(expression)
    for column,value in [('r.domain',domain),('r.kind',kind),('r.status',review_status),('g.split',split)]:
        if value: where.append(column+'=?');params.append(value)
    clause=' WHERE '+' AND '.join(where) if where else ''
    with connect() as con:
        base=' FROM records r JOIN groups g USING(group_id)'+join+clause
        total=con.execute('SELECT COUNT(*)'+base,params).fetchone()[0]
        rows=[dict(row) for row in con.execute('SELECT r.id,r.title,r.domain,r.kind,r.status,g.split,r.language,r.flags_json'+base+' ORDER BY r.created_utc,r.id LIMIT ? OFFSET ?',params+[min(max(int(limit),1),100),max(int(offset),0)])]
    return dict(total=total,records=rows)
def get_record(identifier):
    with connect() as con:
        row=con.execute('SELECT r.*,g.split FROM records r JOIN groups g USING(group_id) WHERE id=?',(identifier,)).fetchone()
        if not row: raise ValueError('Record not found')
        result=dict(row)
        for key in ['messages_json','metadata_json','flags_json']: result[key.removesuffix('_json')]=json.loads(result.pop(key))
        result['provenance']=[dict(x) for x in con.execute('SELECT s.path,s.collection,s.license_note,p.source_row,p.source_key FROM provenance p JOIN sources s USING(source_id) WHERE record_id=?',(identifier,))]
        result['reviews']=[dict(x) for x in con.execute('SELECT actor,status,note,checks_json,created_utc FROM reviews WHERE record_id=? ORDER BY id',(identifier,))]
        return result
def review_record(identifier,decision,actor,note,checks):
    if type(checks) is not dict or set(checks)!={'quality','privacy','rights','context'} or any(type(v) is not bool for v in checks.values()): raise ValueError('REVIEW_CHECKS_INVALID')
    if type(actor) is not str or type(note) is not str or len(actor)>128 or len(note)>4096: raise ValueError('REVIEW_TEXT_INVALID')
    if decision not in {'pending','approved','rejected'} or not actor.strip() or not note.strip(): raise ValueError('Decision, reviewer and note are required')
    required=['quality','privacy','rights','context']
    if decision=='approved' and not all(checks.get(key) is True for key in required):
        raise ValueError('Approval requires correctness, privacy, use-rights and context review')
    with connect() as con:
        row=con.execute('SELECT id FROM records WHERE id=?',(identifier,)).fetchone()
        if not row: raise ValueError('Record not found')
        if decision=='approved':
            resolved=materialize(identifier)
            checks={**checks,'materialized_sha256':digest(encode(resolved['messages']))}
        con.execute('UPDATE records SET status=?,quality_reviewed=?,privacy_reviewed=?,rights_reviewed=?,context_reviewed=?,updated_utc=? WHERE id=?',
                    (decision,*[int(checks.get(key) is True) for key in required],now(),identifier))
        con.execute('INSERT INTO reviews(record_id,actor,status,note,checks_json,created_utc) VALUES(?,?,?,?,?,?)',(identifier,actor.strip(),decision,note.strip(),encode(checks),now()))
        event(con,'review',dict(record_id=identifier,status=decision,actor=actor))
    return dict(id=identifier,status=decision)
def materialize(identifier,max_characters=200000):
    record=get_record(identifier)
    messages=record['messages']
    meta=record['metadata']
    context=meta.get('context')
    if type(max_characters) is not int or not 1<=max_characters<=200000: raise ValueError('CONTEXT_LIMIT_INVALID')
    if not context:
        if len(encode(messages))>max_characters: raise ValueError('CONTEXT_LIMIT')
        return dict(messages=messages,context_mode='complete_supplied_messages',tool_context_excluded=True)
    base=local_path(meta['supplement_root'])
    path=local_path(base/context['relative_path'])
    before=context.get('preceding_events')
    prior=[]
    for _,item in iter_jsonl(path):
        if before and before[0]<=item.get('event_id',-1)<=before[1] and item.get('kind')=='message':
            data=item.get('data',{})
            if data.get('role') in {'user','assistant'} and isinstance(data.get('text'),str):
                prior.append(dict(role=data['role'],content=data['text']))
    combined=prior+messages
    if len(encode(combined))>max_characters: raise ValueError('Context exceeds character cap; increase cap explicitly. Content is never silently truncated.')
    return dict(messages=combined,context_mode='recorded_preceding_dialogue_plus_target_pair',
                tool_context_excluded=True,recorded_context_completeness=context.get('completeness','unknown'))
def create_chunks(con,record_id,text,size=1800,overlap=200):
    chunks=[]
    for ordinal,start in enumerate(range(0,len(text),size-overlap)):
        content=text[start:start+size]
        identifier=digest(record_id+':'+str(ordinal)+':'+content)
        con.execute('INSERT OR IGNORE INTO chunks VALUES(?,?,?,?,?)',(identifier,record_id,ordinal,content,digest(content)))
        chunks.append(dict(id=identifier,record_id=record_id,ordinal=ordinal,text=content))
        if start+size>=len(text): break
    return chunks
def eligible_sql(kind):
    # Holdout examples and evaluation answers are never a default RAG corpus.
    base="r.status='approved' AND r.quality_reviewed=1 AND r.privacy_reviewed=1 AND r.rights_reviewed=1 AND r.context_reviewed=1"
    return base+(" AND r.kind='example'" if kind=='sft' else " AND r.kind='document' AND g.split='train'")
def export_dataset(kind,domain='',max_characters=200000):
    if kind not in {'sft','rag','review'}: raise ValueError('Invalid export type')
    run=now().replace(':','').replace('-','').replace('+','_')+'_'+uuid.uuid4().hex[:6]
    destination=local_path('exports/'+run,False)
    from . import runtime
    runtime._mkdir(destination)
    counts=Counter();files={};skipped=[];leak_check={}
    with connect() as con:
        where="r.status='pending'" if kind=='review' else eligible_sql(kind)
        params=[]
        if domain: where+=' AND r.domain=?';params.append(domain)
        selected=list(con.execute('SELECT r.*,g.split FROM records r JOIN groups g USING(group_id) WHERE '+where+' ORDER BY r.id',params))
        handles={}
        names=['candidates.jsonl'] if kind=='review' else ['rag.jsonl'] if kind=='rag' else [x+'.jsonl' for x in ['train','validation','test']]
        try:
            handles={name:runtime.BoundedText() for name in names}
            for row in selected:
                split=row['split']
                meta=json.loads(row['metadata_json'])
                if kind=='sft':
                    try: resolved=materialize(row['id'],max_characters)
                    except (OSError,ValueError):
                        skipped.append(dict(id=row['id'],reason='CONTEXT_UNAVAILABLE_OR_LIMIT'));continue
                    last=con.execute('SELECT checks_json FROM reviews WHERE record_id=? ORDER BY id DESC LIMIT 1',(row['id'],)).fetchone()
                    approved_hash=json.loads(last[0]).get('materialized_sha256') if last else None
                    if approved_hash!=digest(encode(resolved['messages'])):
                        skipped.append(dict(id=row['id'],reason='CURRENT_CONTENT_REVIEW_REQUIRED'));continue
                    payload=dict(messages=resolved['messages'])
                    name=split+'.jsonl'
                    leak_check[row['id']]=dict(split=split,group_id=row['group_id'],context_mode=resolved['context_mode'])
                elif kind=='rag':
                    for chunk in create_chunks(con,row['id'],row['text']):
                        payload=dict(id=chunk['id'],text=chunk['text'],metadata=dict(record_id=row['id'],title=row['title'],
                            domain=row['domain'],language=row['language'],group_id=row['group_id'],split=split,
                            source_paths=[x['path'] for x in get_record(row['id'])['provenance']],review_status='approved',chunk=chunk['ordinal']))
                        handles['rag.jsonl'].write(encode(payload)+'\n');counts['rag_chunks']+=1
                    continue
                else:
                    payload=dict(id=row['id'],title=row['title'],kind=row['kind'],domain=row['domain'],split=split,
                                 group_id=row['group_id'],messages=json.loads(row['messages_json']),text=row['text'],
                                 metadata=meta,flags=json.loads(row['flags_json']),status='pending',training_ready=False)
                    name='candidates.jsonl'
                handles[name].write(encode(payload)+'\n');counts[name]+=1
        except BaseException:
            raise
        for name,handle in handles.items():
            runtime.write_new(destination/name,handle.bytes())
        for name in names:
            path=destination/name;files[name]=dict(bytes=path.stat().st_size,sha256=file_hash(path))
        manifest=dict(kind=kind,created_utc=now(),counts=dict(counts),files=files,skipped=skipped,
                      training_ready=kind=='sft' and bool(leak_check),human_approval_required=True,
                      context_truncated=False,tool_context_excluded=True if kind=='sft' else None,
                      groups_kept_together=True,exact_content_deduplicated=True,domain=domain or 'all',
                      notice='Training candidates require review. RAG exports contain approved training documents only. Fine-tuning runs separately from Ollama.')
        runtime.write_new(destination/'manifest.json',json.dumps(manifest,indent=2).encode('utf-8'))
        if kind=='sft': runtime.write_new(destination/'provenance.json',json.dumps(leak_check,indent=2).encode('utf-8'))
        event(con,'export',dict(kind=kind,directory=destination.relative_to(ROOT).as_posix(),counts=dict(counts)))
    return dict(directory=destination.relative_to(ROOT).as_posix(),manifest=manifest)
def ollama_request(endpoint,payload=None,url=None):
    from .runtime import model_request
    return model_request(endpoint,payload,url)
def embed_corpus(model,url=None):
    catalog=ollama_request('/api/tags',url=url)
    matches=[row for row in catalog.get('models',[]) if row.get('name') in {model,model+':latest'} or row.get('model')==model]
    if not matches or not matches[0].get('digest'): raise ValueError('Model must already be installed in Ollama and expose a digest')
    model_name=matches[0]['name'];model_digest=matches[0]['digest'];written=0
    with connect() as con:
        rows=list(con.execute('SELECT r.* FROM records r JOIN groups g USING(group_id) WHERE '+eligible_sql('rag')))
        chunks=[]
        for row in rows: chunks.extend(create_chunks(con,row['id'],row['text']))
        for start in range(0,len(chunks),8):
            batch=[item for item in chunks[start:start+8] if not con.execute('SELECT 1 FROM embeddings WHERE chunk_id=? AND model=? AND model_digest=?',(item['id'],model_name,model_digest)).fetchone()]
            if not batch: continue
            response=ollama_request('/api/embed',dict(model=model_name,input=[item['text'] for item in batch],truncate=False),url)
            vectors=response.get('embeddings',[])
            if len(vectors)!=len(batch): raise ValueError('Ollama embedding count mismatch')
            for item,vector in zip(batch,vectors):
                if not vector or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in vector): raise ValueError('Invalid embedding vector')
                con.execute('INSERT INTO embeddings VALUES(?,?,?,?,?,?)',(item['id'],model_name,model_digest,len(vector),encode(vector),now()))
                written+=1
            con.commit()
        event(con,'embed',dict(model=model_name,digest=model_digest,chunks_written=written))
    return dict(model=model_name,digest=model_digest,chunks_written=written)
def semantic_search(query,model,url=None,limit=5):
    tags=ollama_request('/api/tags',url=url)
    match=next((row for row in tags.get('models',[]) if row.get('name') in {model,model+':latest'}),None)
    if not match: raise ValueError('Embedding model not installed')
    vector=ollama_request('/api/embed',dict(model=match['name'],input=query,truncate=False),url)['embeddings'][0]
    norm=math.sqrt(sum(x*x for x in vector))
    if not norm: raise ValueError('Zero query vector')
    found=[]
    with connect() as con:
        for row in con.execute('SELECT c.id,c.text,r.title,e.vector_json FROM embeddings e JOIN chunks c ON c.id=e.chunk_id JOIN records r ON r.id=c.record_id JOIN groups g USING(group_id) WHERE e.model=? AND e.model_digest=? AND '+eligible_sql('rag'),(match['name'],match['digest'])):
            candidate=json.loads(row['vector_json'])
            if len(candidate)!=len(vector): raise ValueError('Embedding dimension mismatch')
            other_norm=math.sqrt(sum(x*x for x in candidate))
            score=sum(x*y for x,y in zip(vector,candidate))/(norm*other_norm) if other_norm else 0
            found.append(dict(id=row['id'],title=row['title'],score=score,text=row['text']))
    return sorted(found,key=lambda x:x['score'],reverse=True)[:limit]
def backup():
    from . import runtime
    destination=local_path('backups/'+uuid.uuid4().hex+'.sqlite3',False)
    runtime.write_new(destination,b'')
    with connect() as source, runtime.io_errors(), runtime.guarded._store_scope(destination,initial=True):
        target=sqlite3.connect(destination.as_uri()+'?mode=rw',uri=True)
        try:source.backup(target);runtime.validate_schema(target)
        finally:target.close()
    return dict(file=destination.relative_to(ROOT).as_posix(),sha256=file_hash(destination),bytes=destination.stat().st_size)
def main():
    from . import runtime
    parser=runtime.Parser(prog='corpus-workbench',description=__doc__,allow_abbrev=False)
    parser.add_argument('--workspace',required=True)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init');sub.add_parser('status');sub.add_parser('backup')
    recovery=sub.add_parser('recover');recovery.add_argument('--confirm-stopped',action='store_true')
    sub.add_parser('demo')
    importer=sub.add_parser('import-jsonl');importer.add_argument('path');importer.add_argument('--collection',default='user-import')
    listing=sub.add_parser('search');listing.add_argument('query');listing.add_argument('--domain',default='');listing.add_argument('--limit',type=int,default=25)
    detail=sub.add_parser('show');detail.add_argument('id')
    exporter=sub.add_parser('export');exporter.add_argument('kind',choices=['sft','rag','review']);exporter.add_argument('--domain',default='');exporter.add_argument('--max-characters',type=int,default=200000)
    reviewer=sub.add_parser('review');reviewer.add_argument('id');reviewer.add_argument('decision',choices=['pending','approved','rejected']);reviewer.add_argument('--actor',required=True);reviewer.add_argument('--note',required=True)
    for check in ['quality','privacy','rights','context']: reviewer.add_argument('--'+check+'-reviewed',action='store_true')
    embed=sub.add_parser('embed');embed.add_argument('--model',required=True);embed.add_argument('--url')
    semantic=sub.add_parser('semantic-search');semantic.add_argument('query');semantic.add_argument('--model',required=True);semantic.add_argument('--url')
    server=sub.add_parser('serve');server.add_argument('--port',type=int,default=8765);server.add_argument('--fictional-models',action='store_true')
    sub.add_parser('load-benchmarks');sub.add_parser('leaderboard')
    discover=sub.add_parser('models');discover.add_argument('--url')
    bench=sub.add_parser('benchmark');bench.add_argument('--models',nargs='+',required=True);bench.add_argument('--language',default='');bench.add_argument('--limit',type=int,default=0);bench.add_argument('--url')
    scoring=sub.add_parser('score');scoring.add_argument('id');scoring.add_argument('score',type=float);scoring.add_argument('--actor',required=True);scoring.add_argument('--note',required=True)
    council=sub.add_parser('discuss');council.add_argument('task');council.add_argument('--planner',required=True);council.add_argument('--coder',required=True);council.add_argument('--reviewer',required=True);council.add_argument('--rounds',type=int,default=2);council.add_argument('--url')
    queue=sub.add_parser('queue-discussion');queue.add_argument('id')
    routing=sub.add_parser('recommend');routing.add_argument('language');routing.add_argument('--skill');routing.add_argument('--fallback',default=None)
    args=parser.parse_args()
    if args.command=='recover' and not args.confirm_stopped: raise runtime.WorkbenchError('STOPPED_ASSERTION_REQUIRED')
    runtime.configure(args.workspace,create=args.command in {'init','demo'},confirm_stopped=args.command=='recover')
    if args.command=='init': initialize();result=status()
    elif args.command=='demo':
        from .demo import run
        initialize();result=run()
    elif args.command=='recover': result=runtime.recover()
    elif args.command=='status': result=status()
    elif args.command=='import-jsonl': result=import_jsonl(args.path,args.collection)
    elif args.command=='search': result=list_records(args.query,domain=args.domain,limit=args.limit)
    elif args.command=='show': result=get_record(args.id)
    elif args.command=='review': result=review_record(args.id,args.decision,args.actor,args.note,{key:getattr(args,key+'_reviewed') for key in ['quality','privacy','rights','context']})
    elif args.command=='export': result=export_dataset(args.kind,args.domain,args.max_characters)
    elif args.command=='embed': result=embed_corpus(args.model,args.url)
    elif args.command=='semantic-search': result=semantic_search(args.query,args.model,args.url)
    elif args.command=='backup': result=backup()
    elif args.command in {'load-benchmarks','leaderboard','models','benchmark','score','discuss','queue-discussion','recommend'}:
        from . import models
        if args.command=='load-benchmarks': result=models.load_benchmarks()
        elif args.command=='leaderboard': result=models.leaderboard()
        elif args.command=='models': result=models.discover(args.url)
        elif args.command=='benchmark': result=models.benchmark(args.models,args.language,args.limit,args.url)
        elif args.command=='score': result=models.score(args.id,args.score,args.actor,args.note)
        elif args.command=='discuss': result=models.discuss(args.task,args.planner,args.coder,args.reviewer,args.rounds,args.url)
        elif args.command=='queue-discussion': result=models.queue_discussion(args.id)
        else: result=models.recommend(args.language,args.skill,args.fallback)
    else:
        from .web import serve
        if args.fictional_models:
            from .demo import FictionalClient
            runtime.set_client(FictionalClient())
        serve(args.port);return
    return result
