"""Guarded fresh private snapshots and revalidated comparison/plan artifacts."""
from . import contracts as c,journal as j,runtime as r,engine
from .vendor import preflight
COLLECTION={'candidate':'candidates','comparison':'comparisons','plan':'plans'}

def verify_payload(directory,request):
    rows=c.inventory(request['manifest'])
    try:
        with preflight._root_scope(directory):
            if preflight.candidate_inventory(directory,rows)!=rows:c.fail('PAYLOAD_MANIFEST_MISMATCH')
    except (preflight.PreflightError,OSError):c.fail('PAYLOAD_UNSAFE_OR_CHANGED')

def capture(directory,request):
    source=r.local_path(request['source']);rows=c.inventory(request['manifest'])
    try:
        with preflight._root_scope(source):
            verify_payload(source,request);r.mkdir(directory);payload=directory/'payload';r.mkdir(payload)
            directories=sorted({'/'.join(row['path'].split('/')[:i]) for row in rows for i in range(1,len(row['path'].split('/')))},key=lambda n:(n.count('/'),n))
            for name in directories:r.mkdir(payload/name)
            for row in rows:
                info,raw=preflight.hash_file(source/row['path'],limit=c.MAX_FILE,collect=True)
                if info!={key:row[key] for key in ('size','sha256')}:c.fail('PAYLOAD_MANIFEST_MISMATCH')
                r.write_new(payload/row['path'],raw)
            verify_payload(source,request);verify_payload(payload,request)
    except (preflight.PreflightError,OSError):c.fail('PAYLOAD_UNSAFE_OR_CHANGED')

def content(state,kind,request):
    if kind=='candidate':return engine.candidate(request)
    if kind=='comparison':
        read(state,'candidate',request['baseline_id']);read(state,'candidate',request['candidate_id']);return j.comparison(state,request)
    read(state,'comparison',request['comparison_id']);return j.plan_value(state,request)

def write(state,identifier,kind,request):
    value=content(state,kind,request);result=j.result_for(state,identifier,kind,request);directory=r.local_path(result['target'],False)
    if kind=='candidate':capture(directory,request)
    else:r.mkdir(directory)
    r.write_new(directory/(kind+'.json'),r.encode(value))
    if kind=='candidate':r.write_new(directory/'manifest.json',r.encode(request['manifest']));r.write_new(directory/'launcher.json',r.encode(request['launcher']))
    r.write_new(directory/'READY.json',r.encode(result));return result

def read(state,kind,identifier):
    c.choice(kind,COLLECTION);c.identifier(identifier);result=state[COLLECTION[kind]].get(identifier)
    if result is None:c.fail('ARTIFACT_NOT_REGISTERED')
    request=state['jobs'][identifier]['request'];expected=content(state,kind,request);directory=r.local_path(result['target']);raw=r.read_bytes(directory/(kind+'.json'),c.MAX_REPORT)
    if raw!=r.encode(expected) or r.digest(raw)!=result[kind+'_sha256']:c.fail('ARTIFACT_HASH_MISMATCH')
    if r.decode(r.read_bytes(directory/'READY.json'))!=result:c.fail('ARTIFACT_MARKER_MISMATCH')
    if kind=='candidate':
        if r.read_bytes(directory/'manifest.json')!=r.encode(request['manifest']) or r.read_bytes(directory/'launcher.json')!=r.encode(request['launcher']):c.fail('CANDIDATE_METADATA_MISMATCH')
        verify_payload(r.local_path(result['target']+'/payload'),request)
    return expected
