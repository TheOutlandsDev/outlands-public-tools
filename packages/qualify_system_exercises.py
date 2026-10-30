"""Fresh complete-ZIP CLI/browser exercises and optional Ubuntu document rendering."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile
from build import verify_archive,digest


def require(ok,code):
    if not ok:raise ValueError(code)


def command(args,log,env=None,timeout=240):
    p=subprocess.run(list(map(str,args)),capture_output=True,env=env,timeout=timeout)
    log.write_bytes(p.stdout+p.stderr)
    require(p.returncode==0,'QUALIFICATION_COMMAND_FAILED_PRIVATE_LOG_RETAINED')
    return p


def qualify(packages,workspace,evidence,browser=False,render=False):
    require(workspace.is_absolute() and not workspace.exists() and workspace.parent.is_dir(),'NEW_PRIVATE_WORKSPACE_REQUIRED')
    require(evidence.is_absolute() and not evidence.exists() and evidence.parent.is_dir(),'NEW_EVIDENCE_DIRECTORY_REQUIRED')
    catalog=json.loads((packages/'catalog.json').read_bytes());record=next(r for r in catalog['downloads'] if r['id']=='complete')
    raw=(packages/record['filename']).read_bytes();require(digest(raw)==record['sha256'] and record['components']==127,'EXPECTED_REVIEWED_COMPLETE_ARCHIVE')
    verify_archive(raw);workspace.mkdir();evidence.mkdir()
    with zipfile.ZipFile(packages/record['filename']) as z:z.extractall(workspace/'extracted')
    root=next((workspace/'extracted').iterdir());private=workspace/'fictional-exercises'
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUTF8':'1','OUTLANDS_TEST_TEMP':str(workspace)}
    result=command([sys.executable,'-B',root/'workshops/system_exercises.py','--workspace',private],workspace/'cli.log',env)
    outcomes=json.loads(result.stdout);require(outcomes['status']=='PASS' and outcomes['exercises_passed']==2,'BOTH_EXERCISES_REQUIRED')
    lifecycle_run=command([sys.executable,'-B',root/'workshops/lifecycle_exercises.py','--workspace',workspace/'lifecycle-exercises'],workspace/'lifecycle-cli.log',env)
    lifecycle=json.loads(lifecycle_run.stdout);require(lifecycle['status']=='PASS' and lifecycle['exercises_passed']==2 and lifecycle['command_checks']==53,'BOTH_LIFECYCLE_EXERCISES_REQUIRED')
    ingestion_run=command([sys.executable,'-B',root/'workshops/ingestion_evidence.py','--workspace',workspace/'ingestion-evidence'],workspace/'ingestion-evidence.log',env)
    ingestion=json.loads(ingestion_run.stdout);require(ingestion['status']=='PASS' and ingestion['command_checks']==23 and ingestion['private_export_files']==9 and ingestion['matched']==1 and ingestion['unmatched']==1,'INGESTION_EVIDENCE_REQUIRED')
    manufacturing_run=command([sys.executable,'-B',root/'workshops/manufacturing_review.py','--workspace',workspace/'manufacturing-review'],workspace/'manufacturing-review.log',env)
    manufacturing=json.loads(manufacturing_run.stdout)
    require(manufacturing['status']=='PASS' and manufacturing['command_checks']==12 and manufacturing['expected_review_outcomes']==4 and manufacturing['operator_review']=='REQUIRED','MANUFACTURING_REVIEW_REQUIRED')
    require(manufacturing['individual_eligibility_does_not_prove_combined_capacity'] and manufacturing['missing_finish_withholds_totals'] and manufacturing['duplicates_do_not_inflate'] and manufacturing['resource_pins_match'] and manufacturing['original_inputs_unchanged'] and manufacturing['report_hashes_recomputed'],'MANUFACTURING_ORACLES_REQUIRED')
    material_run=command([sys.executable,'-B',root/'workshops/material_quality_review.py','--workspace',workspace/'material-quality-review'],workspace/'material-quality-review.log',env)
    material=json.loads(material_run.stdout)
    require(material['status']=='PASS' and material['command_checks']==24 and material['expected_review_outcomes']==13 and material['operator_review']=='REQUIRED','MATERIAL_QUALITY_REVIEW_REQUIRED')
    require(material['coverage_complete_still_requires_review'] and material['duplicates_do_not_inflate'] and material['lot_pins_match'] and material['explicit_report_mappings'] and material['original_inputs_unchanged'] and material['report_hashes_recomputed'],'MATERIAL_QUALITY_ORACLES_REQUIRED')
    browsers={}
    if browser:
        require(os.environ.get('GITHUB_ACTIONS')=='true','HOSTED_BROWSER_QUALIFICATION_ONLY')
        for name in ('import-migration-workbench','document-template-workbench','environment-setup-workbench','release-update-workbench'):
            run=command([sys.executable,'-B','-W','error',root/'systems'/name/'run_browser_checks.py'],workspace/(name+'.log'),{**env,'OUTLANDS_BROWSER_EVIDENCE':str(evidence)})
            log=(run.stdout+run.stderr).decode('utf-8');count=re.search(r'Ran (\d+) tests?',log)
            require(count is not None and int(count[1])==20 and 'skipped=' not in log,'ALL_20_BROWSER_WORKFLOWS_REQUIRED')
            browsers[name]=dict(tests=20,skips=0,status='PASS')
        require({'migration-wide.png','migration-narrow.png','documents-wide.png','documents-narrow.png','setup-wide.png','setup-narrow.png','release-wide.png','release-narrow.png'}<={p.name for p in evidence.iterdir()},'BROWSER_CAPTURES_REQUIRED')
    renders=[]
    if render:
        require(sys.platform=='linux' and all(shutil.which(n) for n in ('soffice','pdftotext','pdftoppm','pdfinfo')),'UBUNTU_RENDER_TOOLS_REQUIRED')
        documents=list((private/'documents/builds').glob('*/document.docx'));require(len(documents)==2,'BOTH_DOCUMENTS_REQUIRED')
        expected=outcomes['exercises']['documents']
        for path in documents:
            pin=hashlib.sha256(path.read_bytes()).hexdigest();kind='original' if pin==expected['original_docx_sha256'] else 'revised'
            require(pin==expected[kind+'_docx_sha256'],'RENDER_SOURCE_PIN_MISMATCH')
            target=workspace/('render-'+kind);target.mkdir();profile=target/'lo-profile'
            command(['soffice','-env:UserInstallation='+profile.as_uri(),'--headless','--convert-to','pdf','--outdir',target,path],target/'convert.log',env,120)
            pdf=target/'document.pdf';require(pdf.is_file() and pdf.stat().st_size>0,'RENDER_PDF_REQUIRED')
            text=command(['pdftotext','-layout',pdf,'-'],target/'text.log',env).stdout.decode('utf-8')
            for needle in ('Service handoff for Sample instrument','Sample bracket','Example cable','Total quantity 7','Requested items' if kind=='original' else 'Requested quantities'):require(needle in text,'RENDER_CONTENT_ORACLE_FAILED')
            require(('Review notes' in text)==(kind=='revised'),'RENDER_SECTION_ORACLE_FAILED')
            info=command(['pdfinfo',pdf],target/'info.log',env).stdout.decode('utf-8');pages=re.search(r'^Pages:\s+(\d+)',info,re.M)
            require(pages is not None and int(pages[1])==1,'ONE_PAGE_FICTIONAL_DOCUMENT_EXPECTED')
            command(['pdftoppm','-png','-r','120',pdf,evidence/('document-'+kind)],target/'images.log',env)
            renders.append(dict(case=kind,pages=1,total_quantity=7,docx_sha256=pin,renderer='LibreOffice and Poppler on Ubuntu',microsoft_word_visual_validation=False))
    captures={p.name:dict(bytes=p.stat().st_size,sha256=digest(p.read_bytes()),synthetic_only=True) for p in evidence.glob('*.png')}
    summary=dict(schema=1,status='PASS',source_revision=catalog['source_revision'],packaging_revision=catalog['packaging_revision'],package_sha256=record['sha256'],
                 exercises=outcomes,lifecycle_exercises=lifecycle,ingestion_evidence=ingestion,manufacturing_review=manufacturing,material_quality_review=material,browser_checks=browsers,document_rendering=renders,captures=captures,raw_logs_published=False,private_instances_published=False,
                 scope='Invented inputs; package bytes, CLI oracles, actual Chromium workflows and optional LibreOffice rendering; no production or Microsoft Word visual claim')
    (evidence/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    require({p.name for p in evidence.iterdir()}==set(captures)|{'summary.json'},'UNREVIEWED_PUBLIC_EVIDENCE_FILE')
    print(json.dumps(summary))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packages',required=True,type=Path);p.add_argument('--workspace',required=True,type=Path);p.add_argument('--evidence',required=True,type=Path);p.add_argument('--browser',action='store_true');p.add_argument('--render',action='store_true');a=p.parse_args();qualify(a.packages,a.workspace,a.evidence,a.browser,a.render)
