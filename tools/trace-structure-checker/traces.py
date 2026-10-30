"""Check selected declared span graphs and explicit coverage without assuming serial execution."""
import toolkit as t
import decision_core as c
import telemetry_core as r
def check(raw):
    v=t.decode(raw);t.fields(v,{'format','runs','traces','spans'});t.require(v['format']=='outlands-trace-structure-v1','FORMAT_INVALID');counts={};issues=[];scope=r.trace_context(v,counts,issues)
    return r.output(raw,'outlands-trace-structure-report-v1',counts,issues,scope['qualified'],scope['assessment'],{key+'_sha256':c.cohort_pin(scope[key]) for key in ('runs','traces','spans')})
def main(argv=None):return c.cli('Check declared span structure; no tracing, service access or clock collection.',check,argv)
if __name__=='__main__':raise SystemExit(main())
