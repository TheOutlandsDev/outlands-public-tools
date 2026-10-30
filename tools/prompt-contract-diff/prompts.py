"""Compare a narrow declared prompt/output interface without rendering or inference."""
import re
import toolkit as t
import decision_core as c

PLACEHOLDER=re.compile(r'\{\{([a-z][a-z0-9_-]{0,47})\}\}')

def contract(value):
    _,out=c.record(value,{'id','revision','messages','variables','output_contract'},('id',),('revision',))
    variables=c.tags(value['variables']);messages=value['messages']
    t.require(type(messages) is list and 1<=len(messages)<=16,'MESSAGE_LIMIT')
    used=set();seen=set();normalized=[]
    for row in messages:
        t.fields(row,{'id','role','template'});t.identifier(row['id'])
        t.require(row['id'] not in seen,'MESSAGE_ID_DUPLICATE');seen.add(row['id'])
        t.require(row['role'] in ('system','user','assistant'),'MESSAGE_ROLE_INVALID')
        t.require(type(row['template']) is str and len(row['template'])<=4096,'TEMPLATE_INVALID')
        rest=PLACEHOLDER.sub('',row['template']);t.require('{{' not in rest and '}}' not in rest,'PLACEHOLDER_INVALID')
        used.update(PLACEHOLDER.findall(row['template']));normalized.append(dict(row))
    t.require(used==set(variables),'VARIABLE_DECLARATION_MISMATCH')
    output=value['output_contract'];t.fields(output,{'taxonomy','fields'});tax=c.taxonomy(output['taxonomy'])
    fields=output['fields'];t.require(type(fields) is list and 1<=len(fields)<=16,'OUTPUT_FIELD_LIMIT')
    seen=set();normalized_fields=[];label_fields=0
    for row in fields:
        t.fields(row,{'id','type','required'});t.identifier(row['id'])
        t.require(row['id'] not in seen,'OUTPUT_FIELD_DUPLICATE');seen.add(row['id'])
        t.require(row['type'] in ('label','text','integer','boolean') and type(row['required']) is bool,'OUTPUT_FIELD_INVALID')
        if row['type']=='label':label_fields+=1;t.require(row['required'],'LABEL_FIELD_MUST_BE_REQUIRED')
        normalized_fields.append(dict(row))
    t.require(label_fields==1,'EXACTLY_ONE_LABEL_FIELD_REQUIRED')
    out.update(messages=normalized,variables=variables,output_contract=dict(taxonomy=tax,fields=sorted(normalized_fields,key=lambda row:row['id'])))
    return out

def check(raw):
    value=t.decode(raw);t.fields(value,{'format','before','after'});t.require(value['format']=='outlands-prompt-contract-diff-v1','FORMAT_INVALID')
    before=contract(value['before']);after=contract(value['after']);issues=[];changes=None
    a=before['output_contract']['taxonomy'];b=after['output_contract']['taxonomy']
    if before['id']!=after['id']:c.issue(issues,'contracts',0,'PROMPT_ID_MISMATCH')
    if after['revision']<before['revision']:c.issue(issues,'contracts',0,'PROMPT_REVISION_REGRESSION')
    if a['id']!=b['id']:c.issue(issues,'contracts',0,'TAXONOMY_ID_MISMATCH')
    if b['revision']<a['revision']:c.issue(issues,'contracts',0,'TAXONOMY_REVISION_REGRESSION')
    if a['labels']!=b['labels'] and b['revision']<=a['revision']:c.issue(issues,'contracts',0,'TAXONOMY_CHANGE_NEEDS_REVISION')
    semantic={k:v for k,v in before.items() if k!='revision'}!={k:v for k,v in after.items() if k!='revision'}
    if semantic and after['revision']<=before['revision']:c.issue(issues,'contracts',0,'PROMPT_CHANGE_NEEDS_REVISION')
    if not issues:
        old={f['id']:f for f in before['output_contract']['fields']};new={f['id']:f for f in after['output_contract']['fields']}
        changes=dict(messages_changed=before['messages']!=after['messages'],message_order_changed=[r['id'] for r in before['messages']]!=[r['id'] for r in after['messages']],
            variables_added=sorted(set(after['variables'])-set(before['variables'])),variables_removed=sorted(set(before['variables'])-set(after['variables'])),
            fields_added=sorted(set(new)-set(old)),fields_removed=sorted(set(old)-set(new)),fields_changed=sorted(k for k in set(old)&set(new) if old[k]!=new[k]),
            taxonomy_changed=a!=b,version_only=not semantic and before['revision']!=after['revision'])
        if semantic:c.issue(issues,'contracts',0,'PROMPT_CONTRACT_CHANGED')
    result=c.base(raw,'outlands-prompt-contract-review-v1',{},issues)
    result.update(before_sha256=c.pin(before),after_sha256=c.pin(after),before_taxonomy_sha256=c.pin(a),after_taxonomy_sha256=c.pin(b),changes=changes,
                  model_behavior_evaluated=False,prompt_rendered=False,inference_performed=False)
    return result

def main(argv=None):return c.cli('Compare supplied prompt contracts; no rendering or model calls.',check,argv)
if __name__=='__main__':raise SystemExit(main())
