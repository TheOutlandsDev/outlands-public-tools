"""Pure bounded analysis; explicit file pins and canonical private preview artifacts."""
import csv
import io
from . import contracts as c,runtime as r

def seed_fictional(root):
    for name in ('contract.json','orders.csv','supplement.jsonl','conflicts.jsonl','preview-request.json'):r.write_new(root/'inbox'/name,r.read_bytes(r.SOURCE/'examples'/name))

def selected_sources(request):
    c.request('plan',request);result=[]
    for item in sorted(request['sources'],key=lambda item:item['path']):
        raw=r.read_bytes(r.local_path(item['path']),c.MAX_SOURCE)
        result.append((dict(path=item['path'],format=item['format'],bytes=len(raw),sha256=r.digest(raw)),raw))
    return result

def rows(raw,kind):
    try:text=raw.decode('utf-8-sig')
    except UnicodeError:c.fail('SOURCE_ENCODING_INVALID')
    if kind=='jsonl':
        lines=text.split('\n')
        if lines[-1]=='':lines.pop()
        for number,line in enumerate(lines,1):
            if number>c.MAX_ROWS:c.fail('ROW_LIMIT')
            try:row=r.decode(line.encode('utf-8'));code=None
            except r.WorkbenchError as error:row=None;code=str(error)
            yield number,number,row,code
    else:
        previous=csv.field_size_limit(65536)
        try:
            reader=csv.reader(io.StringIO(text,newline=''),strict=True)
            try:header=next(reader)
            except StopIteration:c.fail('CSV_HEADER_REQUIRED')
            if not header or len(header)>32 or any(not name or len(name.encode('utf-8'))>128 for name in header) or len({v.casefold() for v in header})!=len(header):c.fail('CSV_HEADER_INVALID')
            header_end=reader.line_num
            for index,row in enumerate(reader,1):
                if index>c.MAX_ROWS:c.fail('ROW_LIMIT')
                start=last+1 if index>1 else header_end+1
                end=reader.line_num
                yield start,end,dict(zip(header,row)) if len(row)==len(header) else None,None if len(row)==len(header) else 'CSV_ROW_WIDTH_INVALID'
                last=end
        except csv.Error:c.fail('CSV_PARSE_INVALID')
        finally:csv.field_size_limit(previous)

def analyze(request,sources):
    c.request('plan',request);contract=request['contract'];groups={};rejected=[];ignored={};total=0
    for source,raw in sources:
        for first,last,row,code in rows(raw,source['format']):
            total+=1
            if total>c.MAX_ROWS:c.fail('ROW_LIMIT')
            provenance=dict(source=source['path'],source_sha256=source['sha256'],first_line=first,last_line=last)
            try:
                if code:c.fail(code)
                normalized,extras=c.normalize(row,contract)
                for name in extras:ignored[name]=ignored.get(name,0)+1
            except r.WorkbenchError as error:
                rejected.append(dict(**provenance,code=str(error)));continue
            key=r.encode(normalized[contract['key']]).decode();digest=r.digest(r.encode(normalized));group=groups.setdefault(key,{})
            if digest not in group:group[digest]=dict(data=normalized,sha256=digest,provenance=[])
            group[digest]['provenance'].append(provenance)
    accepted=[];conflicts=[];duplicates=0;conflict_rows=0
    for key,variants in sorted(groups.items()):
        ordered=[variants[k] for k in sorted(variants)]
        if len(ordered)>1:
            count=sum(len(item['provenance']) for item in ordered);conflict_rows+=count;conflicts.append(dict(key=r.decode(key.encode()),rows=count,variants=ordered))
        else:
            item=ordered[0];duplicates+=len(item['provenance'])-1;accepted.append(dict(key=r.decode(key.encode()),**item))
    summary=dict(input_rows=total,accepted_rows=len(accepted),duplicate_rows=duplicates,rejected_rows=len(rejected),conflict_rows=conflict_rows,conflicting_keys=len(conflicts))
    assert summary['input_rows']==sum(summary[k] for k in ('accepted_rows','duplicate_rows','rejected_rows','conflict_rows'))
    source_info=[s for s,_ in sources];body=dict(contract=contract,sources=source_info,records=accepted,rejected=rejected,conflicts=conflicts,ignored_fields=ignored,summary=summary)
    fingerprint=r.digest(r.encode(body));result=dict(format='outlands-import-preview-v1',fingerprint=fingerprint,**body)
    if len(r.encode(result))>c.MAX_PLAN:c.fail('PLAN_LIMIT')
    return result

def build(request):return analyze(request,selected_sources(request))

def verify_sources(plan):
    for item in plan['sources']:
        raw=r.read_bytes(r.local_path(item['path']),c.MAX_SOURCE)
        if len(raw)!=item['bytes'] or r.digest(raw)!=item['sha256']:c.fail('SOURCE_BYTES_CHANGED')

def write_plan(job_id,request):
    plan=build(request);directory=r.local_path('plans/'+job_id,False);r.mkdir(directory);raw=r.encode(plan);r.write_new(directory/'plan.json',raw);verify_sources(plan)
    result=dict(plan_id=job_id,target='plans/'+job_id,plan_sha256=r.digest(raw),fingerprint=plan['fingerprint'],summary=plan['summary']);r.write_new(directory/'PLANNED.json',r.encode(result));return result

def read_plan(result,*,current=False):
    identifier=c.identifier(result['plan_id']);directory=r.local_path('plans/'+identifier)
    raw=r.read_bytes(directory/'plan.json',c.MAX_PLAN)
    if r.digest(raw)!=result['plan_sha256']:c.fail('PLAN_HASH_MISMATCH')
    if r.decode(r.read_bytes(directory/'PLANNED.json'))!=result:c.fail('PLAN_MARKER_MISMATCH')
    plan=r.decode(raw)
    c.fields(plan,('format','fingerprint','contract','sources','records','rejected','conflicts','ignored_fields','summary'))
    if plan['format']!='outlands-import-preview-v1' or plan['fingerprint']!=result['fingerprint'] or plan['summary']!=result['summary']:c.fail('PLAN_CONTRACT_MISMATCH')
    c.pin(plan['fingerprint']);c.contract(plan['contract'])
    body={k:v for k,v in plan.items() if k not in ('format','fingerprint')}
    if r.digest(r.encode(body))!=plan['fingerprint']:c.fail('PLAN_FINGERPRINT_MISMATCH')
    if current:
        verify_sources(plan);request=dict(sources=[dict(path=s['path'],format=s['format']) for s in plan['sources']],contract=plan['contract'])
        if build(request)!=plan:c.fail('PLAN_REPLAY_MISMATCH')
    return plan
