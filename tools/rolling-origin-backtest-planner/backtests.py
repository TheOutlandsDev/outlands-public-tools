"""Plan bounded regular-grid rolling origins and full multi-horizon folds, offline."""
import toolkit as t
import temporal_core as c


def plan(raw):
    value=t.decode(raw); t.fields(value,{'format','series','grid','training','horizons','stride'})
    t.require(value['format']=='outlands-rolling-origin-plan-v1','FORMAT_INVALID'); t.identifier(value['series'])
    grid,n=c.grid(value['grid']); training=value['training']; t.fields(training,{'min_points','max_points','gap_points'})
    minimum=t.integer(training['min_points'],1000,1); maximum=training['max_points']
    if maximum is not None: t.integer(maximum,1000,minimum)
    gap=t.integer(training['gap_points'],1000); stride=t.integer(value['stride'],1000,1)
    horizons=value['horizons']; t.require(type(horizons) is list and 1<=len(horizons)<=16,'HORIZON_LIMIT')
    for h in horizons: t.integer(h,365,1)
    t.require(len(set(horizons))==len(horizons),'DUPLICATE_HORIZON'); horizons=sorted(horizons)
    origins=list(range(minimum-1+gap,n-max(horizons),stride))
    t.require(len(origins)*len(horizons)<=4096,'EVALUATION_PAIR_LIMIT')
    issues=[]; folds=[]
    if not origins: c.problem(issues,'plan',0,'NO_EVALUATION_FOLDS')
    def period(index): return grid['start']+index*grid['step']
    for number,origin in enumerate(origins,1):
        end=origin-gap; start=0 if maximum is None else max(0,end-maximum+1)
        folds.append(dict(fold=number,series=value['series'],origin=period(origin),
                          training_start=period(start),training_end=period(end),training_points=end-start+1,
                          excluded_gap_points=gap,targets=[dict(horizon=h,period=period(origin+h)) for h in horizons]))
    result=c.base(raw,'outlands-rolling-origin-backtest-plan-v1',dict(grid_points=n,folds=len(folds),evaluation_pairs=len(folds)*len(horizons)),issues)
    result.update(plan=folds if not issues else None,grid=grid,horizons=horizons,observations_verified=False,
                  target_updates_plan_only=True,forecasts_generated=False)
    return result


def main(argv=None): return c.cli('Plan explicit rolling-origin folds without model training or forecast generation.',plan,argv)
if __name__=='__main__': raise SystemExit(main())
