"""Optional Linux visual qualification of invented documents; not application runtime."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from documents import application as app,runtime as r

def run(args):
    process=subprocess.run(args,capture_output=True,text=True,timeout=120)
    if process.returncode:raise RuntimeError('RENDER_COMMAND_FAILED')
    return process.stdout

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args();root=Path(args.output).absolute()
    if root.exists() or '..' in Path(args.output).parts:raise RuntimeError('NEW_RENDER_DIRECTORY_REQUIRED')
    with r.io_errors():root=r.guarded._export_path(root)
    for name in ('soffice','pdftoppm','pdftotext','pdfinfo'):
        if shutil.which(name) is None:raise RuntimeError('RENDER_DEPENDENCY_REQUIRED')
    root.mkdir();qa=root/'qa';qa.mkdir();instance=root/'private-instance';r.configure(instance,create=True)
    try:
        r.initialize();fixture=app.example()
        def job(fn,request):return fn(r.encode(dict(expected_head=app.overview()['head'],actor='sample_renderer',reason='Fictional visual qualification',request=request)))['job']['result']
        template=job(app.save_template,dict(parent_id=None,template=fixture['template']));cases=[]
        for name,count,sections in [('short',2,['summary','items','notes']),('long',44,['summary','items','notes'])]:
            values=copy.deepcopy(fixture['values'])
            if name=='long':values['items']=[dict(item='Sample item '+str(number).zfill(2)+' for a fictional review',quantity=number) for number in range(1,count+1)]
            preview=job(app.preview,dict(template_id=template['template_id'],template_sha256=template['template_sha256'],values=values,sections=sections));built=job(app.build,dict(preview_id=preview['preview_id'],preview_sha256=preview['preview_sha256'],checks=dict(quality=True,privacy=True,rights=True,context=True)));document=root/(name+'.docx');document.write_bytes(app.document_bytes(built['build_id']));profile=root/('profile-'+name)
            converted=subprocess.run(['soffice','-env:UserInstallation='+profile.as_uri(),'--headless','--convert-to','pdf','--outdir',str(root),str(document)],capture_output=True,text=True,timeout=120);pdf=root/(name+'.pdf')
            if converted.returncode or not pdf.is_file() or not pdf.stat().st_size:
                messages=(converted.stdout+'\n'+converted.stderr).lower();print(json.dumps(dict(status='FICTIONAL_RENDER_CONVERSION_DIAGNOSTIC',case=name,returncode=converted.returncode,source_load_error='source file could not be loaded' in messages,conversion_message='using filter' in messages,profile_lock_error='lock' in messages,output_present=pdf.is_file())),flush=True);raise RuntimeError('RENDER_PDF_MISSING')
            info=run(['pdfinfo',str(pdf)]);pages=re.search(r'^Pages:\s+(\d+)\s*$',info,re.M)
            if pages is None or not 1<=int(pages[1])<=6 or '612 x 792 pts' not in info:raise RuntimeError('RENDER_PAGE_CONTRACT_FAILED')
            text=run(['pdftotext','-layout',str(pdf),'-']);total=sum(row['quantity'] for row in values['items'])
            for needle in ('Service handoff for Sample instrument','Summary','Requested items','Total quantity '+str(total),'Review notes'):
                if needle not in text:raise RuntimeError('RENDER_TEXT_MISSING')
            for item in values['items']:
                if item['item'] not in text:raise RuntimeError('RENDER_ROW_MISSING')
            if name=='long' and int(pages[1])<2:raise RuntimeError('MULTIPAGE_FIXTURE_NOT_EXERCISED')
            run(['pdftoppm','-png','-r','100',str(pdf),str(qa/name)]);images=sorted(qa.glob(name+'-*.png'))
            if len(images)!=int(pages[1]) or any(p.read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n' for p in images):raise RuntimeError('RENDER_IMAGES_MISSING')
            cases.append(dict(case=name,rows=count,total_quantity=total,pages=int(pages[1]),letter_portrait=True,all_row_labels_found=True,document_sha256=built['document_sha256'],images=[dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in images]))
        report=dict(status='FICTIONAL_DOCUMENT_RENDER_PASS',renderer='LibreOffice and Poppler on Ubuntu',cases=cases,visual_review_required=True,microsoft_word_visual_validation=False);(qa/'render-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
    finally:r.close()

if __name__=='__main__':main()
