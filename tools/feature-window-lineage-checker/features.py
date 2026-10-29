"""Check exact selected lag-window contributors, timing and as-of revision lineage."""
import toolkit as t
import temporal_core as c


def feature(row):
    t.fields(row,{'id','series','origin','target','step','lag_points','window_points','contributors'})
    t.identifier(row['id']); t.identifier(row['series']); origin=c.ordinal(row['origin']); target=c.ordinal(row['target'])
    step=t.integer(row['step'],10**6,1); t.require(target>origin and (target-origin)%step==0 and (target-origin)//step<=365,'FEATURE_TARGET_INVALID')
    lag=t.integer(row['lag_points'],1000); window=t.integer(row['window_points'],1000,1)
    t.require(origin-(lag+window-1)*step>=0,'FEATURE_WINDOW_BEFORE_ZERO')
    refs=row['contributors']; t.require(type(refs) is list and len(refs)<=1000,'CONTRIBUTOR_LIMIT')
    refs=[c.reference(ref) for ref in refs]; t.require(len({ref['id'] for ref in refs})==len(refs),'DUPLICATE_CONTRIBUTOR')
    return row['id'],dict(row,contributors=sorted(refs,key=lambda ref:ref['id']))


def check(raw):
    value=t.decode(raw); t.fields(value,{'format','observations','features'})
    t.require(value['format']=='outlands-feature-window-lineage-v1','FORMAT_INVALID')
    ids,periods,oc,issues=c.prepare(value['observations'])
    features,fc,other=c.rows(value['features'],feature,'features'); issues+=other
    t.require(sum(row['window_points'] for _,row in features.values())<=4096,'TOTAL_FEATURE_WINDOW_LIMIT')
    if not features: c.problem(issues,'features',0,'EMPTY_FEATURE_COHORT')
    lineage=[]
    for key,(index,row) in sorted(features.items()):
        try:
            end=row['origin']-row['lag_points']*row['step']; start=end-(row['window_points']-1)*row['step']
            expected=set(range(start,end+1,row['step'])); selected=[]; seen=set()
            for ref in row['contributors']:
                t.require(ref['id'] in ids,'CONTRIBUTOR_MISSING'); source=ids[ref['id']][1]
                t.require(source['sha256']==ref['sha256'],'CONTRIBUTOR_PIN_MISMATCH')
                t.require(source['series']==row['series'],'CONTRIBUTOR_SERIES_MISMATCH')
                t.require(source['period'] in expected,'CONTRIBUTOR_OUTSIDE_WINDOW')
                t.require(source['period'] not in seen,'DUPLICATE_CONTRIBUTOR_PERIOD'); seen.add(source['period'])
                t.require(source['available_at']<=row['origin'],'CONTRIBUTOR_AVAILABLE_AFTER_ORIGIN')
                current=c.latest(periods,row['series'],source['period'],row['origin'])
                t.require(source['id']==current['id'],'STALE_OBSERVATION_REVISION')
                selected.append(c.public_reference(source))
            t.require(seen==expected,'FEATURE_WINDOW_COVERAGE_MISMATCH')
            lineage.append(dict(id=key,series=row['series'],origin=row['origin'],target=row['target'],
                                start=start,end=end,contributors=sorted(selected,key=lambda source:source['period'])))
        except t.Rejected as error: c.problem(issues,'features',index,str(error))
    result=c.base(raw,'outlands-feature-window-lineage-review-v1',dict(observations=oc,features=fc),issues)
    result.update(lineage=lineage if not issues else None,feature_values_calculated=False,cutoff_inclusive=True)
    return result


def main(argv=None): return c.cli('Check pinned feature-window contributors and declared availability without calculating features.',check,argv)
if __name__=='__main__': raise SystemExit(main())
