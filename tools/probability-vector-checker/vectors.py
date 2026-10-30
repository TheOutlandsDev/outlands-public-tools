"""Check explicit class probabilities without normalization, inference or truth claims."""
from fractions import Fraction
import toolkit as t
import decision_core as c
import probability_core as p

def vector(row,labels):
    key,out=c.record(row,{'id','revision','model','model_revision','probabilities'},('id','model'),('revision','model_revision'))
    values=row['probabilities']
    if values is None:return key,out
    t.require(type(values) is list and len(values)<=32,'VECTOR_LIMIT')
    normalized=[];seen=set()
    for entry in values:
        t.fields(entry,{'label','value'});t.identifier(entry['label'])
        t.require(entry['label'] in labels,'LABEL_UNKNOWN');t.require(entry['label'] not in seen,'LABEL_AMBIGUOUS');seen.add(entry['label'])
        value=entry['value']
        if value is not None:_,value=c.decimal(value)
        normalized.append(dict(label=entry['label'],value=value))
    out['probabilities']=sorted(normalized,key=lambda r:r['label']);return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','taxonomy','cases'})
    t.require(value['format']=='outlands-probability-vector-v1','FORMAT_INVALID')
    taxonomy=c.taxonomy(value['taxonomy']);counts={};issues=[]
    cases=p.collect(value['cases'],lambda row:vector(row,taxonomy['labels']),'cases',counts,issues);qualified=not issues;assessment=None;all_valid=False
    if qualified:
        outcomes=[]
        for key,(position,row) in sorted(cases.items()):
            selected={r['label']:r['value'] for r in row['probabilities'] or []}
            missing=[label for label in taxonomy['labels'] if label not in selected or selected[label] is None]
            total=None if missing else sum((c.decimal(v)[0] for v in selected.values()),Fraction(0))
            failures=[]
            if missing:failures.append('PROBABILITIES_MISSING')
            elif total!=1:failures.append('PROBABILITY_SUM_NOT_ONE')
            for code in failures:c.issue(issues,'cases',position,code)
            outcomes.append(dict(id=key,valid=not failures,missing_labels=missing,probability_sum=p.fraction(total) if total is not None else None,
                vector_sha256=c.pin(row) if not failures else None,failed_criteria=failures))
        all_valid=all(row['valid'] for row in outcomes)
        assessment=dict(cases=outcomes,valid_cases=sum(row['valid'] for row in outcomes),all_vectors_valid=all_valid)
    return p.output(raw,'outlands-probability-vector-report-v1',counts,issues,assessment=assessment,
        taxonomy_sha256=c.pin(taxonomy) if qualified else None,cases_sha256=c.cohort_pin(cases) if qualified else None,
        qualified_cases_sha256=c.cohort_pin(cases) if all_valid else None,probabilities_renormalized=False)

def main(argv=None):return c.cli('Check declared class probabilities exactly; no normalization or inference.',check,argv)
if __name__=='__main__':raise SystemExit(main())
