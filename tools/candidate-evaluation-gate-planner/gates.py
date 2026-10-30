"""Plan manual evaluation review from exact declared cohort counts, never deployment."""
import toolkit as t
import decision_core as c

def truth(row,labels):
    key,out=c.record(row,{'id','expected_label'},('id','expected_label'));t.require(row['expected_label'] in labels,'EXPECTED_LABEL_INVALID');return key,out
def prediction(row,labels):
    key,out=c.record(row,{'id','label'},('id',))
    if row['label'] is not None:t.identifier(row['label']);t.require(row['label'] in labels,'PREDICTION_LABEL_INVALID')
    return key,out
def model(value,labels,side):
    _,out=c.record(value,{'id','revision','prompt_sha256','decision_policy_sha256','cohort_sha256','taxonomy_sha256','predictions'},('id',),('revision',))
    for key in ('prompt_sha256','decision_policy_sha256','cohort_sha256','taxonomy_sha256'):t.sha(value[key])
    rows,counts,issues=c.rows(value['predictions'],lambda row:prediction(row,labels),side)
    return out,rows,counts,issues
def policy(value):
    t.fields(value,{'minimum_accuracy','maximum_regression','maximum_abstention_increase','required_prompt_sha256','required_decision_policy_sha256'});out=dict(value)
    for key in ('minimum_accuracy','maximum_regression','maximum_abstention_increase'):_,out[key]=c.decimal(value[key])
    for key in ('required_prompt_sha256','required_decision_policy_sha256'):t.sha(value[key])
    return out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','labels','cohort','baseline','candidate','policy'});t.require(value['format']=='outlands-candidate-evaluation-gate-v1','FORMAT_INVALID')
    taxonomy=c.taxonomy(value['labels']);rules=policy(value['policy']);cohort,cc,issues=c.rows(value['cohort'],lambda r:truth(r,taxonomy['labels']),'cohort');cohort_valid=bool(cohort) and not issues
    before,bp,bc,other=model(value['baseline'],taxonomy['labels'],'baseline');issues+=other
    after,ap,ac,other=model(value['candidate'],taxonomy['labels'],'candidate');issues+=other
    if not cohort:c.issue(issues,'cohort',0,'EMPTY_COHORT')
    if before['id']!=after['id']:c.issue(issues,'models',0,'MODEL_ID_MISMATCH')
    if after['revision']<=before['revision']:c.issue(issues,'models',0,'CANDIDATE_REVISION_NOT_NEWER')
    for side,header,predictions in [('baseline',before,bp),('candidate',after,ap)]:
        if header['cohort_sha256']!=c.cohort_pin(cohort):c.issue(issues,side,0,'COHORT_PIN_MISMATCH')
        if header['taxonomy_sha256']!=c.pin(taxonomy):c.issue(issues,side,0,'TAXONOMY_PIN_MISMATCH')
        for key,(index,_) in predictions.items():
            if key not in cohort:c.issue(issues,side,index,'CASE_NOT_IN_COHORT')
        for key in cohort:
            if key not in predictions:c.issue(issues,side,0,'CASE_PREDICTION_MISSING')
    if after['prompt_sha256']!=rules['required_prompt_sha256']:c.issue(issues,'candidate',0,'CANDIDATE_PROMPT_PIN_MISMATCH')
    if after['decision_policy_sha256']!=rules['required_decision_policy_sha256']:c.issue(issues,'candidate',0,'CANDIDATE_POLICY_PIN_MISMATCH')
    metrics=assessment=None
    if not issues:
        n=len(cohort);metrics={}
        for side,predictions in [('baseline',bp),('candidate',ap)]:
            correct=sum(predictions[key][1]['label']==row['expected_label'] for key,(_,row) in cohort.items())
            abstained=sum(row['label'] is None for _,row in predictions.values());incorrect=n-correct-abstained
            t.require(correct+incorrect+abstained==n and incorrect>=0,'EVALUATION_ACCOUNTING_FAILED')
            metrics[side]=dict(cohort=n,correct=correct,incorrect=incorrect,abstained=abstained,accuracy=c.ratio(correct,n),abstention=c.ratio(abstained,n))
        from fractions import Fraction
        b,a=metrics['baseline'],metrics['candidate'];failed=[]
        if Fraction(a['correct'],n)<c.decimal(rules['minimum_accuracy'])[0]:failed.append('MINIMUM_ACCURACY_NOT_MET')
        if Fraction(b['correct']-a['correct'],n)>c.decimal(rules['maximum_regression'])[0]:failed.append('ACCURACY_REGRESSION_EXCEEDED')
        if Fraction(a['abstained']-b['abstained'],n)>c.decimal(rules['maximum_abstention_increase'])[0]:failed.append('ABSTENTION_INCREASE_EXCEEDED')
        assessment=dict(eligible_for_manual_review=not failed,failed_criteria=failed,
            accuracy_delta=c.ratio(a['correct']-b['correct'],n),abstention_delta=c.ratio(a['abstained']-b['abstained'],n))
        if failed:c.issue(issues,'evaluation',0,'CANDIDATE_REQUIRES_REVIEW')
    result=c.base(raw,'outlands-candidate-evaluation-review-v1',dict(cohort=cc,baseline=bc,candidate=ac),issues)
    result.update(cohort_sha256=c.cohort_pin(cohort) if cohort_valid else None,taxonomy_sha256=c.pin(taxonomy),metrics=metrics,assessment=assessment,
        artifact_bytes_verified=False,label_truth_verified=False,holdout_independence_verified=False,deploy_authorized=False,release_performed=False,training_performed=False)
    return result

def main(argv=None):return c.cli('Plan review of supplied evaluations; no training, inference or deployment.',check,argv)
if __name__=='__main__':raise SystemExit(main())
