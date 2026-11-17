"""Bounded explicit-manifest launcher around the unchanged axis-fix core."""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import warnings
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
MAX_ROWS=256
MAX_MANIFESTS=8
MAX_TOTAL_BYTES=64*1048576
MAX_TOTAL_PIXELS=16_000_000
ALIASES={
 'glass_id':('glass_id','GlassID','glass','GlassId'),
 'cdo_xml_path':('cdo_xml_path','cdo_path','cdo_xml','cdo'),
 'geom_name':('geom_name','geom','GeometryID','geometry_id'),
 'class_yolo':('class_yolo','class_name','class'),
 'crop_path':('crop_path','CropPath'),
}

def sha(raw):return hashlib.sha256(raw).hexdigest()

def ordinary(value,exists=True):
 p=Path(os.path.abspath(value))
 for part in (p,*p.parents):
  try:s=part.lstat()
  except FileNotFoundError:
   if part==p and not exists:continue
   raise ValueError('PATH_UNAVAILABLE') from None
  if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:raise ValueError('LINK_PATH_REFUSED')
 return p

def selected_file(value,root,limit):
 p=Path(value);p=ordinary(p if p.is_absolute() else root/p)
 if not p.is_relative_to(root) or not p.is_file():raise ValueError('INPUT_OUTSIDE_ROOT_OR_NOT_FILE')
 if p.stat().st_size>limit:raise ValueError('INPUT_SIZE_LIMIT')
 return p

def modules():
 baseline=json.loads((ROOT/'BASELINE.json').read_bytes())
 loaded=[]
 for name,path in [('axisfix','original/panel_overlay_aggregate_v2_axisfix.py'),('published_rev3b','engine/Vern_Analyze_v2.py')]:
  p=ROOT/path
  if sha(p.read_bytes())!=baseline['source_sha256'][path]:raise ValueError('PINNED_IMPLEMENTATION_CHANGED')
  if name=='published_rev3b':
   import matplotlib
   matplotlib.use('Agg',force=True)
  spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);loaded.append(m)
 return loaded

def canonical(row,name):
 values={str(row[k]).strip() for k in ALIASES[name] if row.get(k) is not None and str(row[k]).strip()}
 if len(values)>1:raise ValueError('CONFLICTING_MANIFEST_ALIASES')
 value=next(iter(values),'')
 if len(value)>4096 or '\x00' in value:raise ValueError('INVALID_MANIFEST_FIELD')
 return value

def reference(path,core):
 raw=path.read_bytes();text=raw.decode('utf-8-sig')
 if '\x00' in text or re.search(r'<!\s*(?:DOCTYPE|ENTITY)',text,re.I):raise ValueError('XML_DECLARATION_REFUSED')
 tree=ET.fromstring(text);stack=[(tree,1)];count=0
 while stack:
  node,depth=stack.pop();count+=1
  if depth>16 or count>2048:raise ValueError('XML_STRUCTURE_LIMIT')
  stack.extend((child,depth+1) for child in node)
 keys=set()
 for m in tree.iter('Measurement'):
  key=(m.get('ID') or '').strip().upper().split('^',1)[0]
  if not core.is_overlay_measurement(m) or not (core.AOI_AXIS_RE.fullmatch(key) or core.AOI_LEGACY_RE.fullmatch(key)):continue
  if key in keys:raise ValueError('DUPLICATE_REFERENCE_KEY')
  keys.add(key)
  if (m.get('status') or '').strip().upper() not in ('','OK'):raise ValueError('REFERENCE_STATUS_REFUSED')
  try:value=float(m.findtext('Result') or '')
  except ValueError:raise ValueError('INVALID_REFERENCE_NUMBER') from None
  if not math.isfinite(value):raise ValueError('NONFINITE_REFERENCE')

def png(path,axis,engine):
 from PIL import Image
 try:
  with warnings.catch_warnings():
   warnings.simplefilter('error',Image.DecompressionBombWarning)
   with Image.open(path) as image:
    if image.format!='PNG' or getattr(image,'n_frames',1)!=1:raise ValueError('SINGLE_PNG_REQUIRED')
    w,h=image.size
    if min(w,h)<2 or w*h>4_000_000:raise ValueError('IMAGE_DIMENSIONS_REFUSED')
    image.load()
 except (Image.DecompressionBombError,Image.DecompressionBombWarning):raise ValueError('IMAGE_DIMENSIONS_REFUSED') from None
 _,gray=engine.load_image_as_arrays(str(path))
 groups=(engine.LANDSCAPE_ROWS_GROUP_A,engine.LANDSCAPE_ROWS_GROUP_B) if axis=='VX' else (engine.PORTRAIT_COLS_GROUP_A,engine.PORTRAIT_COLS_GROUP_B)
 for group in groups:
  indices=engine.validate_indices(group,h if axis=='VX' else w)
  if not indices:raise ValueError('SAMPLING_GROUPS_UNAVAILABLE')
  scores=[engine.rev3b_profile_qc(gray[i,:] if axis=='VX' else gray[:,i]) for i in indices]
  # A separate featureless-input refusal, not expanded sampling or the Rev 3b gate.
  if not any(q['contrast']>=10 and q['band_count']>=8 for q in scores):raise ValueError('INSUFFICIENT_PATTERN')
 return w*h

def aggregate(root,manifests,out):
 root=ordinary(root)
 if not root.is_dir():raise ValueError('INPUT_ROOT_REQUIRED')
 out=ordinary(out,False)
 if os.path.lexists(out):raise ValueError('OUTPUT_EXISTS')
 if out.is_relative_to(root):raise ValueError('OUTPUT_MUST_BE_OUTSIDE_INPUT_ROOT')
 if not 1<=len(manifests)<=MAX_MANIFESTS:raise ValueError('MANIFEST_COUNT_LIMIT')
 core,engine=modules();inputs={};rows=[];panels={};seen_manifests=set();total_bytes=0;total_pixels=0
 def keep(p):
  nonlocal total_bytes
  if p not in inputs:
   total_bytes+=p.stat().st_size
   if total_bytes>MAX_TOTAL_BYTES:raise ValueError('TOTAL_INPUT_SIZE_LIMIT')
   inputs[p]=sha(p.read_bytes())
 try:
  for item in manifests:
   manifest=selected_file(item,root,1048576)
   if manifest in seen_manifests:raise ValueError('DUPLICATE_MANIFEST')
   seen_manifests.add(manifest);keep(manifest)
   with manifest.open('r',encoding='utf-8-sig',newline='') as stream:
    reader=csv.DictReader(stream)
    if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)):raise ValueError('INVALID_MANIFEST_HEADER')
    for row in reader:
     if len(rows)>=MAX_ROWS:raise ValueError('MANIFEST_ROW_LIMIT')
     if None in row:raise ValueError('EXTRA_MANIFEST_CELLS')
     r={key:canonical(row,key) for key in ALIASES}
     panel=core.panel_id_from_glass(r['glass_id']);corner,layer=core.parse_corner_layer_from_geom(r['geom_name']);axis=core.axis_from_class(r['class_yolo'])
     if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',panel):raise ValueError('PANEL_ID_REFUSED')
     if not corner or layer!='L2' or axis not in ('VX','VY') or not r['crop_path']:raise ValueError('UNSUPPORTED_MEASUREMENT_ROW')
     crop=selected_file(r['crop_path'],root,16*1048576);keep(crop);total_pixels+=png(crop,axis,engine)
     if total_pixels>MAX_TOTAL_PIXELS:raise ValueError('TOTAL_PIXEL_LIMIT')
     r['crop_path']=str(crop)
     ref=None
     if r['cdo_xml_path']:
      ref=selected_file(r['cdo_xml_path'],root,524288);keep(ref);reference(ref,core);r['cdo_xml_path']=str(ref)
     # The legacy core uses the first reference per panel. Refuse conflicting
     # declarations instead of silently hiding them behind that cache.
     if panel in panels and panels[panel]!=ref:raise ValueError('CONFLICTING_PANEL_REFERENCE')
     panels[panel]=ref;rows.append(r)
  if not rows:raise ValueError('EMPTY_MANIFEST')
  new,old={},{}
  with tempfile.TemporaryDirectory(prefix='panel-overlay-input-') as temp:
   prepared=Path(temp)/'selected.csv'
   with prepared.open('w',encoding='utf-8',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(ALIASES));writer.writeheader();writer.writerows(rows)
   core.aggregate_from_manifest(prepared,engine,new,old,False)
  values=[v for panel in new.values() for cell in panel.values() for v in cell]
  if len(values)!=len(rows) or not all(math.isfinite(v) and math.isfinite(s) for v,s in values):raise ValueError('ANALYSIS_INCOMPLETE_OR_NONFINITE')
  result=core.panel_rows(new,old)
  if len(result)!=len(panels):raise ValueError('PANEL_COVERAGE_MISMATCH')
  for p,pin in inputs.items():
   if sha(p.read_bytes())!=pin:raise ValueError('INPUT_CHANGED_DURING_RUN')
  fallback=sum(old.get(panel,{}).get(key) is None and old.get(panel,{}).get(key.split('_',1)[0]+'_L2') is not None for panel in panels for key in core.MEAS_ORDER)
  buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=core.CSV_HEADER);writer.writeheader();writer.writerows(result)
  raw=buffer.getvalue().encode('utf-8')
  with out.open('xb') as stream:stream.write(raw)
  return dict(schema=1,status='RESULT_REQUIRES_REVIEW',panels=len(result),measurements=len(rows),selected_manifests=len(manifests),input_files=len(inputs),csv_sha256=sha(raw),csv_bytes=len(raw),legacy_reference_fallback_cells=fallback,rev3b_sampling_qc_applied=False,featureless_input_refusal=True,quality_approved=False,calibration_verified=False,input_bytes_unchanged=True)
 finally:engine.plt.close('all')

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True,type=Path);p.add_argument('--manifest',required=True,action='append',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args(argv)
 try:value=aggregate(a.root,a.manifest,a.out)
 except (OSError,ValueError,RuntimeError,ET.ParseError,UnicodeError,csv.Error) as error:
  code=str(error) if isinstance(error,ValueError) and re.fullmatch('[A-Z_]+',str(error)) else 'INPUT_OR_ANALYSIS_FAILED'
  print(json.dumps(dict(status='ERROR',code=code)));return 2
 print(json.dumps(value,allow_nan=False));return 0

if __name__=='__main__':raise SystemExit(main())
