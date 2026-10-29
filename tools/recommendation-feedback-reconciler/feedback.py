"""Reconcile immutable recommendation revisions, explicit decisions and observed outcomes."""
from collections import Counter
import toolkit as t
import metrics_core as c


def key(row):
    t.identifier(row['recommendation_id']); t.integer(row['revision'],1000000,1)
    return row['recommendation_id'],row['revision']


def recommendation(row):
    t.fields(row,{'recommendation_id','revision','action'}); identity=key(row); t.identifier(row['action'])
    return identity,dict(row)


def decision(row):
    t.fields(row,{'recommendation_id','revision','decision'}); identity=key(row)
    t.require(row['decision'] in ('accept','reject','defer'),'DECISION_INVALID')
    return identity,dict(row)


def outcome(row):
    t.fields(row,{'recommendation_id','revision','status','observed'}); identity=key(row)
    t.require(row['status'] in ('pending','observed'),'OUTCOME_STATUS_INVALID')
    observed=row['observed']
    if row['status']=='pending': t.require(observed is None,'PENDING_VALUE_FORBIDDEN')
    else: c.number(observed); observed=c.canonical(observed)
    return identity,dict(recommendation_id=identity[0],revision=identity[1],status=row['status'],observed=observed)


def reconcile(raw):
    value=t.decode(raw); t.fields(value,{'format','recommendations','decisions','outcomes'})
    t.require(value['format']=='outlands-recommendation-feedback-v1','FORMAT_INVALID')
    t.require(type(value['recommendations']) is list and 1<=len(value['recommendations'])<=1000,'RECOMMENDATIONS_REQUIRED')
    records,rc,issues=c.rows(value['recommendations'],recommendation,'recommendations')
    decisions,dc,other=c.rows(value['decisions'],decision,'decisions'); issues+=other
    outcomes,oc,other=c.rows(value['outcomes'],outcome,'outcomes'); issues+=other
    for side,rows in (('decisions',decisions),('outcomes',outcomes)):
        for identity,(index,row) in rows.items():
            if identity not in records: issues.append(dict(side=side,row=index,code='ORPHAN_REVISION'))
    for identity,(index,row) in outcomes.items():
        if identity not in decisions or decisions[identity][1]['decision']!='accept':
            issues.append(dict(side='outcomes',row=index,code='OUTCOME_WITHOUT_ACCEPTANCE'))
    states=[]; accepted=observed=0
    if not issues:
        for identity in sorted(records):
            if identity not in decisions: state='AWAITING_REVIEW'
            else:
                choice=decisions[identity][1]['decision']
                if choice=='reject': state='REJECTED'
                elif choice=='defer': state='DEFERRED'
                else:
                    accepted+=1
                    if identity in outcomes and outcomes[identity][1]['status']=='observed':
                        state='OUTCOME_RECORDED'; observed+=1
                    else: state='ACCEPTED_PENDING_OUTCOME'
            states.append(dict(recommendation_id=identity[0],revision=identity[1],state=state))
    return dict(status='PASS' if not issues else 'REVIEW_REQUIRED',format='outlands-feedback-review-v1',
                input_sha256=t.digest(raw),counts=dict(recommendations=rc,decisions=dc,outcomes=oc),issues=issues,
                states=states,state_counts=dict(Counter(row['state'] for row in states)) if not issues else None,
                all_acceptances_have_observed_outcomes=not issues and accepted>0 and observed==accepted,
                outcome_truth_verified=False,causal_effect_estimated=False,
                model_or_policy_updated=False,target_changes_performed=False)


def main(argv=None): return c.cli('Reconcile explicit revision-bound feedback; never update or execute a recommendation.',reconcile,argv)
if __name__=='__main__': raise SystemExit(main())
