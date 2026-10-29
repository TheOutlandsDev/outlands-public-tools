"""Describe coverage/width of supplied intervals; do not fit or certify intervals."""
from collections import defaultdict
from fractions import Fraction
import toolkit as t
import metrics_core as c


def prediction(row):
    record=c.forecast_fields(row,('lower','upper'))
    t.require(c.number(record['lower'])<=c.number(record['upper']),'INTERVAL_ORDER_INVALID')
    return record['id'],record


def summary(rows,nominal):
    if not rows: return None
    inside=below=above=0; width=distance=Fraction()
    for row,actual in rows:
        lower,upper=c.number(row['lower']),c.number(row['upper'])
        width+=upper-lower
        if actual<lower: below+=1; distance+=lower-actual
        elif actual>upper: above+=1; distance+=actual-upper
        else: inside+=1
    count=len(rows); coverage=Fraction(inside,count)
    return dict(count=count,covered=inside,below=below,above=above,coverage=c.ratio(coverage),
                nominal_coverage=c.ratio(nominal),coverage_minus_nominal=c.ratio(coverage-nominal),
                mean_width=c.ratio(width/count),mean_outside_distance=c.ratio(distance/count))


def analyze(raw):
    value=t.decode(raw); t.fields(value,{'format','nominal_coverage','intervals','outcomes'})
    t.require(value['format']=='outlands-interval-coverage-v1','FORMAT_INVALID')
    nominal=c.number(value['nominal_coverage']); t.require(0<nominal<1,'NOMINAL_COVERAGE_INVALID')
    matched,counts,issues=c.pairs(value['intervals'],value['outcomes'],prediction)
    if not matched and not issues: issues.append(dict(side='cohort',row=0,code='EMPTY_COHORT'))
    metrics=None; horizons=[]
    if not issues:
        groups=defaultdict(list)
        for row,actual in matched: groups[row['target']-row['origin']].append((row,actual))
        metrics=summary(matched,nominal)
        horizons=[dict(horizon=h,metrics=summary(groups[h],nominal)) for h in sorted(groups)]
    return dict(status='PASS' if not issues else 'REVIEW_REQUIRED',format='outlands-interval-coverage-review-v1',
                input_sha256=t.digest(raw),counts=counts,issues=issues,metrics=metrics,by_horizon=horizons,
                cohort_complete=not issues,calibration_verified=False,independent_coverage_guarantee=False,
                source_authority_verified=False,target_changes_performed=False)


def main(argv=None): return c.cli('Check declared interval coverage; never fit, widen or certify intervals.',analyze,argv)
if __name__=='__main__': raise SystemExit(main())
