"""Reproduce decisions from recorded normalized scores and explicit abstention policy."""
import toolkit as t
import decision_core as c

def case(row,labels):
    key,out=c.record(row,{'id','scores','declared_label'},('id',))
    t.require(type(row['scores']) is list and len(row['scores'])==len(labels),'SCORE_VECTOR_SIZE')
    seen=set();scores=[]
    for entry in row['scores']:
        t.fields(entry,{'label','value'});t.identifier(entry['label']);_,number=c.decimal(entry['value'])
        t.require(entry['label'] in labels and entry['label'] not in seen,'SCORE_LABEL_INVALID');seen.add(entry['label'])
        scores.append(dict(label=entry['label'],value=number))
    if row['declared_label'] is not None:t.identifier(row['declared_label']);t.require(row['declared_label'] in labels,'DECLARED_LABEL_INVALID')
    out['scores']=sorted(scores,key=lambda e:e['label']);return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','policy','cases'});t.require(value['format']=='outlands-score-abstention-v1','FORMAT_INVALID')
    policy=c.policy(value['policy']);cases,cc,issues=c.rows(value['cases'],lambda row:case(row,policy['labels']),'cases')
    if not cases:c.issue(issues,'cases',0,'EMPTY_CASE_COHORT')
    decisions=None;summary=None
    if not issues:
        decisions=[]
        for key,(index,row) in sorted(cases.items()):
            ranked=sorted([(c.decimal(r['value'])[0],r['label']) for r in row['scores']],key=lambda pair:(-pair[0],pair[1]))
            highest=ranked[0][0];tied=[label for score,label in ranked if score==highest];margin=highest-ranked[1][0];reasons=[]
            if highest<c.decimal(policy['minimum_score'])[0]:reasons.append('SCORE_BELOW_MINIMUM')
            if margin<c.decimal(policy['minimum_margin'])[0]:reasons.append('MARGIN_BELOW_MINIMUM')
            if len(tied)>1 and policy['tie_policy']=='abstain':reasons.append('TOP_SCORE_TIE')
            computed=None if reasons else tied[0];agrees=computed==row['declared_label']
            if not agrees:c.issue(issues,'cases',index,'DECISION_DECLARATION_MISMATCH')
            decisions.append(dict(id=key,computed_label=computed,declared_label=row['declared_label'],agrees_with_policy=agrees,
                highest_scoring_labels=tied,top_score=c.decimal_text(highest),margin=c.decimal_text(margin),tie_observed=len(tied)>1,abstention_reasons=reasons))
        summary=dict(cases=len(decisions),abstentions=sum(r['computed_label'] is None for r in decisions),declaration_mismatches=sum(not r['agrees_with_policy'] for r in decisions))
    result=c.base(raw,'outlands-score-abstention-review-v1',dict(cases=cc),issues)
    result.update(policy_sha256=c.pin(policy),decisions=decisions,summary=summary,confidence_calibrated=False,label_truth_verified=False,inference_performed=False)
    return result

def main(argv=None):return c.cli('Check recorded scores and explicit policy; no inference or real-world decisions.',check,argv)
if __name__=='__main__':raise SystemExit(main())
