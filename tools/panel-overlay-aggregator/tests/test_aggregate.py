import ast,csv,hashlib,io,json,math,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import guarded_aggregate as g
import synthetic
from PIL import Image

class AggregatorTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.core,cls.engine=g.modules()
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='panel-overlay-test-');self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
  self.root=self.base/'inputs';synthetic.generate(self.root);self.out=self.base/'result.csv';self.manifest=self.root/'sites_manifest.csv'
  self.addCleanup(self.engine.plt.close,'all')
 def rows(self):
  with self.manifest.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
 def save(self,rows,fields=synthetic.FIELDS):
  with self.manifest.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 def run_case(self,**kwargs):
  with patch.object(g,'modules',return_value=(self.core,self.engine)):return g.aggregate(kwargs.get('root',self.root),kwargs.get('manifests',[self.manifest]),kwargs.get('out',self.out))
 def csv_rows(self):
  with self.out.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
 def refused(self,code):
  with self.assertRaisesRegex(ValueError,code):self.run_case()
  self.assertFalse(self.out.exists())

 def test_original_implementation_and_published_engine_pins(self):
  b=json.loads((ROOT/'BASELINE.json').read_bytes());self.assertEqual(b['original_implementation_files'],1)
  for name,pin in b['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),pin)
  self.assertTrue(b['verification_assertions_and_code_structure_preserved'])

 def test_retained_verification_assertions_and_outputs(self):
  p=ROOT/'original/verify_panel_overlay_axisfix.py'
  self.assertEqual(sum(isinstance(n,ast.Assert) for n in ast.walk(ast.parse(p.read_bytes()))),9)
  r=subprocess.run([sys.executable,'-B',str(p)],capture_output=True,text=True,timeout=60)
  self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stderr,'')
  self.assertEqual(r.stdout.splitlines(),['syntax_ok=True','overlay_axis_keys_ok=True','axis_specific_row_mapping_ok=True'])

 def test_synthetic_end_to_end_signed_axes_medians_and_differences(self):
  expected=json.loads((self.root/'EXPECTED.json').read_bytes());report=self.run_case();row=self.csv_rows()[0]
  for key in ('LL_L2_VX','LL_L2_VY','CDO_LL_L2_VX','CDO_LL_L2_VY','DIFF_LL_L2_VX','DIFF_LL_L2_VY'):self.assertAlmostEqual(float(row[key]),expected[key],delta=expected['absolute_tolerance_um'])
  self.assertEqual((report['panels'],report['measurements']),(1,3));self.assertEqual(row['Panel ID'],expected['panel'])
  self.assertFalse(report['quality_approved']);self.assertFalse(report['calibration_verified']);self.assertFalse(report['rev3b_sampling_qc_applied'])
  self.assertEqual(report['csv_sha256'],hashlib.sha256(self.out.read_bytes()).hexdigest())

 def test_fixed_sampling_parity_and_no_expanded_qc_gate(self):
  val,sig=self.core.compute_alignment(self.engine,self.root/'vx4.png','VX',False)
  rows=self.rows()[:1];self.save(rows)
  with patch.object(self.engine,'rev3b_build_sampling_groups',side_effect=AssertionError('Unexpected QC gate')) as gate:self.run_case();gate.assert_not_called()
  row=self.csv_rows()[0];self.assertAlmostEqual(float(row['LL_L2_VX']),val,places=6);self.assertAlmostEqual(float(row['SIG_LL_L2_VX']),sig,places=6)

 def test_original_cli_with_explicit_fictional_toml(self):
  legacy=self.base/'legacy-input';legacy.mkdir();rows=self.rows()
  for row in rows:
   for field in ('crop_path','cdo_xml_path'):row[field]=str((self.root/row[field]).resolve())
  with (legacy/'sites_manifest.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=synthetic.FIELDS);w.writeheader();w.writerows(rows)
  config=self.base/'invented.toml';legacy_out=self.base/'legacy.csv'
  config.write_text('[paths]\n'+''.join(k+' = '+json.dumps(v.as_posix())+'\n' for k,v in [('out_root',legacy),('analyzer',ROOT/'engine/Vern_Analyze_v2.py'),('panel_csv',legacy_out)]),encoding='utf-8')
  env=dict(os.environ,MPLBACKEND='Agg',PYTHONUTF8='1');r=subprocess.run([sys.executable,'-B',str(ROOT/'original/panel_overlay_aggregate_v2_axisfix.py'),'--config',str(config)],cwd=self.base,env=env,capture_output=True,text=True,timeout=90)
  self.assertEqual(r.returncode,0,r.stderr);self.assertIn('Wrote 1 panels',r.stdout)
  self.run_case();self.assertEqual(legacy_out.read_bytes(),self.out.read_bytes())

 def test_optional_reference_cells_remain_blank(self):
  rows=self.rows()
  for r in rows:r['cdo_xml_path']=''
  self.save(rows);self.run_case();row=self.csv_rows()[0]
  self.assertEqual(row['CDO_LL_L2_VX'],'');self.assertEqual(row['DIFF_LL_L2_VY'],'')

 def test_legacy_corner_reference_fallback_is_explicit(self):
  (self.root/'reference.xml').write_text('<Body><Measurement ID="LL_L2" type="OL"><Result>0.5</Result></Measurement></Body>')
  report=self.run_case();row=self.csv_rows()[0];self.assertEqual(report['legacy_reference_fallback_cells'],2)
  self.assertEqual(row['CDO_LL_L2_VX'],row['CDO_LL_L2_VY']);self.assertEqual(row['CDO_LL_L2_VX'],'0.500000')

 def test_csv_aliases_and_conflicting_alias_refusal(self):
  rows=self.rows();mapping=dict(zip(synthetic.FIELDS,['GlassID','GeometryID','class_name','CropPath','cdo']))
  self.save([{mapping[k]:v for k,v in r.items()} for r in rows],list(mapping.values()));self.run_case();self.out.unlink()
  rows[0]['GlassID']='OTHER-SYNTHETIC';self.save(rows,synthetic.FIELDS+['GlassID']);self.refused('CONFLICTING_MANIFEST_ALIASES')

 def test_duplicate_manifest_and_empty_inputs_refused(self):
  with self.assertRaisesRegex(ValueError,'DUPLICATE_MANIFEST'):self.run_case(manifests=[self.manifest,self.manifest])
  self.save([]);self.refused('EMPTY_MANIFEST')

 def test_manifest_counts_rows_and_headers_bounded(self):
  with self.assertRaisesRegex(ValueError,'MANIFEST_COUNT_LIMIT'):self.run_case(manifests=[self.manifest]*9)
  with patch.object(g,'MAX_ROWS',2):self.refused('MANIFEST_ROW_LIMIT')
  self.manifest.write_text('glass_id,glass_id\nA,B\n');self.refused('INVALID_MANIFEST_HEADER')

 def test_total_byte_and_pixel_budgets_refuse_before_output(self):
  with patch.object(g,'MAX_TOTAL_BYTES',1):self.refused('TOTAL_INPUT_SIZE_LIMIT')
  with patch.object(g,'MAX_TOTAL_PIXELS',1):self.refused('TOTAL_PIXEL_LIMIT')

 def test_unsupported_measurement_is_not_silently_skipped(self):
  for key,value in [('geom_name','LL_L3'),('class_yolo','unrecognized')]:
   rows=self.rows();original=rows[0][key];rows[0][key]=value;self.save(rows);self.refused('UNSUPPORTED_MEASUREMENT_ROW');rows[0][key]=original;self.save(rows)

 def test_spreadsheet_formula_panel_id_refused(self):
  rows=self.rows();rows[0]['glass_id']='=SYNTHETIC';self.save(rows);self.refused('PANEL_ID_REFUSED')

 def test_conflicting_panel_references_refused(self):
  (self.root/'other.xml').write_bytes((self.root/'reference.xml').read_bytes())
  rows=self.rows();rows[1]['cdo_xml_path']='other.xml';self.save(rows);self.refused('CONFLICTING_PANEL_REFERENCE')

 def test_xml_declarations_malformed_and_duplicate_keys(self):
  cases=[('<!DOCTYPE Body [<!ENTITY invented "x">]><Body/>','XML_DECLARATION_REFUSED'),('<Body>','XML'),('<Body>'+('<Measurement ID="LL_L2_VX" type="OL"><Result>1</Result></Measurement>'*2)+'</Body>','DUPLICATE_REFERENCE_KEY')]
  for text,code in cases:
   (self.root/'reference.xml').write_text(text)
   if code=='XML':
    with self.assertRaises(g.ET.ParseError):self.run_case()
   else:self.refused(code)
   self.assertFalse(self.out.exists())

 def test_xml_nonfinite_status_and_depth_limits(self):
  for text,code in [('<Body><Measurement ID="LL_L2_VX" type="OL"><Result>NaN</Result></Measurement></Body>','NONFINITE_REFERENCE'),('<Body><Measurement ID="LL_L2_VX" type="OL" status="FAIL"><Result>1</Result></Measurement></Body>','REFERENCE_STATUS_REFUSED'),('<n>'*17+'</n>'*17,'XML_STRUCTURE_LIMIT')]:
   (self.root/'reference.xml').write_text(text);self.refused(code)

 def test_missing_inputs_and_escape_refused(self):
  rows=self.rows();rows[0]['crop_path']='missing.png';self.save(rows);self.refused('PATH_UNAVAILABLE')
  outside=self.base/'outside.png';outside.write_bytes((self.root/'vx4.png').read_bytes());rows[0]['crop_path']='../outside.png';self.save(rows);self.refused('INPUT_OUTSIDE_ROOT_OR_NOT_FILE')

 def test_invalid_png_blank_and_dimensions_refused(self):
  p=self.root/'vx4.png';p.write_bytes(b'invented malformed png')
  with self.assertRaises(OSError):self.run_case()
  Image.new('L',(640,100),180).save(p);self.refused('INSUFFICIENT_PATTERN')
  Image.new('L',(2001,2000)).save(p);self.refused('IMAGE_DIMENSIONS_REFUSED')

 def test_nonfinite_and_swallowed_analysis_failures_refused(self):
  with patch.object(self.core,'compute_alignment',return_value=(math.nan,0)):self.refused('ANALYSIS_INCOMPLETE_OR_NONFINITE')
  with patch.object(self.engine,'plot_profiles_and_compute_alignment',side_effect=RuntimeError('invented failure')):self.refused('ANALYSIS_INCOMPLETE_OR_NONFINITE')

 def test_no_overwrite_no_input_tree_output_and_input_immutability(self):
  pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()};self.run_case();first=self.out.read_bytes()
  with self.assertRaisesRegex(ValueError,'OUTPUT_EXISTS'):self.run_case()
  self.assertEqual(self.out.read_bytes(),first)
  self.assertEqual(pins,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()})
  with self.assertRaisesRegex(ValueError,'OUTPUT_MUST_BE_OUTSIDE_INPUT_ROOT'):self.run_case(out=self.root/'out.csv')

 def test_input_change_detected_before_publish(self):
  real=self.core.aggregate_from_manifest
  def mutate(*a,**k):
   result=real(*a,**k);self.manifest.write_text(self.manifest.read_text()+'\n');return result
  with patch.object(self.core,'aggregate_from_manifest',side_effect=mutate):self.refused('INPUT_CHANGED_DURING_RUN')

 def test_symlink_or_reparse_input_is_refused(self):
  p=self.root/'vx4.png';real=Path.lstat
  def fake(item,*a,**k):
   if item==p:
    class Reparse:st_mode=0o100644;st_file_attributes=0x400
    return Reparse()
   return real(item,*a,**k)
  with patch.object(Path,'lstat',fake):self.refused('LINK_PATH_REFUSED')
  link=self.root/'linked.png'
  try:link.symlink_to(p)
  except OSError:return
  with self.assertRaisesRegex(ValueError,'LINK_PATH_REFUSED'):g.ordinary(link)

 def test_pinned_analyzer_tamper_refused_before_import(self):
  fake=self.base/'fake';(fake/'original').mkdir(parents=True);(fake/'BASELINE.json').write_bytes((ROOT/'BASELINE.json').read_bytes())
  marker=self.base/'must-not-exist';(fake/'original/panel_overlay_aggregate_v2_axisfix.py').write_text('raise AssertionError("must not execute")\n')
  with patch.object(g,'ROOT',fake),self.assertRaisesRegex(ValueError,'PINNED_IMPLEMENTATION_CHANGED'):g.modules()
  self.assertFalse(marker.exists())

 def test_copied_cli_from_unrelated_directory_and_safe_errors(self):
  command=[sys.executable,'-B',str(ROOT/'guarded_aggregate.py'),'--root',str(self.root),'--manifest','sites_manifest.csv','--out',str(self.out)]
  r=subprocess.run(command,cwd=self.base,capture_output=True,text=True,timeout=120);self.assertEqual(r.returncode,0,r.stderr);v=json.loads(r.stdout);self.assertEqual(v['measurements'],3);self.assertEqual(r.stderr,'')
  r=subprocess.run(command,cwd=self.base,capture_output=True,text=True,timeout=60);self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout),{'status':'ERROR','code':'OUTPUT_EXISTS'});self.assertNotIn(str(self.base),r.stdout+r.stderr)

if __name__=='__main__':unittest.main()
