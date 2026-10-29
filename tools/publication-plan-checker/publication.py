"""Review a pinned selection and caller review assertions; never copy or publish it."""
import toolkit as t
import run_core as c


def plan(raw):
    value=t.decode(raw)
    t.fields(value,{'format','plan_id','run_id','manifest_sha256','review_sha256','items'})
    t.require(value['format']=='outlands-publication-plan-v1','PLAN_FORMAT_INVALID')
    for key in ('plan_id','run_id'): t.identifier(value[key])
    for key in ('manifest_sha256','review_sha256'): t.sha(value[key])
    rows=c.items(value['items'],{'id','sha256','public_name'})
    c.selected_names(rows)
    return value,rows


def review(raw):
    value=t.decode(raw)
    t.fields(value,{'format','review_id','run_id','manifest_sha256','items'})
    t.require(value['format']=='outlands-publication-review-v1','REVIEW_FORMAT_INVALID')
    for key in ('review_id','run_id'): t.identifier(value[key])
    t.sha(value['manifest_sha256'])
    rows=c.items(value['items'],{'id','sha256','public_name','decision','rights_reviewed','privacy_reviewed','context_reviewed'})
    c.selected_names(rows)
    for row in rows.values():
        t.require(row['decision'] in ('allow','hold') and
                  all(type(row[k]) is bool for k in ('rights_reviewed','privacy_reviewed','context_reviewed')),
                  'REVIEW_ASSERTION_INVALID')
    return value,rows


def check(plan_raw,manifest_raw,review_raw,inputs):
    proposed,selected=plan(plan_raw); reviewed,decisions=review(review_raw)
    manifest,artifacts=c.manifest(manifest_raw)
    c.buffers(inputs,selected)
    issues=[]
    def issue(code,item=None): issues.append(dict(code=code,item=item))
    manifest_pin=t.digest(manifest_raw)
    if proposed['manifest_sha256']!=manifest_pin or reviewed['manifest_sha256']!=manifest_pin: issue('MANIFEST_PIN_MISMATCH')
    if proposed['review_sha256']!=t.digest(review_raw): issue('REVIEW_PIN_MISMATCH')
    if proposed['run_id']!=manifest['run_id'] or reviewed['run_id']!=manifest['run_id']: issue('RUN_ID_MISMATCH')
    if set(selected)!=set(decisions): issue('REVIEW_SELECTION_COVERAGE_MISMATCH')
    observations=[]
    for key,row in sorted(selected.items()):
        raw=inputs[key]; actual=dict(id=key,public_name=row['public_name'],bytes=len(raw),sha256=t.digest(raw))
        observations.append(actual)
        if key not in artifacts:
            issue('UNKNOWN_ARTIFACT_REFERENCE',key)
        else:
            artifact=artifacts[key]
            if row['sha256']!=artifact['sha256']: issue('PLAN_ARTIFACT_PIN_MISMATCH',key)
            if actual['sha256']!=artifact['sha256']: issue('ARTIFACT_HASH_MISMATCH',key)
            if actual['bytes']!=artifact['bytes']: issue('ARTIFACT_SIZE_MISMATCH',key)
        if key not in decisions: continue
        decision=decisions[key]
        if any(row[k]!=decision[k] for k in ('id','sha256','public_name')): issue('REVIEW_ITEM_MISMATCH',key)
        if decision['decision']!='allow': issue('REVIEW_HELD',key)
        if not all(decision[k] for k in ('rights_reviewed','privacy_reviewed','context_reviewed')):
            issue('REVIEW_ASSERTIONS_INCOMPLETE',key)
    return dict(status='PASS' if not issues else 'REVIEW_REQUIRED',format='outlands-publication-plan-review-v1',
                plan_id=proposed['plan_id'],run_id=manifest['run_id'],plan_sha256=t.digest(plan_raw),
                manifest_sha256=manifest_pin,review_sha256=t.digest(review_raw),selected=observations,issues=issues,
                interpretation='DECLARED_PLAN_CONSISTENCY_ONLY',publication_authorized=False,
                privacy_independently_verified=False,rights_independently_verified=False,target_changes_performed=False)


def main(argv=None):
    p=t.Parser(description='Check a reviewed selection; never copy, move, upload or publish artifacts.')
    for flag in ('plan','manifest','review'): p.add_argument('--'+flag,required=True)
    p.add_argument('--item',nargs=2,action='append',default=[],metavar=('ID','FILE'))
    p.add_argument('--out')
    def operation(a):
        raw=t.read(a.plan); _,selected=plan(raw); bound=t.bindings(a.item)
        t.require(set(bound)==set(selected),'BINDING_COVERAGE_INVALID')
        return check(raw,t.read(a.manifest),t.read(a.review),t.buffers(bound))
    return t.run(p,operation,argv)


if __name__=='__main__': raise SystemExit(main())
