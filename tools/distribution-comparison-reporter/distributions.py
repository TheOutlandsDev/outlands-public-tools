"""Compare explicit fixed-bin marginal distributions with complete bucket accounting."""
from fractions import Fraction
import toolkit as t
import metrics_core as c


def policy(fields):
    t.require(type(fields) is list and 1<=len(fields)<=16,'FIELD_LIMIT')
    seen=set(); normalized=[]
    for field in fields:
        t.require(type(field) is dict and field.get('kind') in ('numeric','categorical'),'FIELD_KIND_INVALID')
        kind=field['kind']; key='boundaries' if kind=='numeric' else 'categories'
        t.fields(field,{'name','kind',key}); name=t.identifier(field['name'])
        t.require(name not in seen,'DUPLICATE_FIELD'); seen.add(name)
        items=field[key]
        t.require(type(items) is list and 1<=len(items)<=33,'BUCKET_LIMIT')
        if kind=='numeric':
            t.require(len(items)>=2,'BUCKET_LIMIT')
            values=[c.number(v) for v in items]
            t.require(all(a<b for a,b in zip(values,values[1:])),'BOUNDARY_ORDER_INVALID')
            normalized.append(dict(name=name,kind=kind,boundaries=[c.canonical(v) for v in items]))
        else:
            t.require(len(items)<=32,'BUCKET_LIMIT')
            for item in items: t.identifier(item)
            t.require(len(set(items))==len(items),'DUPLICATE_CATEGORY')
            normalized.append(dict(name=name,kind=kind,categories=list(items)))
    return normalized


def record(row,fields):
    t.fields(row,{'id','values'}); key=t.identifier(row['id'])
    t.fields(row['values'],{f['name'] for f in fields}); values={}
    for field in fields:
        value=row['values'][field['name']]
        if value is not None:
            if field['kind']=='numeric': c.number(value); value=c.canonical(value)
            else: t.identifier(value)
        values[field['name']]=value
    return key,dict(id=key,values=values)


def buckets(field,records):
    if field['kind']=='numeric':
        edges=[c.number(v) for v in field['boundaries']]
        names=['below']+['bin-'+str(i+1) for i in range(len(edges)-1)]+['above','missing']
    else:
        names=['category-'+str(i+1) for i in range(len(field['categories']))]+['unknown','missing']
    counts=dict.fromkeys(names,0)
    for _,row in records.values():
        value=row['values'][field['name']]
        if value is None: key='missing'
        elif field['kind']=='categorical':
            key='category-'+str(field['categories'].index(value)+1) if value in field['categories'] else 'unknown'
        else:
            number=c.number(value)
            if number<edges[0]: key='below'
            elif number>edges[-1]: key='above'
            else:
                index=next((i for i in range(len(edges)-1) if number<edges[i+1]),len(edges)-2)
                key='bin-'+str(index+1)
        counts[key]+=1
    t.require(sum(counts.values())==len(records),'BUCKET_ACCOUNTING_FAILED')
    return counts


def compare(raw):
    value=t.decode(raw); t.fields(value,{'format','fields','reference','current'})
    t.require(value['format']=='outlands-distribution-comparison-v1','FORMAT_INVALID')
    fields=policy(value['fields'])
    left,lc,issues=c.rows(value['reference'],lambda row:record(row,fields),'reference')
    right,rc,other=c.rows(value['current'],lambda row:record(row,fields),'current'); issues+=other
    if not left or not right: issues.append(dict(side='cohort',row=0,code='EMPTY_COMPARISON'))
    comparisons=[]
    if not issues:
        for field in fields:
            a,b=buckets(field,left),buckets(field,right)
            rows=[]; distance=Fraction()
            for key in a:
                p,q=Fraction(a[key],len(left)),Fraction(b[key],len(right)); distance+=abs(q-p)
                rows.append(dict(bucket=key,reference_count=a[key],current_count=b[key],
                                 reference_share=c.ratio(p),current_share=c.ratio(q),delta=c.ratio(q-p)))
            comparisons.append(dict(field=field,buckets=rows,total_variation_distance=c.ratio(distance/2)))
    return dict(status='PASS' if not issues else 'REVIEW_REQUIRED',format='outlands-distribution-review-v1',
                input_sha256=t.digest(raw),policy_sha256=t.digest(t.encode(fields)),
                counts=dict(reference=lc,current=rc),issues=issues,comparisons=comparisons,
                drift_conclusion_verified=False,joint_distribution_compared=False,target_changes_performed=False)


def main(argv=None): return c.cli('Compare supplied fixed-bin marginals; no fitted bins, drift threshold or action.',compare,argv)
if __name__=='__main__': raise SystemExit(main())
