"""Describe exact ordinal-grid gaps and duplicates without filling observations."""
import toolkit as t
import temporal_core as c


def point(row):
    t.fields(row,{'series','period'}); t.identifier(row['series']); c.ordinal(row['period'])
    return (row['series'],row['period']),dict(row)


def check(raw):
    value=t.decode(raw); t.fields(value,{'format','grids','points'})
    t.require(value['format']=='outlands-time-series-grid-v1','FORMAT_INVALID')
    t.require(type(value['grids']) is list and 1<=len(value['grids'])<=16,'GRID_POLICY_LIMIT')
    policies={}; total=0
    for row in value['grids']:
        t.fields(row,{'series','start','end','step'}); t.identifier(row['series'])
        t.require(row['series'] not in policies,'DUPLICATE_GRID_POLICY')
        policy,count=c.grid({k:row[k] for k in ('start','end','step')}); total+=count
        t.require(total<=1000,'TOTAL_GRID_POINT_LIMIT'); policies[row['series']]=policy
    accepted,counts,issues=c.rows(value['points'],point,'points','DUPLICATE_PERIOD')
    selected={key:set() for key in policies}; outside={key:0 for key in policies}
    for index,row in accepted.values():
        series,period=row['series'],row['period']
        if series not in policies: c.problem(issues,'points',index,'SERIES_UNDECLARED'); continue
        policy=policies[series]
        if not policy['start']<=period<=policy['end'] or (period-policy['start'])%policy['step']:
            outside[series]+=1; c.problem(issues,'points',index,'PERIOD_OUTSIDE_GRID'); continue
        selected[series].add(period)
    coverage=[]
    for series,policy in sorted(policies.items()):
        expected=set(range(policy['start'],policy['end']+1,policy['step'])); missing=sorted(expected-selected[series])
        if missing: c.problem(issues,'grids',0,'GRID_GAPS',series=series)
        coverage.append(dict(series=series,expected_points=len(expected),observed_unique_points=len(selected[series]),
                             missing_periods=missing,outside_unique_points=outside[series]))
    result=c.base(raw,'outlands-time-series-grid-review-v1',dict(points=counts),issues)
    result.update(coverage=coverage if not counts['rejected_rows'] and not counts['conflict_rows'] else None,
                  coverage_complete=not issues,observations_filled=False)
    return result


def main(argv=None): return c.cli('Check declared ordinal time grids without filling or interpolating data.',check,argv)
if __name__=='__main__': raise SystemExit(main())
