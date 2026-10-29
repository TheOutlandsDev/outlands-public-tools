"""Check primary-key multiplicity and explicit foreign references in supplied rows."""
from collections import defaultdict
import toolkit as t
import relational_core as c


def check(raw):
    value=t.decode(raw); t.fields(value,{'format','dataset'})
    t.require(value['format']=='outlands-key-reference-check-v1','FORMAT_INVALID')
    schema,tables,counts,issues=c.dataset(value['dataset']); specs={s['name']:s for s in schema['tables']}
    checked=[]; constraint_count=0
    for name,spec in specs.items():
        groups=defaultdict(list); pk=spec['primary_key']; constraint_count+=bool(pk)+len(spec['foreign_keys'])
        if pk:
            positions=c.indices(spec,pk)
            for index,row in tables[name]: groups[c.key(row,positions)].append(index)
            for entries in groups.values():
                if len(entries)>1:
                    for index in entries: c.issue(issues,name,index,'DUPLICATE_PRIMARY_KEY','primary_key')
        foreign=[]
        for fk in spec['foreign_keys']:
            positions=c.indices(spec,fk['columns']); target_positions=c.indices(specs[fk['table']],fk['references'])
            target={c.key(row,target_positions) for _,row in tables[fk['table']]}; skipped=resolved=0
            for index,row in tables[name]:
                if any(row[p] is None for p in positions):
                    if fk['null_policy']=='skip_any': skipped+=1
                    else: c.issue(issues,name,index,'FOREIGN_KEY_NULL',fk['name'])
                elif c.key(row,positions) not in target: c.issue(issues,name,index,'FOREIGN_KEY_MISSING',fk['name'])
                else: resolved+=1
            foreign.append(dict(name=fk['name'],resolved_rows=resolved,skipped_null_rows=skipped))
        checked.append(dict(table=name,observed_rows=len(tables[name]),primary_key_checked=bool(pk),foreign_keys=foreign))
    if not constraint_count: c.issue(issues,'schema',0,'NO_KEY_CONSTRAINTS')
    result=c.base(raw,'outlands-key-reference-review-v1',counts,issues)
    result.update(summary=sorted(checked,key=lambda row:row['table']) if not issues else None,
                  schema_sha256=t.digest(t.encode(schema)),database_contents_verified=False,duplicate_rows_discarded=False)
    return result


def main(argv=None): return c.cli('Check explicit typed primary/foreign keys without importing or repairing records.',check,argv)
if __name__=='__main__': raise SystemExit(main())
