"""Actual independent CLI and connected fictional HVAC geometry acceptance."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
TOOLS={'annotation-manifest-checker':'manifest.py','polygon-geometry-checker':'polygons.py',
       'bounding-box-converter':'boxes.py','annotation-export-handoff-checker':'handoff.py'}
def encode(v): return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode('ascii')
def sha(raw): return hashlib.sha256(raw).hexdigest()

class Walkthrough(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fictional-visual-contracts-'); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def invoke(self,script,args):
        q=subprocess.run([sys.executable,'-B',str(script),*map(str,args)],capture_output=True,
                         env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(q.stderr,b''); return q.returncode,json.loads(q.stdout)

    def cli(self,name,file=None,extra=(),folder=None):
        folder=folder or ROOT/'tools'/name
        return self.invoke(folder/TOOLS[name],['--input',file or folder/'examples/input.json',*extra])

    def run_value(self,name,value,code=0):
        file=self.root/(name+'.json'); file.write_bytes(encode(value)); actual,result=self.cli(name,file=file)
        self.assertEqual(actual,code); return result

    def test_valid_examples(self):
        for name in TOOLS:
            code,result=self.cli(name); self.assertEqual(code,0); self.assertEqual(result['status'],'PASS')

    def test_independent_source_copies(self):
        for name in TOOLS:
            folder=self.root/name; shutil.copytree(ROOT/'tools'/name,folder,ignore=shutil.ignore_patterns('__pycache__'))
            code,result=self.invoke(folder/'source_check.py',[]); self.assertEqual(code,0); self.assertEqual(result['status'],'SOURCE_MATCH')
            self.assertEqual(self.cli(name,folder=folder)[0],0)

    def test_new_reports_and_overwrite_prevention(self):
        for name in TOOLS:
            out=self.root/(name+'.json'); code,result=self.cli(name,extra=('--out',out))
            self.assertEqual(code,0); self.assertEqual(result,dict(status='PASS',report_written=True))
            raw=out.read_bytes(); self.assertEqual(json.loads(raw),self.cli(name)[1])
            self.assertEqual(self.cli(name,extra=('--out',out))[0],2); self.assertEqual(out.read_bytes(),raw)

    def test_source_tree_output_refusal(self):
        for name in TOOLS:
            out=ROOT/'tools'/name/'fictional-never-created.json'
            self.assertEqual(self.cli(name,extra=('--out',out))[0],2); self.assertFalse(out.exists())

    def test_fixed_argument_and_path_errors(self):
        for name in TOOLS:
            code,result=self.cli(name,extra=('--SYNTHETIC_SENTINEL',)); self.assertEqual(code,2)
            self.assertEqual(result,dict(status='ERROR',code='ARGUMENTS_INVALID'))
            code,result=self.cli(name,file=self.root/'SYNTHETIC_SENTINEL.json')
            self.assertEqual(code,2); self.assertNotIn('SYNTHETIC_SENTINEL',json.dumps(result))

    def test_review_examples_retain_complete_qualified_findings(self):
        for name in TOOLS:
            code,result=self.cli(name,file=ROOT/'tools'/name/'examples/needs-review.json')
            self.assertEqual(code,1);self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertTrue(result['issues']);self.assertIsNotNone(result['assessment'])

    def test_raw_input_pins_and_unchanged_inputs(self):
        for name in TOOLS:
            file=ROOT/'tools'/name/'examples/input.json'; raw=file.read_bytes(); _,result=self.cli(name)
            self.assertEqual(result['input_sha256'],sha(raw)); self.assertEqual(file.read_bytes(),raw)

    def test_connected_four_tool_hvac_geometry_and_handoff(self):
        def example(name):return json.loads((ROOT/'tools'/name/'examples/input.json').read_text(encoding='utf-8'))
        manifest_input=example('annotation-manifest-checker');manifest=self.run_value('annotation-manifest-checker',manifest_input)
        polygon_input=example('polygon-geometry-checker');polygon_input['images']=manifest_input['images'];polygon_input['polygons']=[]
        for a in manifest_input['annotations']:
            shape={k:a[k] for k in ('id','revision','image','image_revision','image_snapshot_sha256')}
            if a['kind']=='polygon':shape['vertices']=a['geometry']
            else:
                b=a['geometry'];shape['vertices']=[[b['left'],b['top']],[b['right'],b['top']],[b['right'],b['bottom']],[b['left'],b['bottom']]]
            polygon_input['polygons'].append(shape)
        polygons=self.run_value('polygon-geometry-checker',polygon_input)
        self.assertEqual(polygons['images_sha256'],manifest['images_sha256']);self.assertEqual(polygons['assessment']['valid_polygons'],2)
        self.assertEqual([r['area']['exact_fraction'] for r in polygons['assessment']['polygons']],['800/1','1600/1'])
        # Explicit fictional operator adapter: an envelope is not a replacement for polygon semantics.
        box_input=example('bounding-box-converter');box_input['images']=manifest_input['images'];box_input['boxes']=[]
        originals={r['id']:r for r in polygon_input['polygons']}
        for r in polygons['assessment']['polygons']:
            source=originals[r['id']];b=r['envelope'];row={k:source[k] for k in ('id','revision','image','image_revision','image_snapshot_sha256')}
            row.update(source=dict(format='pixel-xyxy',values=[b[k] for k in ('left','top','right','bottom')]),target='unit-cxcywh');box_input['boxes'].append(row)
        boxes=self.run_value('bounding-box-converter',box_input);self.assertEqual(boxes['images_sha256'],manifest['images_sha256'])
        self.assertEqual([r['converted_values'] for r in boxes['assessment']['boxes']],[['1/4','1/4','1/3','1/4'],['2/5','2/5','2/5','2/5']])
        expected={r['id']:r['source']['values'] for r in box_input['boxes']}
        for r in boxes['assessment']['boxes']:
            row=next(x for x in box_input['boxes'] if x['id']==r['id']);row.update(source=dict(format='unit-cxcywh',values=r['converted_values']),target='pixel-xyxy')
        roundtrip=self.run_value('bounding-box-converter',box_input)
        self.assertEqual({r['id']:r['converted_values'] for r in roundtrip['assessment']['boxes']},expected)
        handoff_input=example('annotation-export-handoff-checker');handoff_input.update(images=manifest_input['images'],annotations=manifest_input['annotations'],taxonomy=manifest_input['taxonomy'])
        for key in ('images_sha256','annotations_sha256','taxonomy_sha256'):handoff_input['handoff'][key]=manifest[key]
        handoff=self.run_value('annotation-export-handoff-checker',handoff_input)
        self.assertTrue(handoff['assessment']['eligible_for_manual_export_review']);self.assertEqual(handoff['selected_annotations_sha256'],manifest['annotations_sha256'])
        for result in (manifest,polygons,boxes,handoff):
            for key in ('artifact_bytes_verified','content_geometry_alignment_verified','approval_authenticity_verified','dataset_export_performed','execution_authorized','target_changes_performed'):self.assertFalse(result[key])

    def test_manifest_consistency_does_not_establish_polygon_validity(self):
        value=json.loads((ROOT/'tools/annotation-manifest-checker/examples/input.json').read_text(encoding='utf-8'))
        a=value['annotations'][0];a['geometry']=[[10,10],[50,30],[50,10],[10,30]]
        manifest=self.run_value('annotation-manifest-checker',value);self.assertFalse(manifest['geometry_verified'])
        shape={k:a[k] for k in ('id','revision','image','image_revision','image_snapshot_sha256')};shape['vertices']=a['geometry']
        polygons=self.run_value('polygon-geometry-checker',dict(format='outlands-polygon-geometry-v1',images=value['images'],polygons=[shape]),1)
        self.assertFalse(polygons['assessment']['eligible_for_manual_geometry_review']);self.assertIn('EDGE_CONTACT',polygons['assessment']['polygons'][0]['failed_criteria'])

    def test_no_execution_mutation_or_action_artifacts(self):
        for name in TOOLS:
            before=set(self.root.iterdir()); _,result=self.cli(name)
            self.assertEqual(set(self.root.iterdir()),before); self.assertFalse(result['execution_authorized']); self.assertFalse(result['target_changes_performed'])

    def test_fictional_game_box_cli(self):
        name='bounding-box-converter';code,r=self.cli(name,file=ROOT/'tools'/name/'examples/game-boxes.json')
        self.assertEqual(code,0);self.assertEqual(r['assessment']['boxes'][0]['converted_values'],['1/4','1/4','1/2','1/2']);self.assertFalse(r['coordinates_rounded'])
