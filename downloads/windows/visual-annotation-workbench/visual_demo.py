"""Fictional two-view practice and independent PNG/mask/export verification."""
from contextlib import closing
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import struct
import subprocess
import sys
import zlib

ROOT=Path(__file__).resolve().parent
PROPOSAL={'1':[[[8,8],[48,8],[48,40],[8,40]]],'2':[[[20,18],[36,18],[36,30],[20,30]]]}
CORRECTION=copy.deepcopy(PROPOSAL);CORRECTION['1'].append([[60,20],[100,20],[100,50],[60,50]])
LATER=copy.deepcopy(PROPOSAL);LATER['1'].append([[62,22],[102,22],[102,52],[62,52]])
def sha(body):return hashlib.sha256(body).hexdigest()
def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}
def practice_specimens(config):
    from visual_workbench import contracts
    return {part:next(prefix+str(i) for i in range(1000) if contracts.partition(config,prefix+str(i))==part) for part,prefix in [('train','sample-a-'),('test','sample-z-')]}
def seed_demo():
    from visual_workbench import application as app,runtime as r,png
    config=r.decode(r.read_bytes(r.SOURCE/'examples/sample-dataset.json'));app.create(r.encode(config));specimens=practice_specimens(config)
    for seed,(part,specimen) in enumerate(specimens.items()):
        path='inbox/'+specimen+'.png';r.write_new(r.local_path(path,False),png.fictional(512,256,seed))
        app.add_view(r.encode(dict(dataset_id=config['dataset_id'],specimen_id=specimen,view_id='front',file=path,polygons=PROPOSAL)))
    return specimens
def decode_mask(raw):
    # Independent narrow decoder for the canonical filter-0 RGBA exports only.
    stream=io.BytesIO(raw);assert stream.read(8)==b'\x89PNG\r\n\x1a\n';chunks=[];compressed=[];width=height=None
    while True:
        head=stream.read(8);assert len(head)==8;size,kind=struct.unpack('>I4s',head);body=stream.read(size);assert len(body)==size;crc=stream.read(4);assert len(crc)==4 and struct.unpack('>I',crc)[0]==zlib.crc32(kind+body)&0xffffffff;chunks.append(kind)
        if kind==b'IHDR':width,height,bits,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',body);assert (bits,color,compression,filtering,interlace)==(8,6,0,0,0)
        elif kind==b'IDAT':compressed.append(body)
        elif kind==b'IEND':assert body==b'';break
        else:raise AssertionError('Unexpected ancillary metadata in a canonical export.')
    assert chunks==[b'IHDR',b'IDAT',b'IEND'] and not stream.read();pixels=zlib.decompress(b''.join(compressed));stride=width*4+1;assert len(pixels)==stride*height
    assert all(pixels[y*stride]==0 for y in range(height));return width,height,b''.join(pixels[y*stride+1:(y+1)*stride] for y in range(height))
def verify_report(workspace,result,expected,polygons=None):
    folder=workspace/result['directory'];m=result['manifest'];assert not m['training_or_inference_executed'];assert len(m['selected'])==expected
    assert tree(folder).keys()==(set(m['files'])|{'manifest.json'}) and json.loads((folder/'manifest.json').read_bytes())==m
    assert len(m['files'])==4*expected
    for n,row in m['files'].items():
        body=(folder/n).read_bytes();assert row==dict(bytes=len(body),sha256=sha(body))
    for item in m['selected']:
        assert item['partition']=='train' if m['mode']=='training' else item['partition'] in ('test','validation')
        record=json.loads((folder/item['prefix']/'annotation.json').read_bytes());assert record['annotation']['annotation_sha256']==item['annotation_sha256'] and record['annotation']['version']==item['version']
        if polygons is not None:assert record['annotation']['polygons']==polygons
        for key,regions in record['annotation']['polygons'].items():
            w,h,pixels=decode_mask((folder/item['prefix']/('class-'+key+'.png')).read_bytes());assert (w,h)==(512,256)
            rectangles=[]
            for region in regions:
                xs=[p[0] for p in region];ys=[p[1] for p in region];rect=(min(xs),min(ys),max(xs),max(ys));assert set(map(tuple,region))=={(rect[0],rect[1]),(rect[2],rect[1]),(rect[2],rect[3]),(rect[0],rect[3])};rectangles.append(rect)
            for y in range(h):
                for x in range(w):
                    value=255 if any(left<=x+.5<right and top<=y+.5<bottom for left,top,right,bottom in rectangles) else 0;offset=4*(y*w+x);assert pixels[offset:offset+4]==bytes((value,value,value,255))
    return m
def exercise(workspace,application=None):
    development=application is not None;application=Path(application) if development else ROOT/'application'
    if not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_PRIVATE_EXERCISE_REQUIRED')
    sys.path.insert(0,str(application));from visual_workbench import png
    config=json.loads((application/'examples/sample-dataset.json').read_bytes());specimens=practice_specimens(config);calls=[]
    def command(*args,expected=0):
        entry=[str(application/'workbench.py')]
        if development:entry=['-c',"import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv.pop(0);runpy.run_path(sys.argv[0],run_name='__main__')",str(application),str(application/'workbench.py')]
        p=subprocess.run([sys.executable,'-I','-B','-X','utf8',*entry,'--workspace',str(workspace),*map(str,args)],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=60);calls.append(args[0])
        if p.returncode!=expected:
            if workspace.is_dir():(workspace/'failed-command.log').write_bytes(p.stdout+p.stderr)
            raise AssertionError('Original CLI failed; private log retained.')
        return json.loads(p.stdout)
    def request(name,value):
        path=workspace/'inbox'/name;path.write_text(json.dumps(value),encoding='utf-8');return 'inbox/'+name
    def view_args(part='train'):return ['--dataset','sample-visual','--specimen',specimens[part],'--view','front']
    def correct(part,expected,polygons):return dict(dataset_id='sample-visual',specimen_id=specimens[part],view_id='front',expected_sha256=expected,polygons=polygons)
    def review(part,annotation,selected,checks=True,expected=0):return dict(dataset_id='sample-visual',specimen_id=specimens[part],view_id='front',annotation_sha256=annotation,expected_version=expected,status='approved',training_selected=selected,actor='sample_reviewer',note='Fictional geometry and split review',checks=dict(quality=checks,privacy=checks,rights=checks,context=checks))
    command('init');command('create','--file','inbox/sample-dataset.json')
    for seed,(part,specimen) in enumerate(specimens.items()):
        path=workspace/'inbox'/(specimen+'.png');path.write_bytes(png.fictional(512,256,seed));value=dict(dataset_id='sample-visual',specimen_id=specimen,view_id='front',file='inbox/'+path.name,polygons=PROPOSAL);command('add-view','--file',request('view-'+part+'.json',value))
    inputs=tree(workspace/'inbox');first=command('show',*view_args());assert first['annotation']['version']==1 and first['review']['status']=='pending'
    second=command('correct','--file',request('correction.json',correct('train',first['annotation']['annotation_sha256'],CORRECTION)));sha2=second['annotation']['annotation_sha256'];assert second['annotation']['version']==2
    assert command('review','--file',request('review-missing.json',review('train',sha2,True,False)),expected=2)==dict(error='REVIEW_CHECKS_REQUIRED')
    review_file=request('review.json',review('train',sha2,True));command('review','--file',review_file)
    old=command('export','--dataset','sample-visual','--mode','training');verify_report(workspace,old,1,CORRECTION);old_bytes=tree(workspace/old['directory'])
    before=tree(workspace);assert command('review','--file',review_file,expected=2)==dict(error='REVIEW_VERSION_CONFLICT') and tree(workspace)==before
    third=command('correct','--file',request('later.json',correct('train',sha2,LATER)));sha3=third['annotation']['annotation_sha256'];assert third['annotation']['version']==3 and third['annotation']['parent_sha256']==sha2
    pending=command('show',*view_args());assert pending['review']==dict(status='pending',training_selected=False,row_version=0)
    omitted=command('export','--dataset','sample-visual','--mode','training');verify_report(workspace,omitted,0)
    command('review','--file',request('later-review.json',review('train',sha3,True)))
    # Held-out proposals get a manual version, then explicit review; selection
    # for training is independently refused by the original application.
    from visual_workbench import application as app,runtime as runtime
    runtime.configure(workspace)
    try:held=app.show('sample-visual',specimens['test'],'front')
    finally:runtime.close()
    held2=command('correct','--file',request('held-correction.json',correct('test',held['annotation']['annotation_sha256'],CORRECTION)))
    assert command('review','--file',request('held-training.json',review('test',held2['annotation']['annotation_sha256'],True)),expected=2)==dict(error='TRAINING_SELECTION_REFUSED')
    command('review','--file',request('held-review.json',review('test',held2['annotation']['annotation_sha256'],False)))
    evaluation=command('export','--dataset','sample-visual','--mode','evaluation');verify_report(workspace,evaluation,1,CORRECTION)
    final=command('export','--dataset','sample-visual','--mode','training');verify_report(workspace,final,1,LATER)
    assert {i['specimen_id'] for i in evaluation['manifest']['selected']}.isdisjoint(i['specimen_id'] for i in final['manifest']['selected'])
    historical=command('show',*view_args(),'--version','2');assert historical['annotation']['polygons']==CORRECTION and historical['review']['status']=='approved'
    history=command('history',*view_args())['versions'];assert len(history)==3 and history[1]['parent_sha256']==history[0]['annotation_sha256'] and history[2]['parent_sha256']==history[1]['annotation_sha256']
    metric=command('evaluate',*view_args());assert metric['per_class']['1']['iou']==1280/2480 and metric['per_class']['2']['iou']==1 and metric['comparison']=='operator_geometry_agreement_not_model_accuracy'
    backup=command('backup');body=(workspace/backup['file']).read_bytes();assert backup['sha256']==sha(body) and backup['bytes']==len(body) and not backup['image_files_included']
    with closing(sqlite3.connect((workspace/backup['file']).as_uri()+'?mode=ro',uri=True)) as db:assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
    before=tree(workspace);assert command('init',expected=2)['error'] and tree(workspace)==before
    reopened=command('show',*view_args());assert reopened['annotation']['annotation_sha256']==sha3 and reopened['review']['status']=='approved' and tree(workspace)==before
    assert tree(workspace/old['directory'])==old_bytes and all(tree(workspace/'inbox')[n]==v for n,v in inputs.items())
    return dict(status='PASS',command_checks=len(calls),practice_views=2,train_specimens=1,test_specimens=1,training_views=1,evaluation_views=1,unreviewed_training_views=0,training_versions=3,report_files_per_selected_view=5,first_class_foreground_pixels=2480,second_class_foreground_pixels=192,first_class_iou=1280/2480,independent_mask_pixels_checked=True,report_hashes_independently_verified=True,held_out_training_refused=True,missing_review_checks_refused=True,stale_review_refused=True,new_version_does_not_inherit_review=True,historical_correction_retained=True,old_report_unchanged=True,original_inputs_unchanged=True,specimen_splits_disjoint=True,backup_integrity_checked=True,saved_correction_reopened=True,existing_initialization_refused_without_writes=True,backup_includes_images=False,trained_model_executed=False,real_images_or_model_weights_included=False)
