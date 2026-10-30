"""Compare compatible declared results, retaining additions/removals and incompleteness."""
import toolkit as t
import decision_core as c
import test_core as r

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','baseline','candidate'});t.require(v['format']=='outlands-regression-comparison-v1','FORMAT_INVALID')
    counts={};issues=[];left=r.bundle(v['baseline'],counts,issues,'baseline_');right=r.bundle(v['candidate'],counts,issues,'candidate_')
    if left['run']['id']==right['run']['id']:c.issue(issues,'runs',0,'RUN_ID_REUSED')
    qualified=not issues;assessment=None
    if qualified:
        l={row['id']:row for row in r.evaluate(left)};rr={row['id']:row for row in r.evaluate(right)};out=[]
        for key in sorted(set(l)|set(rr)):
            a=l.get(key);b=rr.get(key)
            if a is None:state='added'
            elif b is None:state='removed'
            elif a['case_sha256']!=b['case_sha256']:state='incomparable_contract'
            elif a['matched'] is None or b['matched'] is None:state='incomplete_comparison'
            elif a['matched'] and b['matched']:state='unchanged_match'
            elif a['matched']:state='regression'
            elif b['matched']:state='improvement'
            else:state='persisting_mismatch'
            if state not in ('unchanged_match','improvement'):c.issue(issues,'comparison',0,state.upper())
            out.append(dict(id=key,state=state,baseline=a,candidate=b))
        assessment=dict(cases=out,classification_counts={state:sum(row['state']==state for row in out) for state in ('added','removed','incomparable_contract','incomplete_comparison','unchanged_match','regression','improvement','persisting_mismatch')},no_declared_regressions_or_gaps=not issues)
    pins={side+'_'+key:value for side,b in [('baseline',left),('candidate',right)] for key,value in r.bundle_pins(b).items()}
    return r.output(raw,'outlands-regression-comparison-report-v1',counts,issues,qualified,assessment,pins)

def main(argv=None):return c.cli('Compare declared baseline/candidate results; never execute or approve tests.',check,argv)
if __name__=='__main__':raise SystemExit(main())
