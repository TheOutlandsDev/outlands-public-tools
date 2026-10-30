"""Check explicit cache key material and conflicting reuse without reading a cache."""
from collections import defaultdict
import toolkit as t
import decision_core as c
import cache_core as r

def contract(value):
    _,out=c.record(value,{'id','revision','namespace','key_version','dependencies'},('id','namespace'),('revision','key_version'))
    out['dependencies']=c.tags(value['dependencies'],1);return out

def entry(row,required):
    key,out=c.record(row,{'id','contract_sha256','inputs','key_sha256','content_sha256'},('id',))
    for field in ('contract_sha256','key_sha256','content_sha256'):t.sha(row[field])
    out['inputs']=r.inputs(row['inputs']);t.require({p['id'] for p in out['inputs']}<=set(required),'DEPENDENCY_UNKNOWN');return key,out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','contract','entries'})
    t.require(value['format']=='outlands-cache-key-v1','FORMAT_INVALID')
    rule=contract(value['contract']);counts={};issues=[]
    entries=r.collect(value['entries'],lambda row:entry(row,rule['dependencies']),'entries',counts,issues)
    rule_pin=c.pin(rule)
    for position,row in entries.values():
        if row['contract_sha256']!=rule_pin:c.issue(issues,'entries',position,'CONTRACT_PIN_MISMATCH')
    qualified=not issues;assessment=None;all_valid=False
    if qualified:
        groups=defaultdict(list);failures={};expected={};missing={}
        for key,(position,row) in sorted(entries.items()):
            absent=sorted(set(rule['dependencies'])-{r['id'] for r in row['inputs']});missing[key]=absent
            material=dict(contract_sha256=rule_pin,inputs=row['inputs']);expected[key]=c.pin(material) if not absent else None
            failed=[]
            if absent:failed.append('DEPENDENCIES_MISSING')
            elif row['key_sha256']!=expected[key]:failed.append('KEY_DERIVATION_MISMATCH')
            failures[key]=failed;groups[row['key_sha256']].append((key,row,material))
        group_reports=[]
        for digest,members in sorted(groups.items()):
            bindings={c.pin(material) for _,_,material in members};contents={row['content_sha256'] for _,row,_ in members};codes=[]
            if len(bindings)>1:codes.append('KEY_INPUT_BINDING_CONFLICT')
            if len(contents)>1:codes.append('KEY_CONTENT_BINDING_CONFLICT')
            for key,_,_ in members:failures[key].extend(codes)
            group_reports.append(dict(key_sha256=digest,entry_ids=[key for key,_,_ in members],input_bindings=len(bindings),content_bindings=len(contents),consistent=not codes))
        outcomes=[]
        for key,(position,row) in sorted(entries.items()):
            codes=sorted(set(failures[key]))
            for code in codes:c.issue(issues,'entries',position,code)
            outcomes.append(dict(id=key,expected_key_sha256=expected[key],missing_dependencies=missing[key],valid=not codes,failed_criteria=codes))
        all_valid=all(row['valid'] for row in outcomes)
        assessment=dict(entries=outcomes,key_groups=group_reports,unique_keys=len(groups),all_bindings_valid=all_valid)
    return r.output(raw,'outlands-cache-key-report-v1',counts,issues,assessment=assessment,
        contract_sha256=rule_pin if qualified else None,entries_sha256=c.cohort_pin(entries) if qualified else None,
        qualified_entries_sha256=c.cohort_pin(entries) if all_valid else None)

def main(argv=None):return c.cli('Check declared cache key contracts; no cache access or mutation.',check,argv)
if __name__=='__main__':raise SystemExit(main())
