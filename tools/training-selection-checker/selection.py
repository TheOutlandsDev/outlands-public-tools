"""Reconcile pinned training selections, approvals and explicit exclusions."""
import toolkit as t
import decision_core as c
import dataset_common as d

def policy(value):
    _,out=c.record(value,{'id','revision','allowed_labels'},('id',),('revision',))
    out['allowed_labels']=c.tags(value['allowed_labels'],1);return out

def link(row,extra):
    key,out=c.record(row,{'id','record','record_revision','record_sha256'}|extra,('id','record'),('record_revision',))
    t.sha(row['record_sha256']);return key,out

def approval(row):
    key,out=link(row,{'policy_sha256','taxonomy_sha256','decision'})
    t.sha(row['policy_sha256']);t.sha(row['taxonomy_sha256'])
    t.require(row['decision'] in ('approve','reject'),'DECISION_INVALID');return key,out

def exclusion(row):
    key,out=link(row,{'reason'});t.identifier(row['reason']);return key,out

def selection(row):
    key,out=link(row,{'policy_sha256'});t.sha(row['policy_sha256']);return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','taxonomy','records','approvals','exclusions','selections','policy'})
    t.require(value['format']=='outlands-training-selection-v1','FORMAT_INVALID')
    taxonomy=c.taxonomy(value['taxonomy']);rule=policy(value['policy'])
    t.require(set(rule['allowed_labels'])<=set(taxonomy['labels']),'POLICY_LABEL_UNKNOWN')
    counts={};issues=[];records=d.records(value['records'],taxonomy['labels'],counts,issues)
    approvals=d.collect(value['approvals'],approval,'approvals',counts,issues)
    exclusions=d.collect(value['exclusions'],exclusion,'exclusions',counts,issues)
    selections=d.collect(value['selections'],selection,'selections',counts,issues,True)
    approval_slots=d.unique_slot(approvals,lambda r:r['record'],'approvals',issues)
    d.unique_slot(selections,lambda r:r['record'],'selections',issues)
    rule_pin,taxonomy_pin=c.pin(rule),c.pin(taxonomy)
    for side,rows in [('approvals',approvals),('exclusions',exclusions),('selections',selections)]:
        for position,row in rows.values():
            d.reference(row,records,side,position,issues)
            if side!='exclusions' and row['policy_sha256']!=rule_pin:c.issue(issues,side,position,'POLICY_PIN_MISMATCH')
            if side=='approvals' and row['taxonomy_sha256']!=taxonomy_pin:c.issue(issues,side,position,'TAXONOMY_PIN_MISMATCH')
    qualified=not issues;assessment=None;selected_pin=None
    if qualified:
        excluded={r['record'] for _,r in exclusions.values()};outcomes=[];chosen=[]
        for _,row in sorted(selections.values(),key=lambda p:p[1]['record']):
            key=row['record'];source=records[key][1];review=approval_slots.get(key);failures=[]
            if source['partition']!='train':failures.append('NONTRAINING_PARTITION')
            if source['label'] not in rule['allowed_labels']:failures.append('LABEL_NOT_ALLOWED')
            if review is None:failures.append('APPROVAL_MISSING')
            elif review['decision']!='approve':failures.append('APPROVAL_REJECTED')
            if key in excluded:failures.append('RECORD_EXCLUDED')
            for failure in failures:c.issue(issues,'selections',0,failure)
            outcomes.append(dict(record=key,eligible=not failures,failed_criteria=failures))
            chosen.append(source)
        eligible=all(r['eligible'] for r in outcomes)
        assessment=dict(selections=outcomes,selected_records=len(outcomes),eligible_records=sum(r['eligible'] for r in outcomes),
                        eligible_for_manual_export_review=eligible)
        if eligible:selected_pin=c.pin(chosen)
    return d.output(raw,'outlands-training-selection-report-v1',counts,issues,assessment=assessment,
        records_sha256=c.cohort_pin(records) if qualified else None,taxonomy_sha256=taxonomy_pin if qualified else None,
        policy_sha256=rule_pin if qualified else None,selected_records_sha256=selected_pin)

def main(argv=None):return c.cli('Review pinned training selections; never export or train.',check,argv)
if __name__=='__main__':raise SystemExit(main())
