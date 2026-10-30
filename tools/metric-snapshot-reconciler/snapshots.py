"""Reconcile one explicit metric snapshot per selected series/run, with exact arithmetic."""
import toolkit as t
import decision_core as c
import telemetry_core as r
def check(raw):
    v=t.decode(raw);t.fields(v,{'format','definitions','series','runs','points'});t.require(v['format']=='outlands-metric-snapshots-v1','FORMAT_INVALID');counts={};issues=[];scope=r.metric_context(v,counts,issues)
    return r.output(raw,'outlands-metric-snapshots-report-v1',counts,issues,scope['qualified'],scope['assessment'],{key+'_sha256':c.cohort_pin(scope[key]) for key in ('definitions','series','runs','points')})
def main(argv=None):return c.cli('Reconcile declared metric snapshots; no collectors, rate calculation or live clocks.',check,argv)
if __name__=='__main__':raise SystemExit(main())
