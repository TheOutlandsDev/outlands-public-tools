"""Fictional pixels and independent geometry, application, HTTP and native I/O tests."""
from contextlib import closing
import copy
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zlib

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from visual_workbench import application as app,contracts as c,geometry as g,png,runtime as r,web


def sample():return json.loads((APP/'examples/sample-dataset.json').read_text(encoding='utf-8'))
def polygons():return {'1':[[[8,8],[48,8],[48,40],[8,40]]],'2':[[[20,18],[36,18],[36,30],[20,30]]]}
def encoded(value):return r.encode(value)
def png_raw(width,height,mode,rows,depth=8,interlace=0):return png.SIGNATURE+png.chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,depth,mode,0,0,interlace))+png.chunk(b'IDAT',zlib.compress(rows))+png.chunk(b'IEND',b'')


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close)
        self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize()
    def load(self,specimen='sample-item',view='front'):
        app.create(encoded(sample()));path=self.root/'inbox/sample-image.png'
        if not path.exists():r.write_new(path,png.fictional())
        return app.add_view(encoded(dict(dataset_id='sample-visual',specimen_id=specimen,view_id=view,file='inbox/sample-image.png',polygons=polygons())))
    def correction(self,specimen='sample-item',view='front'):
        self.load(specimen,view);old=app.show('sample-visual',specimen,view);value=copy.deepcopy(polygons());value['1'][0][0]=[9,8]
        return app.correct(encoded(dict(dataset_id='sample-visual',specimen_id=specimen,view_id=view,expected_sha256=old['annotation']['annotation_sha256'],polygons=value)))
    def approve(self,specimen='sample-item',view='front',**changes):
        record=app.show('sample-visual',specimen,view);value=dict(dataset_id='sample-visual',specimen_id=specimen,view_id=view,annotation_sha256=record['annotation']['annotation_sha256'],expected_version=record['review']['row_version'],status='approved',training_selected=record['view']['partition']=='train',actor='sample_reviewer',note='Fictional review',checks=dict(quality=True,privacy=True,rights=True,context=True));value.update(changes)
        return app.review(encoded(value))


class Geometry(unittest.TestCase):
    def test_rectangle_exact_pixels(self):
        mask=g.raster([[[1,1],[4,1],[4,3],[1,3]]],5,4);self.assertEqual(list(mask),[0]*5+[0,255,255,255,0]*2+[0]*5)
    def test_independent_point_in_polygon_oracle(self):
        # Float ray crossings are independent of the exact-Fraction scanline implementation.
        shapes=[[[0,0],[8,0],[8,7],[0,7]],[[1,1],[8,1],[8,3],[4,3],[4,7],[1,7]],[[0,0],[8,2],[6,7],[1,6]],[[0,0],[7,0],[0,7]]]
        rng=random.Random(31)
        for _ in range(30):
            x,y=rng.randint(0,4),rng.randint(0,3);w,h=rng.randint(1,4),rng.randint(1,4);shapes.append([[x,y],[x+w,y],[x+w,y+h],[x,y+h]])
        for shape in shapes:
            expected=[]
            for y in range(8):
                for x in range(9):
                    inside=False;px,py=x+.5,y+.5
                    for i,a in enumerate(shape):
                        b=shape[(i+1)%len(shape)]
                        if (a[1]>py)!=(b[1]>py) and px<(b[0]-a[0])*(py-a[1])/(b[1]-a[1])+a[0]:inside=not inside
                    expected.append(255 if inside else 0)
            self.assertEqual(g.raster([shape],9,8),bytes(expected));self.assertEqual(g.raster([list(reversed(shape))],9,8),bytes(expected))
    def test_same_class_union(self):
        self.assertEqual(sum(bool(x) for x in g.raster([[[0,0],[3,0],[3,3],[0,3]],[[1,1],[4,1],[4,4],[1,4]]],4,4)),14)
    def test_empty_mask_metrics(self):self.assertIsNone(g.compare(b'\0'*4,b'\0'*4)['iou']);self.assertIsNone(g.compare(b'\0',b'\0')['dice'])
    def test_known_iou_dice(self):
        result=g.compare(bytes([255,255,0,0]),bytes([0,255,255,0]));self.assertEqual(result['iou'],1/3);self.assertEqual(result['dice'],.5);self.assertFalse(result['trained_model_evaluated'])
    def test_mask_length_mismatch(self):
        with self.assertRaises(r.WorkbenchError):g.compare(b'\0',b'')
    def test_polygon_rejections(self):
        bad=[[[0,0],[2,2],[0,2],[2,0]],[[0,0],[1,1],[2,2]],[[0,0],[2,0],[2,2],[0,0]],[[0,0],[64.0,0],[0,2]],[[0,0],[True,0],[0,2]],[[0,0],[65,0],[0,2]],[[-1,0],[2,0],[0,2]],[[0,0],[2,0]],[[0,0],[4,0],[2,0],[2,3],[0,3]]]
        for points in bad:
            with self.subTest(points=points),self.assertRaises(r.WorkbenchError):g.validate({'1':[points],'2':[]},sample()['classes'],64,48)
    def test_empty_class_masks_allowed(self):self.assertEqual(g.validate({'1':[],'2':[]},sample()['classes'],64,48),{'1':[],'2':[]})
    def test_extra_or_missing_class_refused(self):
        for value in ({'1':[]},{'1':[],'2':[],'3':[]}):
            with self.assertRaises(r.WorkbenchError):g.validate(value,sample()['classes'],64,48)
    def test_polygon_count_limit(self):
        value=polygons();value['1']*=5
        with self.assertRaises(r.WorkbenchError):g.validate(value,sample()['classes'],64,48)
    def test_vertex_limit(self):
        with self.assertRaises(r.WorkbenchError):g.validate({'1':[[[x,0] for x in range(65)]],'2':[]},sample()['classes'],64,48)


class Images(unittest.TestCase):
    def test_rgba_roundtrip(self):
        w,h,pixels=png.decode(png.fictional());self.assertEqual((w,h),(64,48));self.assertEqual(png.decode(png.encode(w,h,pixels))[2],pixels)
    def test_gray_rgb_conversion(self):
        for mode,row,expected in ((0,b'\x11\x22',b'\x11\x11\x11\xff\x22\x22\x22\xff'),(2,b'\x11\x22\x33\x44\x55\x66',b'\x11\x22\x33\xff\x44\x55\x66\xff')):
            self.assertEqual(png.decode(png_raw(2,1,mode,b'\0'+row))[2],expected)
    def test_all_five_filters_independent_encoder(self):
        for channels,mode in ((1,0),(3,2),(4,6)):
            for filt in range(5):
                width,height=5,3;source=bytes((i*31+17)%256 for i in range(width*height*channels));rows=bytearray();stride=width*channels
                for y in range(height):
                    rows.append(filt)
                    for x in range(stride):
                        i=y*stride+x;a=source[i-channels] if x>=channels else 0;b=source[i-stride] if y else 0;c0=source[i-stride-channels] if y and x>=channels else 0
                        if filt==4:
                            p=a+b-c0;dist=[abs(p-a),abs(p-b),abs(p-c0)];predictor=(a,b,c0)[dist.index(min(dist))]
                        else:predictor=(0,a,b,(a+b)//2)[filt]
                        rows.append((source[i]-predictor)%256)
                rgba=png.decode(png_raw(width,height,mode,bytes(rows)))[2]
                expected=b''.join(bytes([source[i]])*3+b'\xff' if channels==1 else source[i:i+channels]+(b'\xff' if channels==3 else b'') for i in range(0,len(source),channels));self.assertEqual(rgba,expected)
    def test_metadata_removed_pixels_preserved(self):
        raw=png.fictional();tagged=raw[:33]+png.chunk(b'tEXt',b'Sample\0Fictional metadata')+raw[33:];w,h,normal=png.normalize(tagged);self.assertEqual(normal,raw);self.assertNotIn(b'Fictional metadata',normal);self.assertEqual(png.decode(normal)[2],png.decode(tagged)[2])
    def test_crc_truncation_and_trailing_refused(self):
        raw=png.fictional()
        for value in (raw[:-1],raw+b'x',raw[:40]+bytes([raw[40]^1])+raw[41:],b'not png'):
            with self.assertRaises(r.WorkbenchError):png.decode(value)
    def test_unsupported_depth_palette_interlace(self):
        for depth,mode,interlace in ((16,6,0),(8,3,0),(8,6,1)):
            with self.assertRaises(r.WorkbenchError):png.decode(png_raw(1,1,mode,b'\0\0\0\0\xff',depth,interlace))
    def test_animation_transparency_critical_chunks_refused(self):
        raw=png.fictional()
        for kind in (b'acTL',b'fcTL',b'fdAT',b'tRNS',b'ABCD'):
            with self.assertRaises(r.WorkbenchError):png.decode(raw[:33]+png.chunk(kind,b'')+raw[33:])
    def test_decompression_bomb_refused(self):
        with self.assertRaises(r.WorkbenchError):png.decode(png_raw(1,1,6,b'\0'*1000000))
    def test_extra_zlib_stream_refused(self):
        raw=png.SIGNATURE+png.chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+png.chunk(b'IDAT',zlib.compress(b'\0'*5)+zlib.compress(b'x'))+png.chunk(b'IEND',b'')
        with self.assertRaises(r.WorkbenchError):png.decode(raw)
    def test_bad_filter_dimensions_and_chunk_count(self):
        for raw in (png_raw(1,1,6,b'\5\0\0\0\xff'),png_raw(1024,1024,6,b''),png.fictional()[:33]+png.chunk(b'tEXt',b'')*129+png.fictional()[33:]):
            with self.assertRaises(r.WorkbenchError):png.decode(raw)
    def test_masks_are_binary_opaque_rgba(self):self.assertEqual(png.decode(png.mask_png(2,1,b'\0\xff'))[2],b'\0\0\0\xff\xff\xff\xff\xff')


class Contracts(unittest.TestCase):
    def test_split_is_specimen_stable(self):
        config=sample();self.assertEqual(c.partition(config,'sample-item'),c.partition(copy.deepcopy(config),'sample-item'));self.assertIn(c.partition(config,'sample-item'),('train','validation','test'))
    def test_split_hash_oracle(self):
        config=sample()
        for i in range(100):
            specimen='sample-'+str(i);n=int(hashlib.sha256(('sample-seed\0'+specimen).encode()).hexdigest()[:8],16)%1000;expected='train' if n<600 else 'validation' if n<800 else 'test';self.assertEqual(c.partition(config,specimen),expected)
    def test_invalid_dataset_contracts(self):
        cases=[]
        for key,value in (('format','wrong'),('dataset_id','../sample'),('classes',[]),('title','x\nvalue')):
            config=sample();config[key]=value;cases.append(config)
        config=sample();config['split']['train_per_mille']=601;cases.append(config)
        config=sample();config['classes'][1]['id']=1;cases.append(config)
        config=sample();config['classes'][1]['label']='REGION';cases.append(config)
        config=sample();config['extra']='invented';cases.append(config)
        for config in cases:
            with self.assertRaises(r.WorkbenchError):c.dataset(encoded(config))
    def test_duplicate_json_keys_and_nonfinite(self):
        for raw in (b'{"x":1,"x":2}',b'NaN',b'Infinity',b'1e999'):
            with self.assertRaises(r.WorkbenchError):r.decode(raw)
    def test_size_depth_and_utf8_limits(self):
        for raw in (b'x'*(r.MAX_INPUT+1),b'['*66+b'0'+b']'*66,b'\xff'):
            with self.assertRaises(r.WorkbenchError):r.decode(raw)


class Application(Fixture):
    def test_full_demo(self):
        value=app.demo();self.assertEqual(value['views'],12);self.assertEqual(value['partition_specimens'],dict(train=3,validation=1,test=2));self.assertEqual(value['training_views'],6);self.assertEqual(value['evaluation_views'],6);self.assertAlmostEqual(value['first_class_iou'],1209/1351);self.assertTrue(value['backup_validated']);self.assertFalse(value['trained_model_executed'])
    def test_demo_no_network(self):
        with patch('socket.socket',side_effect=AssertionError('Unexpected network request')):self.assertFalse(app.demo()['real_images_or_model_weights_included'])
    def test_dataset_immutable_idempotent(self):
        self.assertTrue(app.create(encoded(sample()))['created']);self.assertFalse(app.create(encoded(sample()))['created']);value=sample();value['title']='Other fictional title'
        with self.assertRaisesRegex(r.WorkbenchError,'DATASET_IMMUTABLE'):app.create(encoded(value))
    def test_view_idempotent_and_identity_conflict(self):
        self.assertTrue(self.load()['created']);self.assertFalse(self.load()['created']);value=dict(dataset_id='sample-visual',specimen_id='sample-item',view_id='front',file='inbox/sample-image.png',polygons={'1':[],'2':[]})
        with self.assertRaisesRegex(r.WorkbenchError,'VIEW_IDENTITY_CONFLICT'):app.add_view(encoded(value))
    def test_same_specimen_views_share_split(self):
        self.assertEqual(self.load(view='front')['view']['partition'],self.load(view='side')['view']['partition'])
    def test_lineage_and_historical_reads(self):
        first=self.load();second=self.correction();record=app.show('sample-visual','sample-item','front',1);self.assertEqual(record['annotation'],{k:v for k,v in first['annotation'].items()});self.assertEqual(second['annotation']['parent_sha256'],first['annotation']['annotation_sha256']);self.assertEqual(len(app.history('sample-visual','sample-item','front')['versions']),2)
    def test_correction_idempotent_latest(self):
        self.correction();record=app.show('sample-visual','sample-item','front');self.assertFalse(app.correct(encoded(dict(dataset_id='sample-visual',specimen_id='sample-item',view_id='front',expected_sha256=record['annotation']['annotation_sha256'],polygons=record['annotation']['polygons'])))['created'])
    def test_stale_correction_refused_no_partial_write(self):
        first=self.load();self.correction()
        with self.assertRaisesRegex(r.WorkbenchError,'ANNOTATION_CONFLICT'):app.correct(encoded(dict(dataset_id='sample-visual',specimen_id='sample-item',view_id='front',expected_sha256=first['annotation']['annotation_sha256'],polygons=polygons())))
        self.assertEqual(len(app.history('sample-visual','sample-item','front')['versions']),2)
    def test_proposal_cannot_be_approved(self):
        self.load()
        with self.assertRaisesRegex(r.WorkbenchError,'REVIEW_CHECKS_REQUIRED'):self.approve()
    def test_review_all_checks_required_strict_boolean(self):
        self.correction()
        for checks in (dict(quality=True,privacy=False,rights=True,context=True),dict(quality=1,privacy=True,rights=True,context=True)):
            with self.assertRaises(r.WorkbenchError):self.approve(checks=checks)
    def test_review_stale_version_refused(self):
        self.correction();self.approve()
        with self.assertRaisesRegex(r.WorkbenchError,'REVIEW_VERSION_CONFLICT'):self.approve(expected_version=0)
    def test_empty_review_note_allowed(self):
        self.correction();self.assertEqual(self.approve(note='')['review']['note'],'')
    def test_correction_resets_review(self):
        self.correction();self.approve();record=app.show('sample-visual','sample-item','front');value=copy.deepcopy(polygons());value['1'][0][0]=[10,9];app.correct(encoded(dict(dataset_id='sample-visual',specimen_id='sample-item',view_id='front',expected_sha256=record['annotation']['annotation_sha256'],polygons=value)));self.assertEqual(app.show('sample-visual','sample-item','front')['review'],dict(status='pending',training_selected=False,row_version=0));self.assertEqual(app.show('sample-visual','sample-item','front',2)['review']['status'],'approved')
    def test_holdout_training_selection_refused(self):
        specimen=next('item-'+str(i) for i in range(100) if c.partition(sample(),'item-'+str(i))!='train');self.correction(specimen)
        with self.assertRaisesRegex(r.WorkbenchError,'TRAINING_SELECTION_REFUSED'):self.approve(specimen,training_selected=True)
    def test_rejected_training_selection_refused(self):
        self.correction()
        with self.assertRaises(r.WorkbenchError):self.approve(status='rejected',training_selected=True)
    def test_export_latest_review_and_hashes(self):
        app.demo()
        for mode in ('training','evaluation'):
            result=app.export('sample-visual',mode);manifest=result['manifest'];directory=self.root/result['directory'];self.assertEqual(len(manifest['selected']),6);self.assertFalse(manifest['training_or_inference_executed'])
            self.assertEqual({p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()},set(manifest['files'])|{'manifest.json'})
            for name,item in manifest['files'].items():
                raw=(directory/name).read_bytes();self.assertEqual(item,dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
            for row in manifest['selected']:
                self.assertEqual(row['version'],2);self.assertEqual(row['partition']=='train',mode=='training');record=app.show('sample-visual',row['specimen_id'],row['view_id']);self.assertEqual(row['annotation_sha256'],record['annotation']['annotation_sha256']);prefix=directory/row['prefix']
                w,h,pixels=png.decode((prefix/'class-1.png').read_bytes());expected=bytes(255 if 9<=x<49 and 9<=y<41 else 0 for y in range(h) for x in range(w));self.assertEqual(pixels[::4],expected)
                # Both class masks retain positive values in their overlap.
                self.assertEqual(pixels[(20*w+24)*4],255);self.assertEqual(png.decode((prefix/'class-2.png').read_bytes())[2][(20*w+24)*4],255)
    def test_pending_latest_not_exported(self):
        app.demo();row=app.views('sample-visual')['views'][0];record=app.show('sample-visual',row['specimen_id'],row['view_id']);value=record['annotation']['polygons'];value['2']=[];app.correct(encoded(dict(dataset_id='sample-visual',specimen_id=row['specimen_id'],view_id=row['view_id'],expected_sha256=record['annotation']['annotation_sha256'],polygons=value)))
        selections=app.export('sample-visual','training')['manifest']['selected']+app.export('sample-visual','evaluation')['manifest']['selected'];self.assertEqual(len(selections),11);self.assertNotIn((row['specimen_id'],row['view_id']),[(x['specimen_id'],x['view_id']) for x in selections])
    def test_image_hash_tampering_refused(self):
        row=self.load()['view'];(self.root/'images'/(row['image_sha256']+'.png')).write_bytes(png.fictional(seed=1))
        with self.assertRaisesRegex(r.WorkbenchError,'IMAGE_HASH_MISMATCH'):app.image('sample-visual','sample-item','front')
    def test_store_budget_rolls_back(self):
        with patch.object(r,'MAX_STORE',1),self.assertRaisesRegex(r.WorkbenchError,'STORE_LIMIT'):app.create(encoded(sample()))
        self.assertEqual(app.datasets(),dict(datasets=[]))
    def test_append_only_database(self):
        self.correction();self.approve()
        for table in ('datasets','views','annotations','reviews'):
            with self.assertRaises(sqlite3.IntegrityError),r.connect() as con:con.execute('DELETE FROM '+table)
    def test_backup_database_only(self):
        self.load();value=app.backup();self.assertFalse(value['image_files_included']);self.assertEqual(value['sha256'],r.digest((self.root/value['file']).read_bytes()))
        with closing(sqlite3.connect(self.root/value['file'])) as con:r.validate_schema(con);self.assertEqual(con.execute('SELECT COUNT(*) FROM views').fetchone()[0],1)
    def test_schema_and_version_tampering_refused(self):
        path=self.root/'database/visual.sqlite3'
        with closing(sqlite3.connect(path)) as con:con.execute('PRAGMA user_version=2');con.commit()
        with self.assertRaisesRegex(r.WorkbenchError,'STORE_VERSION_REFUSED'):app.datasets()
        with closing(sqlite3.connect(path)) as con:con.execute('PRAGMA user_version=0');con.execute('CREATE TABLE unknown(x)');con.commit()
        with self.assertRaisesRegex(r.WorkbenchError,'STORE_SCHEMA_REFUSED'):app.datasets()


class Filesystem(Fixture):
    def test_source_cannot_be_instance(self):
        r.close()
        with self.assertRaises(r.WorkbenchError):r.configure(APP,create=True)
    def test_parent_escape_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('../outside',False)
    def test_existing_output_never_replaced(self):
        path=self.root/'inbox/existing.json';r.write_new(path,b'original')
        with self.assertRaises(r.WorkbenchError):r.write_new(path,b'replacement')
        self.assertEqual(path.read_bytes(),b'original')
    def make_link(self,action):
        try:action()
        except OSError:
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('Native link fixture required')
            self.skipTest('Native link fixture unavailable on this filesystem')
    def test_native_hardlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.link(self.root/'inbox/sample-dataset.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/visual.sqlite3',self.root/'database/alias.sqlite3'))
        with self.assertRaises(r.WorkbenchError):app.datasets()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.symlink(self.root/'inbox/sample-dataset.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'sample-dataset.json')
    @unittest.skipIf(os.name=='nt','POSIX-only FIFO')
    def test_posix_fifo_refused_without_blocking(self):
        target=self.root/'inbox/sample-fifo';os.mkfifo(target)
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    @unittest.skipUnless(os.name=='nt','Windows-only stream names')
    def test_windows_stream_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('inbox/sample-dataset.json:stream')
    def test_stale_lock_requires_assertion(self):
        r.close();(self.root/'.session-lock').mkdir()
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(app.datasets(),dict(datasets=[]))
    def test_nonempty_stale_lock_refused(self):
        r.close();(self.root/'.session-lock').mkdir();(self.root/'.session-lock/owned').write_bytes(b'fictional')
        with self.assertRaises(r.WorkbenchError):r.configure(self.root,confirm_stopped=True)
    def test_actual_child_termination_and_restart(self):
        self.correction();r.close();process=subprocess.Popen([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:self.assertEqual(json.loads(process.stdout.readline())['mode'],'LOOPBACK_VISUAL_UI');process.kill();process.communicate(timeout=10)
        finally:
            if process.poll() is None:process.kill();process.communicate(timeout=10)
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(app.show('sample-visual','sample-item','front')['annotation']['version'],2)


class BrowserApi(Fixture):
    def setUp(self):
        super().setUp();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def request(self,path='/',method='GET',value=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            connection.request(method,path,body=encoded(value) if value is not None else None,headers=headers or {});response=connection.getresponse();return response.status,response.read(),dict(response.getheaders())
        finally:connection.close()
    def test_html_and_no_cache(self):
        status,raw,headers=self.request();self.assertEqual(status,200);self.assertIn(web.TOKEN.encode(),raw);self.assertNotIn(b'__SESSION_TOKEN__',raw);self.assertEqual(headers['Cache-Control'],'no-store');self.assertIn("img-src 'self' blob:",headers['Content-Security-Policy'])
    def test_image_and_api_read_token_required(self):
        for path in ('/api/datasets','/api/image'):self.assertEqual(self.request(path)[0],403)
    def test_host_header_refused(self):self.assertEqual(self.request(headers={'Host':'example.invalid'})[0],403)
    def test_cross_origin_write_refused(self):self.assertEqual(self.request('/api/backup','POST',{},dict(Origin='https://example.invalid',**{'X-Outlands-Token':web.TOKEN}))[0],403)
    def test_write_token_required(self):self.assertEqual(self.request('/api/backup','POST',{})[0],403)
    def test_image_exact_canonical_bytes(self):
        self.load();status,raw,headers=self.request('/api/image?dataset=sample-visual&specimen=sample-item&view=front',headers={'X-Outlands-Token':web.TOKEN});self.assertEqual(status,200);self.assertEqual(raw,png.fictional());self.assertEqual(headers['Content-Type'],'image/png')
    def test_fixed_error_no_private_path(self):
        status,raw,_=self.request('/api/view?dataset=missing',headers={'X-Outlands-Token':web.TOKEN});self.assertEqual(status,400);self.assertEqual(json.loads(raw),dict(error='OPERATION_REFUSED'))
    def test_unknown_fields_and_duplicate_query_refused(self):
        headers={'X-Outlands-Token':web.TOKEN};self.assertEqual(self.request('/api/backup','POST',{'extra':'fictional'},headers)[0],400);self.assertEqual(self.request('/api/views?dataset=a&dataset=b',headers=headers)[0],400)
    def test_real_correction_through_http(self):
        first=self.load();value=dict(dataset_id='sample-visual',specimen_id='sample-item',view_id='front',expected_sha256=first['annotation']['annotation_sha256'],polygons=polygons());status,raw,_=self.request('/api/correct','POST',value,{'X-Outlands-Token':web.TOKEN});self.assertEqual(status,200);self.assertEqual(json.loads(raw)['annotation']['version'],2)


if __name__=='__main__':unittest.main()
