"""Check supplied run lineage, artifact bytes and the existing public snapshot contract."""
import toolkit as t
import run_core as c
import snapshot


def declaration(raw):
    value=t.decode(raw)
    t.fields(value,{'format','run_id','manifest_sha256','snapshot_sha256','snapshot_policy_sha256',
                    'snapshot_bindings','steps'})
    t.require(value['format']=='outlands-run-provenance-v1','PROVENANCE_FORMAT_INVALID')
    t.identifier(value['run_id'])
    for key in ('manifest_sha256','snapshot_sha256','snapshot_policy_sha256'): t.sha(value[key])
    bindings=c.items(value['snapshot_bindings'],{'id','artifact'})
    for row in bindings.values(): t.identifier(row['artifact'])
    t.require(len({v['artifact'] for v in bindings.values()})==len(bindings),'DUPLICATE_SNAPSHOT_BINDING')
    steps=c.items(value['steps'],{'id','code_version','uses','produces'})
    for step in steps.values():
        t.identifier(step['code_version']); c.ids(step['uses'],1); c.ids(step['produces'],1)
    return value


def check(contract_raw,manifest_raw,snapshot_raw,policy_raw,inputs):
    contract=declaration(contract_raw)
    manifest,rows=c.manifest(manifest_raw)
    for raw in (snapshot_raw,policy_raw):
        t.require(type(raw) is bytes and len(raw)<=t.MAX_INPUT,'INPUT_LIMIT')
    observed,issues=c.observe(rows,inputs)
    def issue(code,item=None): issues.append(dict(code=code,item=item))
    for field,raw in (('manifest_sha256',manifest_raw),('snapshot_sha256',snapshot_raw),('snapshot_policy_sha256',policy_raw)):
        if contract[field]!=t.digest(raw): issue(field.upper()+'_MISMATCH')
    if contract['run_id']!=manifest['run_id']: issue('RUN_ID_MISMATCH')
    selected={v['id']:v['artifact'] for v in contract['snapshot_bindings']}
    source_ids={k for k,v in rows.items() if v['role']=='input'}
    t.require(set(selected.values())==source_ids,'SNAPSHOT_INPUT_COVERAGE_INVALID')
    snapshot_result=snapshot.check(snapshot_raw,policy_raw,{key:inputs[artifact] for key,artifact in selected.items()})
    for row in snapshot_result['issues']: issue('SNAPSHOT_'+row['code'],row['item'])
    available={k for k,v in rows.items() if v['role']!='result'}
    touched,produced=set(),set()
    for step in contract['steps']:
        uses,outputs=set(step['uses']),set(step['produces'])
        for key in sorted(uses|outputs):
            if key not in rows: issue('UNKNOWN_ARTIFACT_REFERENCE',key)
        if not uses<=available: issue('ARTIFACT_NOT_AVAILABLE',step['id'])
        if uses&outputs: issue('SELF_DEPENDENCY',step['id'])
        if len([key for key in uses if key in rows and rows[key]['role']=='code'])!=1:
            issue('ONE_CODE_ARTIFACT_REQUIRED',step['id'])
        if not any(key in rows and rows[key]['role'] in ('input','result') for key in uses):
            issue('DATA_INPUT_REQUIRED',step['id'])
        if outputs&produced: issue('DUPLICATE_PRODUCER',step['id'])
        if any(key in rows and rows[key]['role']!='result' for key in outputs):
            issue('EXTERNAL_ARTIFACT_PRODUCTION_FORBIDDEN',step['id'])
        touched.update(uses|outputs); produced.update(outputs)
        available.update(key for key in outputs if key in rows and rows[key]['role']=='result')
    if produced!={k for k,v in rows.items() if v['role']=='result'}: issue('RESULT_PRODUCTION_COVERAGE_MISMATCH')
    if touched!=set(rows): issue('ARTIFACT_USAGE_COVERAGE_MISMATCH')
    return dict(status='PASS' if not issues else 'REVIEW_REQUIRED',format='outlands-run-provenance-review-v1',
                run_id=manifest['run_id'],contract_sha256=t.digest(contract_raw),manifest_sha256=t.digest(manifest_raw),
                observed=observed,snapshot_status=snapshot_result['status'],
                steps=[dict(id=s['id'],code_version=s['code_version']) for s in contract['steps']],issues=issues,
                record_counts_independently_verified=False,execution_verified=False,
                source_authority_verified=False,target_changes_performed=False)


def main(argv=None):
    p=t.Parser(description='Check declared lineage and explicit pinned artifacts; execute nothing.')
    for flag in ('contract','manifest','snapshot','policy'): p.add_argument('--'+flag,required=True)
    p.add_argument('--item',nargs=2,action='append',default=[],metavar=('ID','FILE'))
    p.add_argument('--out')
    def operation(a):
        raw=t.read(a.manifest); _,rows=c.manifest(raw); bound=t.bindings(a.item)
        t.require(set(bound)==set(rows),'BINDING_COVERAGE_INVALID')
        return check(t.read(a.contract),raw,t.read(a.snapshot),t.read(a.policy),t.buffers(bound))
    return t.run(p,operation,argv)


if __name__=='__main__': raise SystemExit(main())
