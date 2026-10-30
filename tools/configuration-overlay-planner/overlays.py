"""Plan explicitly ordered metadata-only overlays without producing or applying setting values."""
import toolkit as t
import decision_core as c
import config_core as r

def layer(row):
    key,out=c.record(row,{'id','revision','ordinal','contract_sha256'},('id',),('revision',));t.integer(row['ordinal'],1000,1);t.sha(row['contract_sha256']);return key,out

def change(row):
    key,out=c.record(row,{'id','layer','layer_revision','layer_sha256','key','action','value_type','value_sha256','allow_override'},('id','layer','key'),('layer_revision',))
    t.sha(row['layer_sha256']);t.require(row['action'] in ('set','delete'),'ACTION_INVALID');t.require(type(row['allow_override']) is bool,'OVERRIDE_FLAG_INVALID')
    if row['action']=='set':t.require(row['value_type'] in r.TYPES,'VALUE_TYPE_INVALID');t.sha(row['value_sha256'])
    else:t.require(row['value_type'] is None and row['value_sha256'] is None and row['allow_override'] is False,'DELETE_PAYLOAD_INVALID')
    return key,out

def check(raw):
    v=t.decode(raw);t.fields(v,{'format','contract','layers','changes'});t.require(v['format']=='outlands-config-overlays-v1','FORMAT_INVALID')
    counts={};issues=[];contract=r.contract(v['contract'],'contract',counts,issues);fields={row['id']:row for row in contract['fields']}
    layers=r.collect(v['layers'],layer,'layers',counts,issues);changes=r.collect(v['changes'],change,'changes',counts,issues,False)
    r.slots(layers,lambda row:row['ordinal'],'layers',issues);r.slots(changes,lambda row:(row['layer'],row['key']),'changes',issues)
    for expected,(position,row) in enumerate(sorted(layers.values(),key=lambda pair:pair[1]['ordinal']),1):
        if row['ordinal']!=expected:c.issue(issues,'layers',position,'LAYER_ORDINAL_GAP')
        if row['contract_sha256']!=c.pin(contract):c.issue(issues,'layers',position,'CONTRACT_PIN_MISMATCH')
    for position,row in changes.values():
        r.reference(row,'layer',layers,'changes',position,issues)
        if row['key'] not in fields:c.issue(issues,'changes',position,'KEY_UNDECLARED')
        elif row['action']=='set' and row['value_type']!=fields[row['key']]['type']:c.issue(issues,'changes',position,'VALUE_TYPE_MISMATCH')
    qualified=not issues;assessment=None;effective=None
    if qualified:
        present={};outcomes=[]
        for position,row in sorted(changes.values(),key=lambda pair:(layers[pair[1]['layer']][1]['ordinal'],pair[1]['key'])):
            key=row['key'];code=None
            if row['action']=='delete':
                if key not in present:code='DELETE_ABSENT_KEY'
                else:present.pop(key)
            elif key in present and not row['allow_override']:code='OVERRIDE_DENIED'
            else:present[key]=row
            if code:c.issue(issues,'changes',position,code)
            outcomes.append(dict(id=row['id'],key=key,layer=row['layer'],action=row['action'],applied=code is None,failed_criterion=code))
        missing=sorted(key for key,field in fields.items() if field['required'] and key not in present)
        for key in missing:c.issue(issues,'contract',0,'REQUIRED_KEY_MISSING')
        final=None
        if not issues:
            final=[dict(key=key,value_type=present[key]['value_type'],source_layer=present[key]['layer'],source_change=present[key]['id']) for key in sorted(present)]
            effective=c.pin(dict(contract_sha256=c.pin(contract),present=[dict(key=key,value_type=present[key]['value_type'],value_sha256=present[key]['value_sha256']) for key in sorted(present)]))
        assessment=dict(changes=outcomes,missing_required_keys=missing,effective_fields=final,defaults_inserted=False)
    return r.output(raw,'outlands-config-overlays-report-v1',counts,issues,qualified,assessment,dict(contract_sha256=c.pin(contract),layers_sha256=c.cohort_pin(layers),changes_sha256=c.cohort_pin(changes)),effective_configuration_sha256=effective)

def main(argv=None):return c.cli('Plan pinned configuration overlays; no raw values, defaults or settings writes.',check,argv)
if __name__=='__main__':raise SystemExit(main())
