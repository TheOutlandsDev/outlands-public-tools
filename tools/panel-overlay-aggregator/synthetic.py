"""Invented PNG/CSV/XML inputs for the axis-fix aggregation walkthrough."""
import argparse,csv,json
from pathlib import Path
from engine.synthetic import image

FIELDS=['glass_id','geom_name','class_yolo','crop_path','cdo_xml_path']
def generate(out):
 from guarded_aggregate import ordinary
 out=ordinary(out,False);out.mkdir()
 for name,shift,portrait in [('vx4',4,False),('vx8',8,False),('vy_minus4',-4,True)]:image(shift,portrait).save(out/(name+'.png'))
 xml='<Body><Measurement ID="LL_L2_VX" type="OL" status="OK"><Result>0.25</Result></Measurement><Measurement ID="LL_L2_VY" type="OL" status="OK"><Result>-0.5</Result></Measurement></Body>'
 (out/'reference.xml').write_text(xml,encoding='utf-8')
 rows=[dict(glass_id='T-SYNTHETIC-PANEL-01',geom_name='LL_L2^invented',class_yolo=cls,crop_path=name+'.png',cdo_xml_path='reference.xml') for name,cls in [('vx4','vernier_h'),('vx8','vernier_h'),('vy_minus4','vernier_v')]]
 with (out/'sites_manifest.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
 (out/'EXPECTED.json').write_text(json.dumps(dict(fictional=True,panel='SYNTHETIC-PANEL-01',measurements=3,panels=1,LL_L2_VX=1.5,LL_L2_VY=-1.0,CDO_LL_L2_VX=.25,CDO_LL_L2_VY=-.5,DIFF_LL_L2_VX=1.25,DIFF_LL_L2_VY=-.5,absolute_tolerance_um=.03,calibration_claimed=False),indent=2)+'\n',encoding='utf-8')
 return dict(status='GENERATED',fictional=True,images=3,manifests=1,reference_xml=1)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);print(json.dumps(generate(p.parse_args().out)))
