"""Check caller-declared model capabilities without loading or probing a model."""
import toolkit as t
import decision_core as c
import routing_core as r

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','models'})
    t.require(value['format']=='outlands-model-capability-v1','FORMAT_INVALID')
    counts={};issues=[];catalog=r.collect(value['models'],r.model,'models',counts,issues);qualified=not issues;assessment=None
    if qualified:
        outcomes=[]
        for key,(position,row) in sorted(catalog.items()):
            failures=r.model_failures(row)
            for code in failures:c.issue(issues,'models',position,code)
            outcomes.append(dict(id=key,revision=row['revision'],model_sha256=c.pin(row),consistent=not failures,failed_criteria=failures))
        assessment=dict(models=outcomes,consistent_models=sum(row['consistent'] for row in outcomes))
    return r.output(raw,'outlands-model-capability-report-v1',counts,issues,assessment=assessment,models_sha256=c.cohort_pin(catalog) if qualified else None)

def main(argv=None):return c.cli('Review declared model capabilities; no model loading or provider access.',check,argv)
if __name__=='__main__':raise SystemExit(main())
