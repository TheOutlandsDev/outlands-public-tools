"""New-only pinned template, preview and DOCX artifacts in private instance folders."""
from . import contracts as c,journal as j,runtime as r,ooxml

def write_template(identifier,request):
    raw=r.encode(request['template']);directory=r.local_path('templates/'+identifier,False);r.mkdir(directory);r.write_new(directory/'template.json',raw);result=dict(template_id=identifier,target='templates/'+identifier,template_sha256=r.digest(raw),parent_id=request['parent_id'],label=request['template']['label']);r.write_new(directory/'READY.json',r.encode(result));return result
def read_template(state,identifier):
    c.identifier(identifier);result=state['templates'].get(identifier)
    if result is None:c.fail('TEMPLATE_NOT_REGISTERED')
    directory=r.local_path(result['target']);raw=r.read_bytes(directory/'template.json',c.MAX_TEMPLATE);expected=j.template_value(state,identifier)
    if r.digest(raw)!=result['template_sha256'] or raw!=r.encode(expected):c.fail('TEMPLATE_HASH_MISMATCH')
    if r.decode(r.read_bytes(directory/'READY.json'))!=result:c.fail('TEMPLATE_MARKER_MISMATCH')
    return expected
def write_preview(identifier,request,state):
    read_template(state,request['template_id']);model=j.compose_preview(state,request);raw=r.encode(model);directory=r.local_path('previews/'+identifier,False);r.mkdir(directory);r.write_new(directory/'preview.json',raw);result=dict(preview_id=identifier,target='previews/'+identifier,preview_sha256=r.digest(raw),template_id=request['template_id'],template_sha256=request['template_sha256'],values_sha256=model['values_sha256'],summary=model['summary']);r.write_new(directory/'READY.json',r.encode(result));return result
def read_preview(state,identifier):
    c.identifier(identifier);result=state['previews'].get(identifier)
    if result is None:c.fail('PREVIEW_NOT_REGISTERED')
    read_template(state,result['template_id']);directory=r.local_path(result['target']);raw=r.read_bytes(directory/'preview.json',c.MAX_PREVIEW);expected=j.compose_preview(state,state['jobs'][identifier]['request'])
    if r.digest(raw)!=result['preview_sha256'] or raw!=r.encode(expected):c.fail('PREVIEW_HASH_MISMATCH')
    if r.decode(r.read_bytes(directory/'READY.json'))!=result:c.fail('PREVIEW_MARKER_MISMATCH')
    return expected
def write_build(identifier,request,state):
    model=read_preview(state,request['preview_id']);directory=r.local_path('builds/'+identifier,False);r.mkdir(directory);raw=ooxml.build(model);r.write_new(directory/'document.docx',raw);r.write_new(directory/'preview.json',r.encode(model));ooxml.inspect(r.read_bytes(directory/'document.docx',c.MAX_DOCX),model);read_preview(state,request['preview_id']);result=dict(build_id=identifier,target='builds/'+identifier,preview_id=request['preview_id'],preview_sha256=request['preview_sha256'],document_sha256=r.digest(raw),document_bytes=len(raw),parts=8);r.write_new(directory/'BUILT.json',r.encode(result));return result
def read_build(state,identifier):
    c.identifier(identifier);result=state['builds'].get(identifier)
    if result is None:c.fail('BUILD_NOT_REGISTERED')
    model=read_preview(state,result['preview_id']);directory=r.local_path(result['target']);raw=r.read_bytes(directory/'document.docx',c.MAX_DOCX)
    if len(raw)!=result['document_bytes'] or r.digest(raw)!=result['document_sha256']:c.fail('DOCUMENT_HASH_MISMATCH')
    if r.read_bytes(directory/'preview.json',c.MAX_PREVIEW)!=r.encode(model):c.fail('BUILD_PREVIEW_MISMATCH')
    if r.decode(r.read_bytes(directory/'BUILT.json'))!=result:c.fail('BUILD_MARKER_MISMATCH')
    return raw,model,ooxml.inspect(raw,model)
