"""Pointer, keyboard, zoom, conflict, review and narrow-screen Chromium acceptance."""
import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import sys
from playwright.sync_api import sync_playwright,expect

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from visual_workbench import application as app,contracts as c,png,runtime as r,web


class CanvasBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        try:cls.browser=cls.playwright.chromium.launch(headless=True)
        except BaseException:cls.playwright.stop();raise
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.playwright.stop()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close)
        self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.config=json.loads((APP/'examples/sample-dataset.json').read_text(encoding='utf-8'));app.create(r.encode(self.config))
        self.specimen=next('sample-'+str(i) for i in range(100) if c.partition(self.config,'sample-'+str(i))=='train')
        r.write_new(self.root/'inbox/fictional.png',png.fictional(512,256));self.polygons={'1':[[[8,8],[48,8],[48,40],[8,40]]],'2':[]}
        app.add_view(r.encode(dict(dataset_id='sample-visual',specimen_id=self.specimen,view_id='front',file='inbox/fictional.png',polygons=self.polygons)))
        self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
        self.context=self.browser.new_context(viewport={'width':1440,'height':1050});self.addCleanup(self.context.close)
        self.external=[];self.errors=[]
        def route(request):
            if request.request.url.startswith(f'http://127.0.0.1:{self.server.server_port}/'):request.continue_()
            else:self.external.append(request.request.url.split(':',1)[0]);request.abort()
        self.context.route('**/*',route);self.page=self.context.new_page();self.page.on('pageerror',lambda error:self.errors.append(str(error)));self.page.goto(f'http://127.0.0.1:{self.server.server_port}/');expect(self.page.locator('#status')).to_have_text('Saved view loaded.')
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def tearDown(self):
        self.assertEqual(self.external,[]);self.assertEqual(self.errors,[])
        destination=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if destination:
            target=Path(destination);target.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(target/(self._testMethodName+'.png')),full_page=True)
    def coords(self):return json.loads(self.page.locator('#polygons').input_value())
    def click_point(self,x,y):
        box=self.page.locator('#canvas').bounding_box();scale=float(self.page.locator('#zoom').input_value());self.page.mouse.click(box['x']+x*scale,box['y']+y*scale)
    def save(self):
        self.page.locator('#save').click();expect(self.page.locator('#status')).to_have_text('Immutable correction saved. Review is pending for a new version.')
    def test_pointer_draw_and_keyboard_finish_save(self):
        for point in ((60,20),(100,20),(100,50),(60,50)):self.click_point(*point)
        self.page.keyboard.press('Enter');self.assertEqual(self.coords()['1'][1],[[60,20],[100,20],[100,50],[60,50]]);self.save();self.assertEqual(app.show('sample-visual',self.specimen,'front')['annotation']['version'],2)
    def test_vertex_drag_undo_redo(self):
        self.page.locator('#mode').select_option('edit');box=self.page.locator('#canvas').bounding_box();self.page.mouse.move(box['x']+8,box['y']+8);self.page.mouse.down();self.page.mouse.move(box['x']+12,box['y']+10,steps=4);self.page.mouse.up();self.assertEqual(self.coords()['1'][0][0],[12,10]);self.page.keyboard.press('Control+z');self.assertEqual(self.coords()['1'][0][0],[8,8]);self.page.keyboard.press('Control+Shift+z');self.assertEqual(self.coords()['1'][0][0],[12,10]);self.save()
    def test_zoom_pan_pointer_coordinates(self):
        self.page.locator('#zoom').select_option('4');self.page.locator('#viewport').evaluate('(element)=>{element.scrollLeft=240;element.scrollTop=32;}');self.page.locator('#mode').select_option('pan');viewport=self.page.locator('#viewport').bounding_box();self.page.mouse.move(viewport['x']+150,viewport['y']+100);self.page.mouse.down();self.page.mouse.move(viewport['x']+100,viewport['y']+100,steps=4);self.page.mouse.up();self.assertGreaterEqual(self.page.locator('#viewport').evaluate('e=>e.scrollLeft'),280);self.page.locator('#mode').select_option('draw')
        for point in ((100,20),(120,20),(120,40)):self.click_point(*point)
        self.page.locator('#finish').click();self.assertEqual(self.coords()['1'][1],[[100,20],[120,20],[120,40]]);self.save()
    def test_keyboard_coordinate_editing(self):
        for x,y in ((70,50),(90,50),(80,70)):
            self.page.locator('#point-x').fill(str(x));self.page.locator('#point-y').fill(str(y));self.page.locator('#point-form button').click()
        self.page.locator('#finish').click();self.assertEqual(self.coords()['1'][1],[[70,50],[90,50],[80,70]]);self.page.locator('#delete').click();self.assertEqual(len(self.coords()['1']),1);self.page.locator('#undo').click();self.assertEqual(len(self.coords()['1']),2)
    def test_invalid_save_and_stale_save_retain_draft(self):
        bad={'1':[[[8,8],[48,40],[8,40],[48,8]]],'2':[]};self.page.locator('#polygons').fill(json.dumps(bad));self.page.locator('#save').click();expect(self.page.locator('#status')).to_contain_text('OPERATION_REFUSED; draft retained.');self.assertEqual(self.coords(),bad);self.assertEqual(app.show('sample-visual',self.specimen,'front')['annotation']['version'],1)
        self.page.locator('#reload').click();expect(self.page.locator('#status')).to_have_text('Saved view loaded.');old=app.show('sample-visual',self.specimen,'front');new=copy.deepcopy(self.polygons);new['2']=[[[80,80],[90,80],[80,90]]];app.correct(r.encode(dict(dataset_id='sample-visual',specimen_id=self.specimen,view_id='front',expected_sha256=old['annotation']['annotation_sha256'],polygons=new)))
        draft=copy.deepcopy(self.polygons);draft['1'][0][0]=[10,9];self.page.locator('#polygons').fill(json.dumps(draft));self.page.locator('#save').click();expect(self.page.locator('#status')).to_contain_text('OPERATION_REFUSED; draft retained.');self.assertEqual(self.coords(),draft);self.assertEqual(app.show('sample-visual',self.specimen,'front')['annotation']['polygons'],new)
    def test_review_export_metrics_and_backup(self):
        self.save();self.page.locator('#review-status').select_option('approved')
        for key in ('quality','privacy','rights','context','training'):self.page.locator('#'+key).check()
        self.page.locator('#review-form button').click();expect(self.page.locator('#status')).to_have_text('Review recorded for this saved version.');self.page.locator('#training-export').click();expect(self.page.locator('#status')).to_have_text('Private training export created.');self.assertEqual(json.loads(self.page.locator('#report').inner_text())['selected_views'],1);self.page.locator('#metrics').click();expect(self.page.locator('#metric-output')).to_contain_text('operator_geometry_agreement_not_model_accuracy');self.page.locator('#backup').click();expect(self.page.locator('#report')).to_contain_text('"image_files_included": false')
    def test_narrow_viewport_keyboard_workflow(self):
        self.page.set_viewport_size({'width':390,'height':844});self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)
        self.page.locator('#polygons').fill(json.dumps(self.polygons));self.save();expect(self.page.locator('#identity')).to_contain_text('version 2');self.assertEqual(self.page.locator('#canvas').evaluate('e=>e.width'),512)
    def test_unfinished_polygon_refused_and_escape(self):
        self.click_point(60,20);self.page.locator('#class').select_option('2');expect(self.page.locator('#status')).to_contain_text('Finish or cancel unfinished vertices before changing class.');self.assertEqual(self.page.locator('#class').input_value(),'1');self.page.locator('#save').click();expect(self.page.locator('#status')).to_contain_text('Finish or cancel unfinished vertices');self.page.locator('#canvas').focus();self.page.keyboard.press('Escape');self.save();self.assertEqual(len(self.coords()['1']),1)
    def test_create_dataset_and_import_view(self):
        self.page.locator('summary').click();config=copy.deepcopy(self.config);config['dataset_id']='sample-browser';self.page.locator('#dataset-json').fill(json.dumps(config));self.page.locator('#create').click();expect(self.page.locator('#status')).to_have_text('Immutable dataset configuration created.');expect(self.page.locator('#identity')).to_have_text('No view loaded');value=dict(dataset_id='sample-browser',specimen_id='sample-import',view_id='side',file='inbox/fictional.png',polygons=self.polygons);self.page.locator('#view-json').fill(json.dumps(value));self.page.locator('#add-view').click();expect(self.page.locator('#status')).to_have_text('Canonical PNG and initial proposal imported.');expect(self.page.locator('#identity')).to_contain_text('sample-import / side');self.assertEqual(app.show('sample-browser','sample-import','side')['annotation']['version'],1)


if __name__=='__main__':unittest.main()
