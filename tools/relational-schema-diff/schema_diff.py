"""Describe valid relational schema declarations without generating/applying DDL."""
import toolkit as t
import relational_core as c


def compare(raw):
    value=t.decode(raw); t.fields(value,{'format','before','after'})
    t.require(value['format']=='outlands-relational-schema-diff-v1','FORMAT_INVALID')
    before=c.schema(value['before']); after=c.schema(value['after'])
    left={s['name']:s for s in before['tables']}; right={s['name']:s for s in after['tables']}; changes=[]
    def add(table,code,column=None,constraint=None): changes.append(dict(table=table,column=column,constraint=constraint,code=code))
    for table in sorted(set(left)|set(right)):
        if table not in left: add(table,'TABLE_ADDED'); continue
        if table not in right: add(table,'TABLE_REMOVED'); continue
        a,b=left[table],right[table]; ac={col['name']:col for col in a['columns']}; bc={col['name']:col for col in b['columns']}
        for col in sorted(set(ac)|set(bc)):
            if col not in ac: add(table,'COLUMN_ADDED',col); continue
            if col not in bc: add(table,'COLUMN_REMOVED',col); continue
            for field,code in [('type','COLUMN_TYPE_CHANGED'),('nullable','COLUMN_NULLABILITY_CHANGED')]:
                if ac[col][field]!=bc[col][field]: add(table,code,col)
        if list(ac)!=list(bc): add(table,'COLUMN_ORDER_OR_MEMBERS_CHANGED')
        if a['primary_key']!=b['primary_key']: add(table,'PRIMARY_KEY_CHANGED')
        af={fk['name']:fk for fk in a['foreign_keys']}; bf={fk['name']:fk for fk in b['foreign_keys']}
        for name in sorted(set(af)|set(bf)):
            if name not in af: add(table,'FOREIGN_KEY_ADDED',constraint=name)
            elif name not in bf: add(table,'FOREIGN_KEY_REMOVED',constraint=name)
            elif t.encode(af[name])!=t.encode(bf[name]): add(table,'FOREIGN_KEY_CHANGED',constraint=name)
        if list(af)!=list(bf): add(table,'FOREIGN_KEY_ORDER_OR_MEMBERS_CHANGED')
    if list(left)!=list(right): add(None,'TABLE_ORDER_OR_MEMBERS_CHANGED')
    result=c.base(raw,'outlands-relational-schema-diff-review-v1',dict(before_tables=len(left),after_tables=len(right)),[])
    result.update(status='REVIEW_REQUIRED' if changes else 'PASS',changes=changes,before_schema_sha256=t.digest(t.encode(before)),
                  after_schema_sha256=t.digest(t.encode(after)),compatibility_verified=False,rename_inferred=False,ddl_generated=False)
    return result


def main(argv=None): return c.cli('Compare explicit relational schema declarations without SQL/DDL execution.',compare,argv)
if __name__=='__main__': raise SystemExit(main())
