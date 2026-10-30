"""Apply caller-declared minimum/target/multiple/cap rules without procurement."""
import toolkit as t
import decision_core as c
import stock_core as r

def position(row):
    key,out=c.record(row,{'id','revision','item','unit','inventory_position','as_of'},('id','item','unit'),('revision',));t.integer(row['inventory_position'],10**15,-10**15);t.integer(row['as_of']);return key,out

def policy(row):
    key,out=c.record(row,{'id','revision','position','position_revision','position_sha256','minimum','target','order_multiple','maximum_proposal'},('id','position'),('revision','position_revision'));t.sha(row['position_sha256'])
    for field in ('minimum','target','maximum_proposal'):t.integer(row[field],10**12)
    t.integer(row['order_multiple'],10**12,1);t.require(row['minimum']<=row['target'],'POLICY_TARGET_INVALID');return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','positions','policies','as_of'});t.require(v['format']=='outlands-replenishment-proposal-v1','FORMAT_INVALID');t.integer(v['as_of'])
    counts={};issues=[];positions=r.collect(v['positions'],position,'positions',counts,issues);policies=r.collect(v['policies'],policy,'policies',counts,issues,False)
    r.slots(policies,lambda row:row['position'],'policies',issues)
    for number,row in policies.values():r.reference(row,'position',positions,'policies',number,issues)
    qualified=not issues;assessment=None
    if qualified:
        selected={row['position']:row for _,row in policies.values()};out=[]
        for key,(number,row) in sorted(positions.items()):
            rule=selected.get(key);current=row['as_of']==v['as_of'];triggered=needed=rounded=proposed=None;codes=[]
            if rule is None:codes.append('POLICY_MISSING')
            if not current:codes.append('POSITION_SNAPSHOT_AS_OF_MISMATCH')
            if current and rule:
                triggered=row['inventory_position']<rule['minimum'];needed=rule['target']-row['inventory_position'] if triggered else 0
                rounded=((needed+rule['order_multiple']-1)//rule['order_multiple'])*rule['order_multiple']
                if rounded>rule['maximum_proposal']:codes.append('PROPOSAL_CAP_EXCEEDED')
                else:proposed=rounded
            for code in codes:c.issue(issues,'positions',number,code)
            out.append(dict(id=key,policy_id=rule['id'] if rule else None,triggered=triggered,required_unrounded=needed,required_order_quantity=rounded,proposed_quantity=proposed,failed_criteria=codes))
        assessment=dict(positions=out)
    return r.output(raw,'outlands-replenishment-proposal-report-v1',counts,issues,qualified,assessment,dict(positions=positions,policies=policies),dict(as_of=v['as_of']))

def main(argv=None):return c.cli('Plan declared replenishment quantities; no purchasing or supplier selection.',check,argv)
if __name__=='__main__':raise SystemExit(main())
