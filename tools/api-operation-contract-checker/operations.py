"""Check bounded operation contracts and ambiguous structured routes without running servers."""
import toolkit as t
import decision_core as c
import api_core as r
def check(raw):
    v=t.decode(raw);t.fields(v,{'format','operations'});t.require(v['format']=='outlands-api-operations-v1','FORMAT_INVALID');counts={};issues=[];operations=r.operation_scope(v['operations'],'operations',counts,issues);qualified=not issues;assessment=None
    if qualified:assessment=dict(operations=[dict(id=key,method=row['method'],route_segments=len(row['route']),request_fields=len(row['request_fields']),response_statuses=sorted(v['status'] for v in row['responses'])) for key,(_,row) in sorted(operations.items())],route_precedence_inferred=False)
    return r.output(raw,'outlands-api-operations-report-v1',counts,issues,qualified,assessment,dict(operations_sha256=c.cohort_pin(operations)))
def main(argv=None):return c.cli('Check structured API operation declarations; no endpoints, servers or network access.',check,argv)
if __name__=='__main__':raise SystemExit(main())
