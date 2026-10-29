"""Registered new-only private profile/evaluation/plan files, revalidated on read."""
from . import contracts as c,journal as j,runtime as r

COLLECTION={'profile':'profiles','evaluation':'evaluations','plan':'plans'}

def content(state,kind,request):
    if kind=='profile':return request['profile']
    if kind=='evaluation':read(state,'profile',request['profile_id']);return j.evaluate(state,request)
    read(state,'evaluation',request['evaluation_id']);return j.plan_value(state,request)

def write(state,identifier,kind,request):
    value=content(state,kind,request);result=j.result_for(state,identifier,kind,request);directory=r.local_path(result['target'],False);r.mkdir(directory);r.write_new(directory/(kind+'.json'),r.encode(value));r.write_new(directory/'READY.json',r.encode(result));return result

def read(state,kind,identifier):
    c.choice(kind,COLLECTION);c.identifier(identifier);result=state[COLLECTION[kind]].get(identifier)
    if result is None:c.fail('ARTIFACT_NOT_REGISTERED')
    request=state['jobs'][identifier]['request'];expected=content(state,kind,request);directory=r.local_path(result['target']);raw=r.read_bytes(directory/(kind+'.json'),c.MAX_PROFILE if kind=='profile' else c.MAX_REPORT)
    if raw!=r.encode(expected) or r.digest(raw)!=result[kind+'_sha256']:c.fail('ARTIFACT_HASH_MISMATCH')
    if r.decode(r.read_bytes(directory/'READY.json'))!=result:c.fail('ARTIFACT_MARKER_MISMATCH')
    return expected
