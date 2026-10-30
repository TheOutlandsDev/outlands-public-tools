"""Explicit probability cohorts and exact arithmetic without fitting or inference."""
from fractions import Fraction
import toolkit as t
import decision_core as c

def fraction(value):
    value=Fraction(value)
    return dict(numerator=value.numerator,denominator=value.denominator,exact_fraction=str(value.numerator)+'/'+str(value.denominator))

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def output(raw,fmt,counts,issues,**values):
    report=c.base(raw,fmt,counts,issues)
    report.update(probability_interpretation_verified=False,label_truth_verified=False,
        cohort_independence_verified=False,calibration_established=False,model_fitted=False,
        model_updated=False,inference_performed=False,artifact_bytes_verified=False,**values)
    return report

def contract(value):
    _,out=c.record(value,{'id','revision','model','model_revision','positive_label','negative_label'},('id','model','positive_label','negative_label'),('revision','model_revision'))
    t.require(value['positive_label']!=value['negative_label'],'LABELS_MUST_DIFFER');return out

def case(row):return c.record(row,{'id','revision'},('id',),('revision',))

def prediction(row):
    key,out=c.record(row,{'id','case','case_revision','case_sha256','model','model_revision','probability'},('id','case','model'),('case_revision','model_revision'))
    t.sha(row['case_sha256'])
    if row['probability'] is not None:_,out['probability']=c.decimal(row['probability'])
    return key,out

def outcome(row):
    key,out=c.record(row,{'id','case','case_revision','case_sha256','label'},('id','case'),('case_revision',))
    t.sha(row['case_sha256'])
    if row['label'] is not None:t.identifier(row['label'])
    return key,out

def slots(selected,side,issues):
    result={}
    for position,row in selected.values():
        if row['case'] in result:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        result[row['case']]=row
    return result

def evaluation(value,counts,issues):
    rule=contract(value['contract']);cohort=collect(value['cohort'],case,'cohort',counts,issues)
    predictions=collect(value['predictions'],prediction,'predictions',counts,issues,False)
    outcomes=collect(value['outcomes'],outcome,'outcomes',counts,issues,False)
    predicted=slots(predictions,'predictions',issues);observed=slots(outcomes,'outcomes',issues)
    for side,rows in [('predictions',predictions),('outcomes',outcomes)]:
        for position,row in rows.values():
            target=cohort.get(row['case'])
            if target is None:c.issue(issues,side,position,'CASE_UNKNOWN')
            elif row['case_revision']!=target[1]['revision'] or row['case_sha256']!=c.pin(target[1]):c.issue(issues,side,position,'CASE_SNAPSHOT_MISMATCH')
            if side=='predictions' and (row['model']!=rule['model'] or row['model_revision']!=rule['model_revision']):c.issue(issues,side,position,'MODEL_BINDING_MISMATCH')
            if side=='outcomes' and row['label'] is not None and row['label'] not in (rule['positive_label'],rule['negative_label']):c.issue(issues,side,position,'LABEL_UNKNOWN')
    qualified=not issues;assessment=None;metrics=None;cases=[]
    pins=dict(contract_sha256=c.pin(rule),cohort_sha256=c.cohort_pin(cohort),predictions_sha256=c.cohort_pin(predictions),outcomes_sha256=c.cohort_pin(outcomes))
    if qualified:
        total=Fraction(0);missing_predictions=[];missing_outcomes=[];unknown_probabilities=[];unknown_outcomes=[]
        for key in sorted(cohort):
            pred=predicted.get(key);actual=observed.get(key);p=None;y=None;error=None
            if pred is None:missing_predictions.append(key);c.issue(issues,'coverage',0,'PREDICTION_MISSING')
            elif pred['probability'] is None:unknown_probabilities.append(key);c.issue(issues,'coverage',0,'PROBABILITY_UNKNOWN')
            else:p=c.decimal(pred['probability'])[0]
            if actual is None:missing_outcomes.append(key);c.issue(issues,'coverage',0,'OUTCOME_MISSING')
            elif actual['label'] is None:unknown_outcomes.append(key);c.issue(issues,'coverage',0,'OUTCOME_UNKNOWN')
            else:y=int(actual['label']==rule['positive_label'])
            if p is not None and y is not None:error=(p-y)**2;total+=error
            cases.append(dict(id=key,prediction_present=pred is not None,outcome_present=actual is not None,
                probability=pred['probability'] if pred else None,label=actual['label'] if actual else None,
                squared_error=fraction(error) if error is not None else None))
        complete=not issues
        assessment=dict(cases=cases,cohort_cases=len(cohort),missing_predictions=missing_predictions,missing_outcomes=missing_outcomes,
            unknown_probabilities=unknown_probabilities,unknown_outcomes=unknown_outcomes,complete=complete)
        if complete:metrics=dict(cases=len(cohort),total_squared_error=fraction(total),mean_squared_error=fraction(total/len(cohort)))
    exposed={key:pin if qualified else None for key,pin in pins.items()}
    return dict(assessment=assessment,metrics=metrics,evaluation_sha256=c.pin(pins) if metrics is not None else None,**exposed),dict(rule=rule,cases=cases)
