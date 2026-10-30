"""Bounded structured API exchange declarations; no wire parsing, authentication or networking."""
import re
import toolkit as t
import decision_core as c

METHODS=('GET','HEAD','POST','PUT','PATCH','DELETE','OPTIONS')
def text(value):t.require(type(value) is str and len(value)<=256,'TEXT_INVALID');return value
def header_name(value):t.identifier(value);t.require(value.startswith('x-') and len(value)>2,'CUSTOM_HEADER_REQUIRED')
def header_value(value):text(value);t.require(all(32<=ord(ch)<=126 for ch in value),'HEADER_VALUE_INVALID')
def media(value):t.require(value in (None,'application/json'),'MEDIA_TYPE_UNSUPPORTED')
def scalar(value):
    if type(value) is bool:return
    if type(value) is int:t.integer(value,10**12,-10**12);return
    text(value)
def mapping(value,location):
    t.require(type(value) is dict and len(value)<=32,'MAP_LIMIT')
    for key,item in value.items():
        if location=='header':header_name(key);header_value(item)
        else:
            t.identifier(key)
            if location=='query':text(item)
            else:scalar(item)
    return dict(value)
def body(value):return None if value is None else mapping(value,'body')
def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected
def slots(rows,slot,side,issues):
    seen=set()
    for position,row in rows.values():
        key=slot(row)
        if key in seen:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        seen.add(key)
def reference(row,field,records,side,position,issues,pins=None):
    selected=records.get(row[field])
    if selected is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    target=selected[1]
    if row[field+'_revision']!=target['revision'] or row[field+'_sha256']!=(pins[row[field]] if pins is not None else c.pin(target)):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return target
def nested(value,parser,maximum,minimum=0):
    t.require(type(value) is list and minimum<=len(value)<=maximum,'NESTED_LIMIT');rows={}
    for raw in value:
        key,row=parser(raw);t.require(key not in rows,'NESTED_ID_DUPLICATE');rows[key]=row
    return [rows[key] for key in sorted(rows)]
def field(row,request):
    key,out=c.record(row,{'id','location','name','type','required','minimum','maximum','min_length','max_length','choices'},('id','name'))
    t.require(row['location'] in (('path','query','header','body') if request else ('header','body')),'LOCATION_INVALID');t.require(row['type'] in ('string','integer','boolean'),'FIELD_TYPE_INVALID');t.require(type(row['required']) is bool,'REQUIRED_FLAG_INVALID')
    t.require(type(row['choices']) is list and len(row['choices'])<=16,'CHOICE_LIMIT')
    if row['type']=='integer':
        for name in ('minimum','maximum'):
            if row[name] is not None:t.integer(row[name],10**12,-10**12)
        t.require(row['min_length'] is None and row['max_length'] is None and row['choices']==[],'INTEGER_RULE_INVALID')
        if row['minimum'] is not None and row['maximum'] is not None:t.require(row['minimum']<=row['maximum'],'INTEGER_LIMIT_ORDER_INVALID')
    elif row['type']=='boolean':t.require(all(row[name] is None for name in ('minimum','maximum','min_length','max_length')) and row['choices']==[],'BOOLEAN_RULE_INVALID')
    else:
        t.require(row['minimum'] is None and row['maximum'] is None,'STRING_RULE_INVALID')
        for name in ('min_length','max_length'):
            if row[name] is not None:t.integer(row[name],256)
        if row['min_length'] is not None and row['max_length'] is not None:t.require(row['min_length']<=row['max_length'],'STRING_LIMIT_ORDER_INVALID')
        for choice in row['choices']:
            text(choice);t.require((row['min_length'] is None or len(choice)>=row['min_length']) and (row['max_length'] is None or len(choice)<=row['max_length']),'CHOICE_OUTSIDE_LIMIT')
        t.require(len(set(row['choices']))==len(row['choices']),'CHOICE_DUPLICATE');out['choices']=sorted(row['choices'])
    if row['location'] in ('path','query','header'):t.require(row['type']=='string','TEXT_LOCATION_REQUIRED')
    if row['location']=='path':
        t.require(row['required'],'PATH_FIELD_REQUIRED')
        for choice in row['choices']:t.identifier(choice)
    if row['location']=='header':
        header_name(row['name'])
        for choice in row['choices']:header_value(choice)
    return key,out
def field_set(value,request):
    rows=nested(value,lambda row:field(row,request),32);seen=set()
    for row in rows:
        slot=(row['location'],row['name']);t.require(slot not in seen,'FIELD_SLOT_AMBIGUOUS');seen.add(slot)
    return rows
def variant(row):
    key,out=c.record(row,{'id','status','media_type','request_valid','fields'},('id',));t.integer(row['status'],599,200);media(row['media_type']);t.require(type(row['request_valid']) is bool,'REQUEST_VALID_FLAG_INVALID');out['fields']=field_set(row['fields'],False)
    if row['status'] in (204,205,304):t.require(row['media_type'] is None,'BODYLESS_STATUS_REQUIRED')
    if row['media_type'] is None:t.require(not any(v['location']=='body' for v in out['fields']),'BODY_FIELDS_WITHOUT_MEDIA')
    return key,out
def route(value):
    t.require(type(value) is list and 1<=len(value)<=8,'ROUTE_LIMIT');parameters=[]
    for part in value:
        t.require(type(part) is str,'ROUTE_SEGMENT_INVALID');match=re.fullmatch(r'\{([a-z][a-z0-9_-]{0,47})\}',part)
        if match:parameters.append(match[1])
        else:t.identifier(part)
    t.require(len(set(parameters))==len(parameters),'PATH_PARAMETER_DUPLICATE');return parameters
def operation(row):
    key,out=c.record(row,{'id','revision','method','route','request_media_type','request_fields','responses'},('id',),('revision',));t.require(row['method'] in METHODS,'METHOD_UNSUPPORTED');parameters=route(row['route']);media(row['request_media_type']);out['request_fields']=field_set(row['request_fields'],True);out['responses']=nested(row['responses'],variant,16,1)
    t.require({v['name'] for v in out['request_fields'] if v['location']=='path'}==set(parameters),'PATH_FIELDS_MISMATCH')
    t.require(len({v['status'] for v in out['responses']})==len(out['responses']),'STATUS_SLOT_AMBIGUOUS')
    if row['method'] in ('GET','HEAD','OPTIONS'):t.require(row['request_media_type'] is None,'METHOD_REQUEST_BODY_UNSUPPORTED')
    if row['request_media_type'] is None:t.require(not any(v['location']=='body' for v in out['request_fields']),'BODY_FIELDS_WITHOUT_MEDIA')
    if row['method']=='HEAD':t.require(all(v['media_type'] is None for v in out['responses']),'HEAD_RESPONSE_BODY_UNSUPPORTED')
    return key,out
def operation_scope(value,side,counts,issues):
    t.require(type(value) is list and len(value)<=128,'OPERATION_LIMIT');rows=collect(value,operation,side,counts,issues)
    t.require(sum(len(row['request_fields'])+sum(len(v['fields']) for v in row['responses']) for _,row in rows.values())<=4096,'OPERATION_FIELD_SCOPE_LIMIT')
    selected=sorted(rows.values(),key=lambda pair:pair[1]['id'])
    for offset,(position,left) in enumerate(selected):
        for _,right in selected[offset+1:]:
            if left['method']==right['method'] and len(left['route'])==len(right['route']) and all(a.startswith('{') or b.startswith('{') or a==b for a,b in zip(left['route'],right['route'])):c.issue(issues,side,position,'ROUTE_OVERLAP')
    return rows
def request(row):
    key,out=c.record(row,{'id','revision','operation','operation_revision','operation_sha256','method','path','media_type','query','headers','body','expected_valid'},('id','operation'),('revision','operation_revision'));t.sha(row['operation_sha256']);t.require(row['method'] in METHODS,'METHOD_UNSUPPORTED');media(row['media_type']);t.require(type(row['path']) is list and 1<=len(row['path'])<=8,'PATH_LIMIT')
    for value in row['path']:t.identifier(value)
    t.require(row['expected_valid'] is None or type(row['expected_valid']) is bool,'EXPECTED_VALID_INVALID');out['query']=mapping(row['query'],'query');out['headers']=mapping(row['headers'],'header');out['body']=body(row['body']);return key,out
def response(row):
    key,out=c.record(row,{'id','revision','request','request_revision','request_sha256','status','media_type','headers','body','expected_valid'},('id','request'),('revision','request_revision'));t.sha(row['request_sha256']);t.integer(row['status'],599,200);media(row['media_type']);t.require(row['expected_valid'] is None or type(row['expected_valid']) is bool,'EXPECTED_VALID_INVALID');out['headers']=mapping(row['headers'],'header');out['body']=body(row['body']);return key,out
def assess_fields(fields,values,path_ready=True):
    outcomes=[];unknown={};failed=False
    for location,provided in values.items():
        names={v['name'] for v in fields if v['location']==location};unknown[location]=len(set(provided)-names)
    for row in fields:
        provided=values[row['location']];state='valid'
        if row['location']=='path' and not path_ready:state='route_unavailable'
        elif row['name'] not in provided:state='missing_required' if row['required'] else 'optional_absent'
        else:
            value=provided[row['name']];correct=type(value) is {'string':str,'integer':int,'boolean':bool}[row['type']]
            if not correct:state='type_invalid'
            elif row['type']=='integer' and ((row['minimum'] is not None and value<row['minimum']) or (row['maximum'] is not None and value>row['maximum'])):state='out_of_range'
            elif row['type']=='string':
                if (row['min_length'] is not None and len(value)<row['min_length']) or (row['max_length'] is not None and len(value)>row['max_length']):state='length_invalid'
                elif row['choices'] and value not in row['choices']:state='choice_invalid'
        if state not in ('valid','optional_absent'):failed=True
        outcomes.append(dict(id=row['id'],state=state))
    criteria=[]
    if any(unknown.values()):criteria.append('UNDECLARED_FIELDS')
    if failed:criteria.append('FIELD_RULE_VIOLATION')
    return outcomes,unknown,criteria
def assess_request(row,selected):
    failed=[];path_ready=len(row['path'])==len(selected['route']) and all(part.startswith('{') or part==value for part,value in zip(selected['route'],row['path']));parameters={part[1:-1]:value for part,value in zip(selected['route'],row['path']) if part.startswith('{')} if path_ready else {}
    if row['method']!=selected['method']:failed.append('METHOD_MISMATCH')
    if not path_ready:failed.append('ROUTE_MISMATCH')
    if row['media_type']!=selected['request_media_type']:failed.append('MEDIA_TYPE_MISMATCH')
    if selected['request_media_type'] is None and row['body'] is not None:failed.append('BODY_NOT_ALLOWED')
    if selected['request_media_type']=='application/json' and row['body'] is None:failed.append('JSON_BODY_REQUIRED')
    fields,unknown,codes=assess_fields(selected['request_fields'],dict(path=parameters,query=row['query'],header=row['headers'],body=row['body'] or {}),path_ready);failed.extend(codes);valid=not failed
    return dict(id=row['id'],valid=valid,failed_criteria=failed,fields=fields,unknown_field_counts=unknown,expectation_met=None if row['expected_valid'] is None else row['expected_valid']==valid)
def request_scope(value,operations,side,counts,issues,required=True):
    rows=collect(value,request,side,counts,issues,required);budget=0;pins={key:c.pin(row) for key,(_,row) in operations.items()}
    for position,row in rows.values():
        selected=reference(row,'operation',operations,side,position,issues,pins)
        if selected is not None:budget+=len(selected['request_fields'])
    t.require(budget<=32768,'FIELD_ASSESSMENT_LIMIT');return rows,budget
def assess_response(row,selected,request_result):
    failed=[];variant=next((v for v in selected['responses'] if v['status']==row['status']),None);fields=[];unknown={}
    if variant is None:failed.append('STATUS_UNDECLARED')
    else:
        if variant['request_valid']!=request_result['valid']:failed.append('REQUEST_VALIDITY_VARIANT_MISMATCH')
        if row['media_type']!=variant['media_type']:failed.append('MEDIA_TYPE_MISMATCH')
        if variant['media_type'] is None and row['body'] is not None:failed.append('BODY_NOT_ALLOWED')
        if variant['media_type']=='application/json' and row['body'] is None:failed.append('JSON_BODY_REQUIRED')
        fields,unknown,codes=assess_fields(variant['fields'],dict(header=row['headers'],body=row['body'] or {}));failed.extend(codes)
    valid=not failed;return dict(id=row['id'],request=row['request'],valid=valid,variant_id=variant['id'] if variant else None,failed_criteria=failed,fields=fields,unknown_field_counts=unknown,expectation_met=None if row['expected_valid'] is None else row['expected_valid']==valid)
def exchange_context(operations_value,requests_value,responses_value,side,counts,issues,required=True):
    prefix=side+'_' if side else '';local=[];operations=operation_scope(operations_value,prefix+'operations',counts,local);requests,budget=request_scope(requests_value,operations,prefix+'requests',counts,local,required);responses=collect(responses_value,response,prefix+'responses',counts,local,False);slots(responses,lambda row:row['request'],prefix+'responses',local)
    request_pins={key:c.pin(row) for key,(_,row) in requests.items()}
    for position,row in responses.values():
        chosen=reference(row,'request',requests,prefix+'responses',position,local,request_pins)
        if chosen is not None and chosen['operation'] in operations:
            selected=operations[chosen['operation']][1];variant=next((v for v in selected['responses'] if v['status']==row['status']),None)
            if variant is not None:budget+=len(variant['fields'])
    t.require(budget<=32768,'FIELD_ASSESSMENT_LIMIT');qualified=not local;request_results={};response_results={};by_request={}
    if qualified:
        for key,(_,row) in sorted(requests.items()):request_results[key]=assess_request(row,operations[row['operation']][1])
        for key,(_,row) in sorted(responses.items()):response_results[key]=assess_response(row,operations[requests[row['request']][1]['operation']][1],request_results[row['request']]);by_request[row['request']]=key
    issues.extend(local);return dict(operations=operations,requests=requests,responses=responses,request_results=request_results,response_results=response_results,by_request=by_request,qualified=qualified)
def summary(scope,key):
    request=scope['request_results'][key];response_id=scope['by_request'].get(key);response=scope['response_results'].get(response_id)
    return dict(request_valid=request['valid'],response_valid=None if response is None else response['valid'],request_expectation_met=request['expectation_met'],response_expectation_met=None if response is None else response['expectation_met'],request_failed_criteria=request['failed_criteria'],response_failed_criteria=None if response is None else response['failed_criteria'])
def output(raw,fmt,counts,issues,qualified,assessment,pins):
    report=c.base(raw,fmt,counts,issues);report.update(assessment=assessment,qualified_scope_sha256=c.pin(dict(format=fmt,**pins)) if qualified and not issues else None,
        network_requests_performed=False,servers_started=False,authentication_performed=False,credentials_verified=False,service_behavior_verified=False,wire_protocol_verified=False,records_changed=False,raw_values_emitted=False)
    report.update({key:value if qualified else None for key,value in pins.items()});return report
