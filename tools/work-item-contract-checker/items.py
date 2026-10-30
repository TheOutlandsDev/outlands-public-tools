"""Check explicitly declared work-item interfaces and metadata presence, never payload values."""
import toolkit as t
import decision_core as c
import worker_core as r

def handler(row):
    key,out=c.record(row,{'id','revision','kind','input_contract_sha256','result_contract_sha256','required_metadata'},('id','kind'),('revision',))
    t.sha(row['input_contract_sha256']);t.sha(row['result_contract_sha256']);out['required_metadata']=c.tags(row['required_metadata']);return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','handlers','items'});t.require(v['format']=='outlands-work-items-v1','FORMAT_INVALID');counts={};issues=[]
    handlers=r.collect(v['handlers'],handler,'handlers',counts,issues);items=r.collect(v['items'],r.item,'items',counts,issues)
    for position,row in items.values():
        selected=r.reference(row,'handler',handlers,'items',position,issues)
        if selected is not None and any(row[field]!=selected[field] for field in ('kind','input_contract_sha256','result_contract_sha256')):c.issue(issues,'items',position,'HANDLER_CONTRACT_MISMATCH')
    qualified=not issues;assessment=None
    if qualified:
        rows=[]
        for key,(position,row) in sorted(items.items()):
            missing=sorted(set(handlers[row['handler']][1]['required_metadata'])-set(row['metadata']))
            if missing:c.issue(issues,'items',position,'ITEM_METADATA_MISSING')
            rows.append(dict(id=key,handler_id=row['handler'],missing_metadata=missing,declared_metadata_complete=not missing))
        assessment=dict(items=rows,payload_values_validated=False,metadata_values_validated=False)
    return r.output(raw,'outlands-work-items-report-v1',counts,issues,qualified,assessment,dict(handlers_sha256=c.cohort_pin(handlers),items_sha256=c.cohort_pin(items)))

def main(argv=None):return c.cli('Check declared work-item interfaces; no payload reads or job execution.',check,argv)
if __name__=='__main__':raise SystemExit(main())
