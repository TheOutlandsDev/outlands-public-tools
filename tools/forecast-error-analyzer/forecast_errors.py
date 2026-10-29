"""Match explicit forecasts/outcomes and report a complete, qualified error cohort."""
from collections import defaultdict
from fractions import Fraction
import toolkit as t
import metrics_core as c


def prediction(row):
    record=c.forecast_fields(row,('predicted',))
    # One explicitly selected revision per forecast ID; never guess the latest.
    return record['id'],record


def summary(errors):
    count=len(errors)
    if not count: return None
    mean_square=sum((v*v for v in errors),Fraction())/count
    return dict(count=count,mean_error=c.ratio(sum(errors,Fraction())/count),
                mae=c.ratio(sum((abs(v) for v in errors),Fraction())/count),mse=c.ratio(mean_square),
                rmse_approx=c.root_mean_square(mean_square))


def analyze(raw):
    value=t.decode(raw); t.fields(value,{'format','forecasts','outcomes'})
    t.require(value['format']=='outlands-forecast-errors-v1','FORMAT_INVALID')
    matched,counts,issues=c.pairs(value['forecasts'],value['outcomes'],prediction)
    if not matched and not issues: issues.append(dict(side='cohort',row=0,code='EMPTY_COHORT'))
    totals=None; horizons=[]
    if not issues:
        by_horizon=defaultdict(list)
        for row,actual in matched: by_horizon[row['target']-row['origin']].append(c.number(row['predicted'])-actual)
        totals=summary([c.number(row['predicted'])-actual for row,actual in matched])
        horizons=[dict(horizon=key,metrics=summary(by_horizon[key])) for key in sorted(by_horizon)]
    return dict(status='PASS' if not issues else 'REVIEW_REQUIRED',format='outlands-forecast-error-review-v1',
                input_sha256=t.digest(raw),counts=counts,issues=issues,metrics=totals,by_horizon=horizons,
                error_direction='PREDICTED_MINUS_OBSERVED',cohort_complete=not issues,
                source_authority_verified=False,forecast_timing_verified=False,target_changes_performed=False)


def main(argv=None): return c.cli('Analyze explicit forecasts/outcomes; incomplete cohorts withhold metrics.',analyze,argv)
if __name__=='__main__': raise SystemExit(main())
