"""Exact equality-join cardinalities using key frequencies, without materializing joins."""
from collections import Counter
import toolkit as t
import relational_core as c


def analyze(raw):
    value=t.decode(raw); t.fields(value,{'format','dataset','join'})
    t.require(value['format']=='outlands-join-cardinality-v1','FORMAT_INVALID')
    schema,tables,counts,issues=c.dataset(value['dataset']); specs={s['name']:s for s in schema['tables']}
    policy=value['join']; t.fields(policy,{'left_table','right_table','left_columns','right_columns','null_policy'})
    for field in ('left_table','right_table'):
        t.identifier(policy[field]); t.require(policy[field] in specs,'JOIN_TABLE_MISSING')
    left=specs[policy['left_table']]; right=specs[policy['right_table']]
    lc=c.names(policy['left_columns']); rc=c.names(policy['right_columns'])
    t.require(len(lc)==len(rc),'JOIN_KEY_ARITY')
    li=c.indices(left,lc); ri=c.indices(right,rc)
    t.require(all(left['columns'][a]['type']==right['columns'][b]['type'] for a,b in zip(li,ri)),'JOIN_TYPE_MISMATCH')
    t.require(policy['null_policy'] in ('never_match','match'),'NULL_POLICY_INVALID')
    def frequency(name,positions):
        return Counter(c.key(row,positions) for _,row in tables[name]
                       if policy['null_policy']=='match' or all(row[i] is not None for i in positions))
    summary=None
    if not issues:
        a=frequency(left['name'],li); b=frequency(right['name'],ri); shared=set(a)&set(b)
        pairs=sum(a[key]*b[key] for key in shared)
        unmatched_left=len(tables[left['name']])-sum(a[key] for key in shared)
        unmatched_right=len(tables[right['name']])-sum(b[key] for key in shared)
        shapes=Counter(('many' if a[key]>1 else 'one')+'_to_'+('many' if b[key]>1 else 'one') for key in shared)
        summary=dict(left_rows=len(tables[left['name']]),right_rows=len(tables[right['name']]),matched_key_groups=len(shared),
             unmatched_left_rows=unmatched_left,unmatched_right_rows=unmatched_right,inner_rows=pairs,
             left_outer_rows=pairs+unmatched_left,right_outer_rows=pairs+unmatched_right,
             full_outer_rows=pairs+unmatched_left+unmatched_right,
             key_group_shapes={key:shapes[key] for key in ('one_to_one','one_to_many','many_to_one','many_to_many')},
             max_matches_per_left_row=max((b[key] for key in shared),default=0),
             max_matches_per_right_row=max((a[key] for key in shared),default=0))
    result=c.base(raw,'outlands-join-cardinality-review-v1',counts,issues)
    result.update(summary=summary,join_policy=policy,join_policy_sha256=t.digest(t.encode(policy)),
                  join_materialized=False,database_plan_verified=False,key_constraints_evaluated=False)
    return result


def main(argv=None): return c.cli('Count supplied equality-join cardinalities without SQL or joined-row output.',analyze,argv)
if __name__=='__main__': raise SystemExit(main())
