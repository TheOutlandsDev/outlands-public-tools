"""Check exact declared metric kinds, labels, limits and explicit expected series."""
import toolkit as t
import decision_core as c
import telemetry_core as r
def check(raw):
    v=t.decode(raw);t.fields(v,{'format','definitions','series'});t.require(v['format']=='outlands-metric-definitions-v1','FORMAT_INVALID');counts={};issues=[];definitions,series=r.metric_contract(v,counts,issues);qualified=not issues;assessment=None
    if qualified:
        assessment=dict(definitions=[dict(id=key,kind=row['kind'],unit=row['unit'],declared_series_count=sum(s['metric']==key for _,s in series.values()),required_series_count=sum(s['metric']==key and s['required'] for _,s in series.values())) for key,(_,row) in sorted(definitions.items())],series=[dict(id=key,metric=row['metric'],label_keys=sorted(row['labels'])) for key,(_,row) in sorted(series.items())],unit_semantics_verified=False)
    return r.output(raw,'outlands-metric-definitions-report-v1',counts,issues,qualified,assessment,dict(definitions_sha256=c.cohort_pin(definitions),series_sha256=c.cohort_pin(series)))
def main(argv=None):return c.cli('Check declared metric definitions; no telemetry collection or instrumentation.',check,argv)
if __name__=='__main__':raise SystemExit(main())
