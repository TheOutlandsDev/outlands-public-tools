"""Fictional intake, receipt, coverage and explicit evidence review through public CLIs."""
import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def require(value, code):
    if not value: raise ValueError(code)

def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()

def sha(raw): return hashlib.sha256(raw).hexdigest()
def tree(root): return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}

def run(workspace):
    require(workspace.is_absolute() and '..' not in workspace.parts and not workspace.exists() and workspace.parent.is_dir(), 'NEW_EXTERNAL_WORKSPACE_REQUIRED')
    require(workspace.resolve() == workspace and not workspace.is_relative_to(ROOT), 'TRUSTED_EXTERNAL_PARENT_REQUIRED')
    for parent in workspace.parents:
        require(not parent.is_symlink() and not parent.is_junction(), 'ORDINARY_PARENT_REQUIRED')
    require((ROOT/'tools/ingestion-run-coverage-checker/coverage.py').is_file() and (ROOT/'systems/test-evidence-workbench/workbench.py').is_file(), 'COMPLETE_PACKAGE_REQUIRED')
    workspace.mkdir(mode=0o700)
    count = 0
    def write(name, value):
        path = workspace/name
        with path.open('xb') as stream: stream.write(value if type(value) is bytes else encode(value))
        return path
    def call(script, *args, expected=0, error=None):
        nonlocal count
        p = subprocess.run([sys.executable, '-B', str(ROOT/script), *map(str,args)], capture_output=True, timeout=90,
                           env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONUTF8':'1'})
        count += 1
        if p.returncode != expected or p.stderr:
            write('private-command-failure-'+str(count)+'.log', p.stdout+p.stderr)
            raise ValueError('COMMAND_FAILED_PRIVATE_LOG_RETAINED')
        value = json.loads(p.stdout)
        if error: require(value == dict(error=error), 'EXPECTED_REFUSAL_REQUIRED')
        return value, p.stdout
    mapping = dict(format='outlands-table-map-v1', identity=['record_id'], unknown_columns='reject', fields=[
        dict(source='Record',target='record_id',type='text',required=True), dict(source='Units',target='units',type='integer',required=True)])
    mapping_path = write('mapping.json',mapping)
    equivalent = write('mapping-equivalent.json',dict(format='outlands-intake-mapping-diff-v1',before=mapping,after=mapping))
    same,_ = call('tools/intake-mapping-diff/mapping_diff.py','--input',equivalent)
    changed = copy.deepcopy(mapping); changed['fields'][1]['required'] = False
    difference = write('mapping-changed.json',dict(format='outlands-intake-mapping-diff-v1',before=mapping,after=changed))
    different,_ = call('tools/intake-mapping-diff/mapping_diff.py','--input',difference,expected=1)
    require(same['changes']==[] and different['changes']==[dict(target='units',code='REQUIRED_CHANGED')], 'MAPPING_ORACLE_FAILED')
    batches=[]; receipts=[]; preserved={}
    expected_counts=dict(input_rows=3,accepted_records=2,duplicate_rows=1,rejected_rows=0,conflict_rows=0)
    for number, name in enumerate(('a','b'),1):
        source=write('batch-'+name+'.csv',('Record,Units\nsample-'+name+'-one,7\nsample-'+name+'-two,9\nsample-'+name+'-one,7\n').encode())
        preview,raw=call('tools/workbook-intake-checker/intake.py','--input',source,'--mapping',mapping_path,'--format','csv')
        require(preview['counts']==expected_counts and preview['imported'] is False, 'INTAKE_ORACLE_FAILED')
        preview_path=write('preview-'+name+'.json',raw)
        declaration=dict(format='outlands-ingestion-receipt-v1',receipt_id='sample-'+name,source_format='csv',sheet=None,
                         source_sha256=sha(source.read_bytes()),mapping_sha256=sha(mapping_path.read_bytes()),preview_sha256=sha(raw),counts=expected_counts)
        receipt_path=write('receipt-'+name+'.json',declaration)
        checked,_=call('tools/ingestion-receipt-reconciler/receipts.py','--receipt',receipt_path,'--source',source,'--mapping',mapping_path,'--preview',preview_path)
        require(checked['row_counts_recomputed'] and checked['observed_counts']==expected_counts and checked['imported'] is False, 'RECEIPT_ORACLE_FAILED')
        batch=dict(id='batch-'+name,sequence=number,source_sha256=declaration['source_sha256'],mapping_sha256=declaration['mapping_sha256'],preview_sha256=declaration['preview_sha256'],counts=expected_counts)
        batches.append(batch)
        # These selected committed-status snapshots are authored declarations, not transaction evidence.
        receipts.append(dict(receipt_id='receipt-'+name,stream='sample-stream',batch=batch,status='committed',receipt_sha256=sha(receipt_path.read_bytes())))
        preserved.update({p.name:sha(p.read_bytes()) for p in (source,preview_path,receipt_path)})
    bad=copy.deepcopy(declaration);bad['preview_sha256']='0'*64
    bad_path=write('receipt-altered-pin.json',bad)
    rejected,_=call('tools/ingestion-receipt-reconciler/receipts.py','--receipt',bad_path,'--source',source,'--mapping',mapping_path,'--preview',preview_path,expected=1)
    require('PREVIEW_SHA256_MISMATCH' in rejected['issues'], 'ALTERED_PIN_NOT_CAUGHT')
    replay_path=write('replay.json',dict(format='outlands-batch-replay-v1',stream='sample-stream',expected=batches,receipts=receipts[:1]))
    replay,_=call('tools/batch-replay-planner/replay.py','--input',replay_path)
    require(replay['status']=='PASS' and replay['execution_authorized'] is False and [r['decision'] for r in replay['plan']]==['SKIP_ALREADY_COMMITTED','MANUAL_REVIEW_NEW_BATCH'], 'REPLAY_SCOPE_FAILED')
    cohort=dict(format='outlands-ingestion-run-coverage-v1',stream='sample-stream',expected=batches,receipts=receipts[:1])
    missing_path=write('coverage-missing.json',cohort)
    missing,_=call('tools/ingestion-run-coverage-checker/coverage.py','--input',missing_path,expected=1)
    require(not missing['cohort_complete'] and missing['declared_totals'] is None, 'MISSING_COVERAGE_NOT_WITHHELD')
    complete_path=write('coverage-complete.json',dict(cohort,receipts=receipts))
    coverage,raw=call('tools/ingestion-run-coverage-checker/coverage.py','--input',complete_path)
    totals=dict(input_rows=6,accepted_records=4,duplicate_rows=2,rejected_rows=0,conflict_rows=0)
    require(coverage['declared_totals']==totals and coverage['cohort_complete'] and coverage['actual_store_contents_verified'] is False, 'COVERAGE_ORACLE_FAILED')
    coverage_path=write('coverage-result.json',raw);preserved[coverage_path.name]=sha(raw)
    evidence=workspace/'evidence';requests=0
    def cli(*args,expected=0,error=None):
        return call('systems/test-evidence-workbench/workbench.py','--workspace',evidence,*args,expected=expected,error=error)[0]
    def request(command,value,expected=0,error=None):
        nonlocal requests
        requests+=1;name='inbox/workshop-'+str(requests)+'.json'
        with (evidence/name).open('xb') as stream:stream.write(encode(value))
        before=tree(evidence);result=cli(command,'--file',name,expected=expected,error=error)
        if expected: require(tree(evidence)==before, 'REFUSAL_CHANGED_EVIDENCE')
        return result
    cli('init')
    script='import json\nfrom pathlib import Path\nv=json.loads(Path("input.json").read_text(encoding="utf-8"))\nprint(json.dumps({"input_rows":v["totals"]["input_rows"],"coverage_sha256":v["coverage_sha256"]}))\n'
    definitions={}
    for name,expected_rows in [('sample-coverage',6),('sample-mismatch',7)]:
        definitions[name]=dict(format='outlands-trusted-check-v1',case_id=name,title='Fictional saved coverage assertion',script=script,
             input=dict(totals=totals,coverage_sha256=sha(raw)),expected=dict(exit_code=0,stdout=dict(input_rows=expected_rows,coverage_sha256=sha(raw)),stderr=''),timeout_ms=3000)
    bundle=evidence/'inbox/coverage-cases.json'
    with bundle.open('xb') as stream:stream.write(encode(dict(format='outlands-check-bundle-v1',cases=list(definitions.values()))))
    cli('import','--file','inbox/coverage-cases.json');cases=cli('cases')['cases']
    pins={name:sha(encode(dict(version=1,parent_sha256=None,definition=value))) for name,value in definitions.items()}
    require(len(cases)==2 and not list((evidence/'runs').iterdir()), 'IMPORT_EXECUTED_CHECKS')
    plan=dict(cases=[dict(case_id=name,expected_sha256=pin,trust_version=1) for name,pin in pins.items()])
    request('run',plan,2,'EXECUTION_TRUST_REQUIRED')
    for name,pin in pins.items():request('trust',dict(case_id=name,case_sha256=pin,expected_version=0,status='approved',actor='sample_operator',note='Reviewed authored fictional summary script only',checks=dict.fromkeys(('code_reviewed','authority','input_reviewed','effects_reviewed'),True)))
    started=request('run',plan);artifact=cli('artifact','--id',started['artifact_id']);payload=artifact['payload'];result=payload['result']
    require(sha(encode(payload))==artifact['artifact_sha256'] and (result['matched'],result['unmatched'])==(1,1), 'ARTIFACT_ORACLE_FAILED')
    for row in result['cases']:
        observed=row['observed'];definition=definitions[row['case_id']]
        require(observed['script_sha256']==sha(script.encode()) and observed['input_sha256']==sha(encode(definition['input'])), 'STAGED_BYTES_ORACLE_FAILED')
        streams={}
        for key in ('stdout','stderr'):
            record=observed['streams'][key];data=base64.b64decode(record['base64'],validate=True)
            require(sha(data)==record['sha256'] and len(data)==record['bytes'] and not record['truncated'], 'CAPTURE_ORACLE_FAILED');streams[key]=data
        actual=json.loads(streams['stdout']);passed=observed['exit_code']==0 and streams['stderr']==b'' and actual==definition['expected']['stdout']
        require(observed['passed']==passed and passed==(row['case_id']=='sample-coverage'), 'VERDICT_ORACLE_FAILED')
    cli('export','--artifact',artifact['artifact_id'],expected=2,error='APPROVAL_REQUIRED')
    review=dict(artifact_id=artifact['artifact_id'],artifact_sha256=artifact['artifact_sha256'],expected_version=0,status='approved',actor='sample_reviewer',note='Complete fictional failure evidence; no import or publication authorized',checks=dict.fromkeys(('quality','privacy','rights','context'),True))
    request('review',dict(review,checks=dict.fromkeys(review['checks'],False)),2,'REVIEW_CHECKS_REQUIRED');request('review',review)
    exported=cli('export','--artifact',artifact['artifact_id']);folder=evidence/exported['directory'];manifest=json.loads((folder/'manifest.json').read_bytes())
    require(manifest==exported['manifest'] and len(manifest['files'])==8 and manifest['public_release_authorized'] is False, 'EXPORT_SCOPE_FAILED')
    require({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}==set(manifest['files'])|{'manifest.json'}, 'EXPORT_INVENTORY_FAILED')
    for name,record in manifest['files'].items():
        data=(folder/name).read_bytes();require(record==dict(bytes=len(data),sha256=sha(data)), 'EXPORT_HASH_FAILED')
    reopened=cli('artifact','--id',artifact['artifact_id']);require(reopened['payload']==payload and reopened['review']['status']=='approved', 'REVIEW_CHANGED_VERDICT')
    require(all(sha((workspace/name).read_bytes())==pin for name,pin in preserved.items()) and sha(mapping_path.read_bytes())==sha(encode(mapping)), 'ORIGINAL_INPUT_CHANGED')
    summary=dict(schema=1,status='PASS',synthetic_only=True,command_checks=count,batches=2,source_rows=6,accepted_records=4,duplicate_rows=2,
        mapping_change_requires_review=True,altered_receipt_pin_caught=True,missing_coverage_withholds_totals=True,
        per_file_counts_recomputed=True,batch_receipts_are_declarations=True,actual_store_contents_verified=False,exactly_once_verified=False,
        evidence_checks=2,matched=1,unmatched=1,review_does_not_change_verdict=True,private_export_files=9,
        independent_raw_capture_and_export_hashes=True,original_inputs_unchanged=True,import_performed=False,external_services_used=False,
        execution_sandbox=False,descendant_containment=False,publication_authorized=False,runtime_bundled=False,
        scope='Actual public CLIs and two authored trusted Python summary checks; committed-status snapshots are fictional declarations, not transaction authority or an actual import')
    write('exercise-results.json',summary)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);args=p.parse_args()
    try:print(json.dumps(run(args.workspace),sort_keys=True))
    except Exception:print(json.dumps(dict(status='FAILED',error='INGESTION_EVIDENCE_EXERCISE_REFUSED_OR_ORACLE_FAILED')));sys.exit(1)
