"""Bounded quiescent-tree copies, exact inventories and fresh restore drills."""
import os
from pathlib import Path
import stat
from . import contracts as c,runtime as r

def _identity(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_nlink,getattr(info,'st_file_attributes',0))

def _safe(path,directory=False):
    with r.io_errors():
        r.guarded.selected_path(path);info=path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:c.fail('TREE_LINK_REFUSED')
        if directory:
            if not stat.S_ISDIR(info.st_mode):c.fail('TREE_DIRECTORY_REQUIRED')
        elif not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:c.fail('TREE_REGULAR_SINGLE_LINK_REQUIRED')
        return info

def source_path(selector):
    c.selector(selector);path=r.local_path(selector);_safe(path,True);return path

def scan(root,excluded=()):
    """Never follows an excluded subtree; included nodes must be portable and regular."""
    files={};directories=[];omitted=[];fingerprints={};seen=set();count=0;total=0
    prefixes=[name.casefold() for name in c.exclusions(list(excluded))]
    def walk(path,relative=''):
        nonlocal count,total
        before=_safe(path,True);fingerprints[relative]=_identity(before)
        entries=[]
        with r.io_errors(),os.scandir(path) as iterator:
            for entry in iterator:
                count+=1
                if count>c.MAX_ENTRIES:c.fail('TREE_ENTRY_LIMIT')
                entries.append(entry.name)
        for name in sorted(entries):
            selected=name if not relative else relative+'/'+name;c.relative(selected);folded=selected.casefold()
            if any(folded==prefix or folded.startswith(prefix+'/') for prefix in prefixes):omitted.append(selected);continue
            if folded in seen:c.fail('TREE_CASE_COLLISION')
            seen.add(folded);target=path/name
            with r.io_errors():info=target.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:c.fail('TREE_LINK_REFUSED')
            if stat.S_ISDIR(info.st_mode):
                directories.append(selected)
                if len(directories)>c.MAX_DIRS:c.fail('TREE_DIRECTORY_LIMIT')
                walk(target,selected)
            else:
                info=_safe(target)
                if info.st_size>c.MAX_FILE:c.fail('TREE_FILE_LIMIT')
                total+=info.st_size
                if len(files)>=c.MAX_FILES or total>c.MAX_TOTAL:c.fail('TREE_TOTAL_LIMIT')
                files[selected]=info.st_size;fingerprints[selected]=_identity(info)
        if _identity(_safe(path,True))!=_identity(before):c.fail('SOURCE_CHANGED_DURING_SCAN')
    walk(root)
    return dict(files=dict(sorted(files.items())),directories=sorted(directories),excluded=sorted(omitted),fingerprints=fingerprints,total_bytes=total)

def _make_directories(root,names):
    for name in sorted(names,key=lambda name:(len(name.split('/')),name)):r.mkdir(root/name)

def _read_stable(path,identity):
    if _identity(_safe(path))!=identity:c.fail('SOURCE_CHANGED')
    raw=r.read_bytes(path,c.MAX_FILE)
    if _identity(_safe(path))!=identity:c.fail('SOURCE_CHANGED')
    return raw

def manifest(raw,expected_id):
    value=r.decode(raw);c.fields(value,('format','snapshot_id','source','exclusions','excluded','directories','files','total_bytes'))
    if value['format']!='outlands-full-snapshot-v1' or c.identifier(value['snapshot_id'])!=expected_id:c.fail('SNAPSHOT_MANIFEST_INVALID')
    c.selector(value['source']);c.exclusions(value['exclusions']);c.integer(value['total_bytes'],0,c.MAX_TOTAL)
    if type(value['files']) is not dict or len(value['files'])>c.MAX_FILES or type(value['directories']) is not list or len(value['directories'])>c.MAX_DIRS or type(value['excluded']) is not list or len(value['excluded'])>c.MAX_ENTRIES:c.fail('SNAPSHOT_MANIFEST_LIMIT')
    seen=set();total=0
    for name in [*value['directories'],*value['files']]:
        c.relative(name);folded=name.casefold()
        if folded in seen:c.fail('SNAPSHOT_PATH_COLLISION')
        seen.add(folded)
        for parent in Path(name).parents:
            if parent!=Path('.') and parent.as_posix() not in value['directories']:c.fail('SNAPSHOT_DIRECTORY_MISSING')
    for name,item in value['files'].items():
        c.fields(item,('bytes','sha256'));c.integer(item['bytes'],0,c.MAX_FILE);c.pin(item['sha256']);total+=item['bytes']
    for name in value['excluded']:c.relative(name)
    if total!=value['total_bytes'] or total>c.MAX_TOTAL or r.encode(value)!=raw:c.fail('SNAPSHOT_MANIFEST_INVALID')
    return value

def verify_tree(root,value):
    captured=scan(root)
    if captured['directories']!=value['directories'] or set(captured['files'])!=set(value['files']):c.fail('SNAPSHOT_INVENTORY_MISMATCH')
    for name,pin in value['files'].items():
        raw=_read_stable(root/name,captured['fingerprints'][name])
        if len(raw)!=pin['bytes'] or r.digest(raw)!=pin['sha256']:c.fail('SNAPSHOT_CONTENT_MISMATCH')
    if scan(root)!=captured:c.fail('SNAPSHOT_CHANGED_DURING_VERIFY')
    return dict(file_count=len(value['files']),directory_count=len(value['directories']),total_bytes=value['total_bytes'])

def snapshot(job_id,request):
    c.identifier(job_id);c.request('snapshot',request);source=source_path(request['source']);captured=scan(source,request['exclusions']);target=r.local_path('snapshots/'+job_id,False);r.mkdir(target);r.mkdir(target/'files');_make_directories(target/'files',captured['directories']);inventory={}
    for name in captured['files']:
        raw=_read_stable(source/name,captured['fingerprints'][name]);r.write_new(target/'files'/name,raw);inventory[name]=dict(bytes=len(raw),sha256=r.digest(raw))
    if scan(source,request['exclusions'])!=captured:c.fail('SOURCE_CHANGED')
    for name,pin in inventory.items():
        raw=_read_stable(source/name,captured['fingerprints'][name])
        if r.digest(raw)!=pin['sha256']:c.fail('SOURCE_CHANGED')
    value=dict(format='outlands-full-snapshot-v1',snapshot_id=job_id,source=request['source'],exclusions=c.exclusions(request['exclusions']),excluded=captured['excluded'],directories=captured['directories'],files=inventory,total_bytes=captured['total_bytes']);raw=r.encode(value);manifest(raw,job_id);r.write_new(target/'manifest.json',raw);verified=verify_tree(target/'files',value)
    if scan(source,request['exclusions'])!=captured:c.fail('SOURCE_CHANGED')
    pin=r.digest(raw);marker=dict(format='outlands-snapshot-commit-v1',snapshot_id=job_id,manifest_sha256=pin,**verified);r.write_new(target/'COMMITTED.json',r.encode(marker));verify_snapshot(job_id,pin)
    return dict(snapshot_id=job_id,manifest_sha256=pin,target='snapshots/'+job_id,excluded_count=len(value['excluded']),**verified)

def _root_inventory(path,names):
    _safe(path,True)
    actual=set()
    with r.io_errors(),os.scandir(path) as entries:
        for entry in entries:
            actual.add(entry.name)
            if len(actual)>len(names):c.fail('SNAPSHOT_ROOT_INVENTORY_MISMATCH')
    if actual!=set(names):c.fail('SNAPSHOT_ROOT_INVENTORY_MISMATCH')

def verify_snapshot(snapshot_id,manifest_sha256):
    c.identifier(snapshot_id);return verify_package(r.local_path('snapshots/'+snapshot_id),manifest_sha256,snapshot_id)

def verify_package(target,manifest_sha256,snapshot_id=None):
    c.pin(manifest_sha256);_root_inventory(target,('files','manifest.json','COMMITTED.json'));raw=r.read_bytes(target/'manifest.json')
    if r.digest(raw)!=manifest_sha256:c.fail('SNAPSHOT_MANIFEST_HASH_MISMATCH')
    parsed=r.decode(raw)
    if type(parsed) is not dict:c.fail('SNAPSHOT_MANIFEST_INVALID')
    identifier=c.identifier(parsed.get('snapshot_id'));value=manifest(raw,snapshot_id or identifier)
    marker=r.decode(r.read_bytes(target/'COMMITTED.json'));verified=verify_tree(target/'files',value);expected=dict(format='outlands-snapshot-commit-v1',snapshot_id=value['snapshot_id'],manifest_sha256=manifest_sha256,**verified)
    if r.encode(marker)!=r.encode(expected):c.fail('SNAPSHOT_COMMIT_MISMATCH')
    return value,verified

def restore(job_id,snapshot_id,manifest_sha256):
    return _restore_package(job_id,r.local_path('snapshots/'+snapshot_id),manifest_sha256,snapshot_id)

def restore_imported(job_id,request):
    c.request('restore_imported',request);return _restore_package(job_id,source_path(request['source']),request['manifest_sha256'])

def _restore_package(job_id,package,manifest_sha256,snapshot_id=None):
    value,verified=verify_package(package,manifest_sha256,snapshot_id);snapshot_id=value['snapshot_id'];source=package/'files';target=r.local_path('restores/'+job_id,False);r.mkdir(target);r.mkdir(target/'files');_make_directories(target/'files',value['directories'])
    for name,pin in value['files'].items():
        raw=r.read_bytes(source/name,c.MAX_FILE)
        if len(raw)!=pin['bytes'] or r.digest(raw)!=pin['sha256']:c.fail('SNAPSHOT_CONTENT_MISMATCH')
        r.write_new(target/'files'/name,raw)
    verify_tree(target/'files',value);verify_package(package,manifest_sha256,snapshot_id);receipt=dict(format='outlands-restore-drill-v1',job_id=job_id,snapshot_id=snapshot_id,manifest_sha256=manifest_sha256,**verified);raw=r.encode(receipt);r.write_new(target/'RESTORED.json',raw)
    result=dict(snapshot_id=snapshot_id,manifest_sha256=manifest_sha256,receipt_sha256=r.digest(raw),target='restores/'+job_id,**verified);verify_restore(job_id,result,value);return result

def verify_restore(job_id,result,value):
    target=r.local_path('restores/'+job_id);_root_inventory(target,('files','RESTORED.json'));raw=r.read_bytes(target/'RESTORED.json');expected=dict(format='outlands-restore-drill-v1',job_id=job_id,snapshot_id=result['snapshot_id'],manifest_sha256=result['manifest_sha256'],file_count=result['file_count'],directory_count=result['directory_count'],total_bytes=result['total_bytes'])
    if r.digest(raw)!=result['receipt_sha256'] or r.encode(r.decode(raw))!=r.encode(expected):c.fail('RESTORE_RECEIPT_MISMATCH')
    verify_tree(target/'files',value)
    return True

def seed_fictional(root):
    fixture=r.decode(r.read_bytes(r.SOURCE/'examples/sample-tree.json'))
    for name,variant in fixture['variants'].items():
        c.relative(name);destination=root/'inbox'/name;r.mkdir(destination);_make_directories(destination,variant['directories'])
        for item in variant['files']:r.write_new(destination/c.relative(item['path']),item['text'].encode('utf-8'))
    r.write_new(root/'inbox/sample-tree.json',r.encode(fixture))
