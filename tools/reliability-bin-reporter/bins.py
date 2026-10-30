"""Describe fixed-bin probability/outcome differences without fitting or calibration claims."""
from fractions import Fraction
import toolkit as t
import decision_core as c
import probability_core as p

def bin_row(row):
    key,out=c.record(row,{'id','lower','upper'},('id',))
    for field in ('lower','upper'):_,out[field]=c.decimal(row[field])
    return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','contract','cohort','predictions','outcomes','bins'})
    t.require(value['format']=='outlands-reliability-bins-v1','FORMAT_INVALID')
    counts={};issues=[];evaluation,state=p.evaluation(value,counts,issues)
    t.require(type(value['bins']) is list and len(value['bins'])<=32,'BIN_LIMIT')
    initial=len(issues);bins=p.collect(value['bins'],bin_row,'bins',counts,issues)
    bins_structural=len(issues)==initial;bin_assessment=None;metrics=None;report_pin=None
    if bins_structural:
        ordered=sorted((row for _,row in bins.values()),key=lambda r:(c.decimal(r['lower'])[0],c.decimal(r['upper'])[0],r['id']))
        widths_valid=all(c.decimal(r['lower'])[0]<c.decimal(r['upper'])[0] for r in ordered)
        gaps=[];overlaps=[]
        if not widths_valid:c.issue(issues,'bins',0,'BIN_WIDTH_INVALID')
        else:
            cursor=Fraction(0);owner=None
            for row in ordered:
                lower,upper=c.decimal(row['lower'])[0],c.decimal(row['upper'])[0]
                if lower>cursor:gaps.append(dict(lower=p.fraction(cursor),upper=p.fraction(lower)))
                elif lower<cursor:overlaps.append(dict(left=owner,right=row['id']))
                if upper>cursor:cursor=upper;owner=row['id']
            if cursor<1:gaps.append(dict(lower=p.fraction(cursor),upper=p.fraction(1)))
            if gaps:c.issue(issues,'bins',0,'BIN_DOMAIN_GAP')
            if overlaps:c.issue(issues,'bins',0,'BIN_OVERLAP')
        valid=widths_valid and not gaps and not overlaps
        bin_assessment=dict(ordered_bins=ordered,gaps=gaps if widths_valid else None,overlaps=overlaps if widths_valid else None,valid_partition=valid)
        if valid and evaluation['metrics'] is not None:
            groups={r['id']:[] for r in ordered}
            for row in state['cases']:
                probability=c.decimal(row['probability'])[0]
                matches=[b for b in ordered if c.decimal(b['lower'])[0]<=probability and (probability<c.decimal(b['upper'])[0] or probability==1 and b['upper']=='1')]
                t.require(len(matches)==1,'BIN_ACCOUNTING_FAILED');groups[matches[0]['id']].append(row)
            total=len(state['cases']);outcomes=[];weighted=Fraction(0)
            for row in ordered:
                selected=groups[row['id']];n=len(selected);positive=sum(r['label']==state['rule']['positive_label'] for r in selected)
                mean=sum((c.decimal(r['probability'])[0] for r in selected),Fraction(0))/n if n else None
                actual=Fraction(positive,n) if n else None;gap=actual-mean if n else None
                if n:weighted+=Fraction(n,total)*abs(gap)
                outcomes.append(dict(id=row['id'],cases=n,case_ids=[r['id'] for r in selected],positives=positive,
                    mean_probability=p.fraction(mean) if n else None,positive_fraction=p.fraction(actual) if n else None,
                    signed_gap=p.fraction(gap) if n else None,absolute_gap=p.fraction(abs(gap)) if n else None))
            t.require(sum(row['cases'] for row in outcomes)==total,'BIN_ACCOUNTING_FAILED')
            metrics=dict(cohort_cases=total,bins=outcomes,empty_bins=[r['id'] for r in outcomes if not r['cases']],weighted_absolute_bin_gap=p.fraction(weighted))
            report_pin=c.pin(dict(evaluation_sha256=evaluation['evaluation_sha256'],bins_sha256=c.cohort_pin(bins)))
    # Binary scope pins remain independent; a malformed bin contract has no bin pin.
    exposed={key:evaluation[key] for key in ('contract_sha256','cohort_sha256','predictions_sha256','outcomes_sha256')}
    return p.output(raw,'outlands-reliability-bin-report-v1',counts,issues,assessment=evaluation['assessment'],bin_assessment=bin_assessment,
        metrics=metrics,bins_sha256=c.cohort_pin(bins) if bins_structural else None,report_sha256=report_pin,**exposed)

def main(argv=None):return c.cli('Describe explicit fixed-bin differences; no fitting or calibration proof.',check,argv)
if __name__=='__main__':raise SystemExit(main())
