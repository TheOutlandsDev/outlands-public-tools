"""Immutable local datasets/images/annotations, reviews, evaluation and checked exports."""
import hashlib
import sqlite3
import uuid
from . import contracts as c,geometry,png,runtime


def _config(con,dataset_id):
    c.token(dataset_id);row=con.execute('SELECT config_sha256,config_json FROM datasets WHERE dataset_id=?',(dataset_id,)).fetchone()
    if row is None:raise runtime.WorkbenchError('DATASET_NOT_FOUND')
    value=c.dataset(row[1].encode())
    if value['dataset_id']!=dataset_id or runtime.digest(runtime.encode(value))!=row[0]:raise runtime.WorkbenchError('CONFIGURATION_HASH_MISMATCH')
    return value,row[0]


def create(raw):
    value=c.dataset(raw);encoded=runtime.encode(value);sha=runtime.digest(encoded)
    with runtime.connect() as con:
        row=con.execute('SELECT config_sha256 FROM datasets WHERE dataset_id=?',(value['dataset_id'],)).fetchone()
        if row:
            if row[0]!=sha:raise runtime.WorkbenchError('DATASET_IMMUTABLE')
            return dict(dataset_id=value['dataset_id'],config_sha256=sha,created=False)
        if con.execute('SELECT COUNT(*) FROM datasets').fetchone()[0]>=50:raise runtime.WorkbenchError('DATASET_LIMIT')
        con.execute('INSERT INTO datasets VALUES(?,?,?)',(value['dataset_id'],sha,encoded.decode()))
    return dict(dataset_id=value['dataset_id'],config_sha256=sha,created=True)


def datasets():
    with runtime.connect() as con:rows=con.execute('SELECT dataset_id,config_sha256 FROM datasets ORDER BY dataset_id LIMIT 51').fetchall()
    if len(rows)>50:raise runtime.WorkbenchError('DATASET_LIMIT')
    return dict(datasets=[dict(dataset_id=r[0],config_sha256=r[1]) for r in rows])


def configuration(dataset_id):
    with runtime.connect() as con:value,sha=_config(con,dataset_id)
    return dict(config=value,config_sha256=sha)


def _view(con,dataset_id,specimen_id,view_id):
    for item in (dataset_id,specimen_id,view_id):c.token(item)
    row=con.execute('SELECT width,height,image_sha256,original_sha256,partition_name FROM views WHERE dataset_id=? AND specimen_id=? AND view_id=?',(dataset_id,specimen_id,view_id)).fetchone()
    if row is None:raise runtime.WorkbenchError('VIEW_NOT_FOUND')
    config,_=_config(con,dataset_id)
    if c.partition(config,specimen_id)!=row[4]:raise runtime.WorkbenchError('SPLIT_MISMATCH')
    return dict(dataset_id=dataset_id,specimen_id=specimen_id,view_id=view_id,width=row[0],height=row[1],image_sha256=row[2],original_sha256=row[3],partition=row[4])


def _hash(config_sha,view,version,parent,origin,polygons):return runtime.digest(runtime.encode(dict(config_sha256=config_sha,view=view,version=version,parent_sha256=parent,origin=origin,polygons=polygons)))


def _annotation(con,view,version=None):
    query='SELECT version,annotation_sha256,parent_sha256,origin,polygons_json FROM annotations WHERE dataset_id=? AND specimen_id=? AND view_id=?';params=[view['dataset_id'],view['specimen_id'],view['view_id']]
    if version is not None:query+=' AND version=?';params.append(c.integer(version,1,200))
    row=con.execute(query+' ORDER BY version DESC LIMIT 1',params).fetchone()
    if row is None:raise runtime.WorkbenchError('ANNOTATION_NOT_FOUND')
    config,config_sha=_config(con,view['dataset_id']);polygons=runtime.decode(row[4].encode());geometry.validate(polygons,config['classes'],view['width'],view['height'])
    if _hash(config_sha,view,row[0],row[2],row[3],polygons)!=row[1]:raise runtime.WorkbenchError('ANNOTATION_HASH_MISMATCH')
    return dict(version=row[0],annotation_sha256=row[1],parent_sha256=row[2],origin=row[3],polygons=polygons)


def _review(con,annotation_sha):
    row=con.execute('SELECT payload_json FROM reviews WHERE annotation_sha256=? ORDER BY row_version DESC LIMIT 1',(annotation_sha,)).fetchone()
    return runtime.decode(row[0].encode()) if row else dict(status='pending',training_selected=False,row_version=0)


def add_view(raw):
    request=runtime.decode(raw);c.fields(request,('dataset_id','specimen_id','view_id','file','polygons'))
    for key in ('dataset_id','specimen_id','view_id'):c.token(request[key])
    original=runtime.read_bytes(runtime.local_path(request['file']));width,height,canonical=png.normalize(original);image_sha=runtime.digest(canonical);original_sha=runtime.digest(original)
    with runtime.connect() as con:
        config,config_sha=_config(con,request['dataset_id']);polygons=geometry.validate(request['polygons'],config['classes'],width,height)
        for specimen,view_id in con.execute('SELECT specimen_id,view_id FROM views WHERE dataset_id=?',(request['dataset_id'],)):
            if specimen.casefold()==request['specimen_id'].casefold():
                if specimen!=request['specimen_id'] or view_id.casefold()==request['view_id'].casefold() and view_id!=request['view_id']:raise runtime.WorkbenchError('CASE_IDENTITY_CONFLICT')
        existing=con.execute('SELECT image_sha256,original_sha256 FROM views WHERE dataset_id=? AND specimen_id=? AND view_id=?',(request['dataset_id'],request['specimen_id'],request['view_id'])).fetchone()
        if existing:
            view=_view(con,request['dataset_id'],request['specimen_id'],request['view_id']);first=_annotation(con,view,1)
            if existing!=(image_sha,original_sha) or first['polygons']!=polygons:raise runtime.WorkbenchError('VIEW_IDENTITY_CONFLICT')
            return dict(view=view,annotation=first,created=False)
        if con.execute('SELECT COUNT(*) FROM views WHERE dataset_id=?',(request['dataset_id'],)).fetchone()[0]>=64:raise runtime.WorkbenchError('VIEW_LIMIT')
        destination=runtime.local_path('images/'+image_sha+'.png',False)
        if destination.exists():
            if runtime.read_bytes(destination)!=canonical:raise runtime.WorkbenchError('IMAGE_HASH_MISMATCH')
        else:runtime.write_new(destination,canonical)
        split=c.partition(config,request['specimen_id'])
        con.execute('INSERT INTO views VALUES(?,?,?,?,?,?,?,?)',(request['dataset_id'],request['specimen_id'],request['view_id'],width,height,image_sha,original_sha,split))
        view=_view(con,request['dataset_id'],request['specimen_id'],request['view_id']);sha=_hash(config_sha,view,1,None,'proposal',polygons)
        con.execute('INSERT INTO annotations VALUES(?,?,?,?,?,?,?,?)',(request['dataset_id'],request['specimen_id'],request['view_id'],1,sha,None,'proposal',runtime.encode(polygons).decode()))
    return dict(view=view,annotation=dict(version=1,annotation_sha256=sha,parent_sha256=None,origin='proposal',polygons=polygons),created=True)


def views(dataset_id):
    with runtime.connect() as con:
        _config(con,dataset_id);keys=con.execute('SELECT specimen_id,view_id FROM views WHERE dataset_id=? ORDER BY specimen_id,view_id LIMIT 65',(dataset_id,)).fetchall()
        if len(keys)>64:raise runtime.WorkbenchError('VIEW_LIMIT')
        rows=[]
        for specimen,view_id in keys:
            view=_view(con,dataset_id,specimen,view_id);annotation=_annotation(con,view);rows.append(dict(**view,version=annotation['version'],annotation_sha256=annotation['annotation_sha256'],review=_review(con,annotation['annotation_sha256'])))
    return dict(dataset_id=dataset_id,views=rows)


def show(dataset_id,specimen_id,view_id,version=None):
    with runtime.connect() as con:
        config,config_sha=_config(con,dataset_id);view=_view(con,dataset_id,specimen_id,view_id);annotation=_annotation(con,view,version);review=_review(con,annotation['annotation_sha256'])
    return dict(config=config,config_sha256=config_sha,view=view,annotation=annotation,review=review)


def image(dataset_id,specimen_id,view_id):
    with runtime.connect() as con:view=_view(con,dataset_id,specimen_id,view_id)
    raw=runtime.read_bytes(runtime.local_path('images/'+view['image_sha256']+'.png'))
    if runtime.digest(raw)!=view['image_sha256']:raise runtime.WorkbenchError('IMAGE_HASH_MISMATCH')
    width,height,_=png.decode(raw)
    if (width,height)!=(view['width'],view['height']):raise runtime.WorkbenchError('IMAGE_DIMENSION_MISMATCH')
    return raw


def correct(raw):
    request=runtime.decode(raw);c.fields(request,('dataset_id','specimen_id','view_id','expected_sha256','polygons'));c.hash_value(request['expected_sha256'])
    with runtime.connect() as con:
        config,config_sha=_config(con,request['dataset_id']);view=_view(con,request['dataset_id'],request['specimen_id'],request['view_id']);previous=_annotation(con,view)
        if previous['annotation_sha256']!=request['expected_sha256']:raise runtime.WorkbenchError('ANNOTATION_CONFLICT')
        polygons=geometry.validate(request['polygons'],config['classes'],view['width'],view['height'])
        if previous['origin']=='manual_correction' and polygons==previous['polygons']:return dict(annotation=previous,created=False)
        version=previous['version']+1
        if version>200:raise runtime.WorkbenchError('ANNOTATION_VERSION_LIMIT')
        sha=_hash(config_sha,view,version,previous['annotation_sha256'],'manual_correction',polygons)
        con.execute('INSERT INTO annotations VALUES(?,?,?,?,?,?,?,?)',(view['dataset_id'],view['specimen_id'],view['view_id'],version,sha,previous['annotation_sha256'],'manual_correction',runtime.encode(polygons).decode()))
    return dict(annotation=dict(version=version,annotation_sha256=sha,parent_sha256=previous['annotation_sha256'],origin='manual_correction',polygons=polygons),created=True)


def review(raw):
    value=runtime.decode(raw);c.fields(value,('dataset_id','specimen_id','view_id','annotation_sha256','expected_version','status','training_selected','actor','note','checks'));c.hash_value(value['annotation_sha256']);c.integer(value['expected_version'],0,1000);c.text(value['actor'],80)
    if value['note']!='':c.text(value['note'],1000)
    if value['status'] not in ('pending','approved','rejected') or type(value['training_selected']) is not bool:raise runtime.WorkbenchError('REVIEW_INVALID')
    c.fields(value['checks'],('quality','privacy','rights','context'))
    if any(type(flag) is not bool for flag in value['checks'].values()):raise runtime.WorkbenchError('REVIEW_INVALID')
    with runtime.connect() as con:
        view=_view(con,value['dataset_id'],value['specimen_id'],value['view_id']);annotation=_annotation(con,view)
        if annotation['annotation_sha256']!=value['annotation_sha256']:raise runtime.WorkbenchError('ANNOTATION_CONFLICT')
        if value['status']=='approved' and (annotation['origin']!='manual_correction' or not all(value['checks'].values())):raise runtime.WorkbenchError('REVIEW_CHECKS_REQUIRED')
        if value['training_selected'] and (value['status']!='approved' or view['partition']!='train'):raise runtime.WorkbenchError('TRAINING_SELECTION_REFUSED')
        old=_review(con,annotation['annotation_sha256'])
        if old['row_version']!=value['expected_version']:raise runtime.WorkbenchError('REVIEW_VERSION_CONFLICT')
        if con.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]>=5000:raise runtime.WorkbenchError('REVIEW_LIMIT')
        result={k:v for k,v in value.items() if k!='expected_version'};result['row_version']=old['row_version']+1
        con.execute('INSERT INTO reviews VALUES(?,?,?)',(annotation['annotation_sha256'],result['row_version'],runtime.encode(result).decode()))
    return dict(review=result,operator_assertions_unverified=True)


def history(dataset_id,specimen_id,view_id):
    with runtime.connect() as con:
        view=_view(con,dataset_id,specimen_id,view_id);rows=con.execute('SELECT version,annotation_sha256,parent_sha256,origin FROM annotations WHERE dataset_id=? AND specimen_id=? AND view_id=? ORDER BY version LIMIT 201',(dataset_id,specimen_id,view_id)).fetchall()
    return dict(view=view,versions=[dict(version=r[0],annotation_sha256=r[1],parent_sha256=r[2],origin=r[3]) for r in rows])


def evaluate(dataset_id,specimen_id,view_id):
    with runtime.connect() as con:
        view=_view(con,dataset_id,specimen_id,view_id);config,_=_config(con,dataset_id);first=_annotation(con,view,1);latest=_annotation(con,view)
    metrics={}
    for row in config['classes']:
        key=str(row['id']);a=geometry.raster(first['polygons'][key],view['width'],view['height']);b=geometry.raster(latest['polygons'][key],view['width'],view['height']);metrics[key]=geometry.compare(a,b)
    return dict(proposal_sha256=first['annotation_sha256'],correction_sha256=latest['annotation_sha256'],per_class=metrics,comparison='operator_geometry_agreement_not_model_accuracy')


def export(dataset_id,mode):
    # Serialize selection with writers so a report represents one consistent state.
    with runtime.DATABASE_LOCK:return _export(dataset_id,mode)


def _export(dataset_id,mode):
    if mode not in ('training','evaluation'):raise runtime.WorkbenchError('EXPORT_MODE_INVALID')
    selected=[];data={};budget=0
    config=configuration(dataset_id);current=views(dataset_id)['views']
    for row in current:
        record=show(dataset_id,row['specimen_id'],row['view_id']);annotation=record['annotation'];review=record['review']
        allowed=row['partition']=='train' and review.get('training_selected') is True if mode=='training' else row['partition'] in ('validation','test')
        if not allowed or review['status']!='approved' or annotation['origin']!='manual_correction':continue
        prefix='items/'+row['specimen_id']+'/'+row['view_id'];raw=image(dataset_id,row['specimen_id'],row['view_id']);data[prefix+'/image.png']=raw
        for class_row in config['config']['classes']:
            key=str(class_row['id']);mask=geometry.raster(annotation['polygons'][key],row['width'],row['height']);data[prefix+'/class-'+key+'.png']=png.mask_png(row['width'],row['height'],mask)
        data[prefix+'/annotation.json']=runtime.encode(record)
        selected.append(dict(specimen_id=row['specimen_id'],view_id=row['view_id'],partition=row['partition'],image_sha256=row['image_sha256'],annotation_sha256=annotation['annotation_sha256'],version=annotation['version'],review_version=review['row_version'],prefix=prefix))
        budget=sum(len(raw) for raw in data.values())
        if budget>64*1024*1024:raise runtime.WorkbenchError('EXPORT_TOTAL_LIMIT')
    manifest=dict(format='outlands-visual-export-v1',mode=mode,dataset_id=dataset_id,config=config['config'],config_sha256=config['config_sha256'],implementation_version='0.1.0',mask_convention='independent_binary_RGBA_0_or_255_pixel_centers',selected=selected,files={name:dict(bytes=len(raw),sha256=runtime.digest(raw)) for name,raw in sorted(data.items())},training_or_inference_executed=False)
    directory=runtime.local_path('reports/'+uuid.uuid4().hex,False);runtime.mkdir(directory)
    for name,raw in sorted(data.items()):
        target=directory/name
        for parent in reversed(target.parents):
            if parent.is_relative_to(directory) and not parent.exists():runtime.mkdir(parent)
        runtime.write_new(target,raw)
    runtime.write_new(directory/'manifest.json',runtime.encode(manifest))
    return dict(directory=directory.relative_to(runtime.ROOT).as_posix(),manifest=manifest)


def backup():
    destination=runtime.local_path('backups/'+uuid.uuid4().hex+'.sqlite3',False);runtime.write_new(destination,b'')
    with runtime.connect() as source,runtime.io_errors(),runtime.guarded._store_scope(destination,initial=True):
        target=sqlite3.connect(destination.as_uri()+'?mode=rw',uri=True)
        try:source.backup(target);runtime.validate_schema(target)
        finally:target.close()
    raw=runtime.read_bytes(destination,64*1024*1024)
    return dict(file=destination.relative_to(runtime.ROOT).as_posix(),bytes=len(raw),sha256=runtime.digest(raw),image_files_included=False)


def demo():
    config=runtime.decode(runtime.read_bytes(runtime.SOURCE/'examples/sample-dataset.json'));create(runtime.encode(config));counts=dict(train=0,validation=0,test=0);specimens=[]
    for i in range(1000):
        specimen='sample-'+str(i);part=c.partition(config,specimen);needed=dict(train=3,validation=1,test=2)
        if counts[part]<needed[part]:counts[part]+=1;specimens.append((specimen,part))
        if counts==needed:break
    proposal={'1':[[[8,8],[48,8],[48,40],[8,40]]],'2':[[[20,18],[36,18],[36,30],[20,30]]]}
    correction={'1':[[[9,9],[49,9],[49,41],[9,41]]],'2':[[[22,19],[38,19],[38,32],[22,32]]]}
    for i,(specimen,part) in enumerate(specimens):
        path='inbox/'+specimen+'.png';runtime.write_new(runtime.local_path(path,False),png.fictional(seed=i))
        for view_id in ('front','side'):
            added=add_view(runtime.encode(dict(dataset_id=config['dataset_id'],specimen_id=specimen,view_id=view_id,file=path,polygons=proposal)))
            result=correct(runtime.encode(dict(dataset_id=config['dataset_id'],specimen_id=specimen,view_id=view_id,expected_sha256=added['annotation']['annotation_sha256'],polygons=correction)))
            review(runtime.encode(dict(dataset_id=config['dataset_id'],specimen_id=specimen,view_id=view_id,annotation_sha256=result['annotation']['annotation_sha256'],expected_version=0,status='approved',training_selected=part=='train',actor='sample_reviewer',note='Fictional geometry review',checks=dict(quality=True,privacy=True,rights=True,context=True))))
    train=export(config['dataset_id'],'training');held=export(config['dataset_id'],'evaluation');metric=evaluate(config['dataset_id'],specimens[0][0],'front');saved=backup()
    return dict(mode='FICTIONAL_VISUAL_ANNOTATION_DEMO',specimens=len(specimens),views=len(views(config['dataset_id'])['views']),partition_specimens=counts,training_views=len(train['manifest']['selected']),evaluation_views=len(held['manifest']['selected']),proposal_and_correction_versions=2,first_class_iou=metric['per_class']['1']['iou'],backup_validated=saved['bytes']>0,trained_model_executed=False,real_images_or_model_weights_included=False)
