"""Custom bounded form and interaction declarations; no HTML, DOM, scripts or browsers."""
import toolkit as t
import decision_core as c

def scalar(value):
    if type(value) is bool:return
    if type(value) is int:t.integer(value,10**12,-10**12);return
    t.require(type(value) is str and len(value)<=256,'SCALAR_INVALID')

def value_state(value,field):
    if type(value) is not {'string':str,'integer':int,'boolean':bool}[field['type']]:return 'type_invalid'
    if field['type']=='integer' and ((field['minimum'] is not None and value<field['minimum']) or (field['maximum'] is not None and value>field['maximum'])):return 'out_of_range'
    if field['type']=='string':
        if (field['min_length'] is not None and len(value)<field['min_length']) or (field['max_length'] is not None and len(value)>field['max_length']):return 'length_invalid'
        if field['choices'] and value not in field['choices']:return 'choice_invalid'
    return 'valid'

def conditions(value):
    t.require(type(value) is list and len(value)<=8,'CONDITION_LIMIT');seen=set();out=[]
    for row in value:
        t.fields(row,{'field','equals'});t.identifier(row['field']);scalar(row['equals'])
        t.require(row['field'] not in seen,'CONDITION_FIELD_DUPLICATE');seen.add(row['field']);out.append(dict(row))
    return sorted(out,key=lambda row:row['field'])

def field(row):
    key,out=c.record(row,{'id','type','required','minimum','maximum','min_length','max_length','choices','visible_when','required_when'},('id',))
    t.require(row['type'] in ('string','integer','boolean'),'FIELD_TYPE_INVALID');t.require(type(row['required']) is bool,'REQUIRED_FLAG_INVALID')
    t.require(type(row['choices']) is list and len(row['choices'])<=16,'CHOICE_LIMIT')
    if row['type']=='integer':
        for name in ('minimum','maximum'):
            if row[name] is not None:t.integer(row[name],10**12,-10**12)
        t.require(row['min_length'] is None and row['max_length'] is None and not row['choices'],'INTEGER_RULE_INVALID')
        if row['minimum'] is not None and row['maximum'] is not None:t.require(row['minimum']<=row['maximum'],'INTEGER_LIMIT_ORDER_INVALID')
    elif row['type']=='boolean':t.require(all(row[name] is None for name in ('minimum','maximum','min_length','max_length')) and not row['choices'],'BOOLEAN_RULE_INVALID')
    else:
        t.require(row['minimum'] is None and row['maximum'] is None,'STRING_RULE_INVALID')
        for name in ('min_length','max_length'):
            if row[name] is not None:t.integer(row[name],256)
        if row['min_length'] is not None and row['max_length'] is not None:t.require(row['min_length']<=row['max_length'],'STRING_LIMIT_ORDER_INVALID')
        for choice in row['choices']:t.require(type(choice) is str and len(choice)<=256,'CHOICE_INVALID');t.require(value_state(choice,row)=='valid','CHOICE_OUTSIDE_LIMIT')
        t.require(len(set(row['choices']))==len(row['choices']),'CHOICE_DUPLICATE');out['choices']=sorted(row['choices'])
    out['visible_when']=conditions(row['visible_when']);out['required_when']=conditions(row['required_when']);return key,out

def nested(value,parser,maximum,minimum=0):
    t.require(type(value) is list and minimum<=len(value)<=maximum,'NESTED_LIMIT');out={}
    for row in value:
        key,normalized=parser(row);t.require(key not in out,'NESTED_ID_DUPLICATE');out[key]=normalized
    return [out[key] for key in sorted(out)]

def field_order(fields):
    records={row['id']:row for row in fields};dependencies={key:{v['field'] for name in ('visible_when','required_when') for v in row[name]} for key,row in records.items()}
    for key,row in records.items():
        for name in ('visible_when','required_when'):
            for condition in row[name]:
                target=records.get(condition['field']);t.require(target is not None,'CONDITION_REFERENCE_UNKNOWN');t.require(value_state(condition['equals'],target)=='valid','CONDITION_VALUE_INVALID')
    order=[]
    while len(order)<len(records):
        ready=sorted(key for key,needs in dependencies.items() if key not in order and needs<=set(order));t.require(bool(ready),'FIELD_DEPENDENCY_CYCLE');order.extend(ready)
    return order

def form(row):
    key,out=c.record(row,{'id','revision','fields'},('id',),('revision',));out['fields']=nested(row['fields'],field,32,1);field_order(out['fields']);return key,out

def mapping(value):
    t.require(type(value) is dict and len(value)<=32,'VALUE_MAP_LIMIT')
    for key,item in value.items():t.identifier(key);scalar(item)
    return dict(value)

def expectation(value):t.require(value is None or type(value) is bool,'EXPECTED_VALID_INVALID')

def submission(row):
    key,out=c.record(row,{'id','revision','form','form_revision','form_sha256','values','expected_valid'},('id','form'),('revision','form_revision'));t.sha(row['form_sha256']);out['values']=mapping(row['values']);expectation(row['expected_valid']);return key,out

def transition(row):
    key,out=c.record(row,{'id','from','to','action','submission_requirement'},('id','from','to','action'));t.require(row['submission_requirement'] in ('none','valid','invalid'),'SUBMISSION_REQUIREMENT_INVALID');return key,out

def flow(row):
    key,out=c.record(row,{'id','revision','form','form_revision','form_sha256','states','initial_state','terminal_states','transitions'},('id','form','initial_state'),('revision','form_revision'));t.sha(row['form_sha256']);out['states']=c.tags(row['states'],2);t.require(len(out['states'])<=16,'STATE_LIMIT');out['terminal_states']=c.tags(row['terminal_states'],1)
    states=set(out['states']);terminal=set(out['terminal_states']);t.require(terminal<states and row['initial_state'] in states-terminal,'FLOW_STATE_INVALID');out['transitions']=nested(row['transitions'],transition,64,1);slots=set()
    for item in out['transitions']:
        t.require(item['from'] in states-terminal and item['to'] in states,'TRANSITION_STATE_INVALID');slot=(item['from'],item['action']);t.require(slot not in slots,'TRANSITION_AMBIGUOUS');slots.add(slot)
    def reach(seeds,reverse=False):
        found=set(seeds)
        while True:
            extra={v['from' if reverse else 'to'] for v in out['transitions'] if v['to' if reverse else 'from'] in found};new=found|extra
            if new==found:return found
            found=new
    t.require(reach({row['initial_state']})==states and reach(terminal,True)==states,'FLOW_DISCONNECTED_OR_DEAD_END');return key,out

def event(row):
    t.fields(row,{'sequence','action','from','to','submission','submission_revision','submission_sha256'});t.integer(row['sequence'],128,1)
    for name in ('action','from','to'):t.identifier(row[name])
    if row['submission'] is None:t.require(row['submission_revision'] is None and row['submission_sha256'] is None,'EMPTY_SUBMISSION_REFERENCE_INVALID')
    else:t.identifier(row['submission']);t.integer(row['submission_revision'],10**6,1);t.sha(row['submission_sha256'])
    return dict(row)

def history(row):
    key,out=c.record(row,{'id','revision','flow','flow_revision','flow_sha256','events','expected_valid'},('id','flow'),('revision','flow_revision'));t.sha(row['flow_sha256']);expectation(row['expected_valid']);t.require(type(row['events']) is list and len(row['events'])<=128,'EVENT_LIMIT');out['events']=[event(item) for item in row['events']];return key,out

def collect(value,parser,side,counts,issues,required=False,maximum=1000):
    t.require(type(value) is list and len(value)<=maximum,'COHORT_LIMIT');rows,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not rows:c.issue(issues,side,0,'COHORT_EMPTY')
    return rows

def reference(row,name,records,pins,side,position,issues):
    target=records.get(row[name])
    if target is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    selected=target[1]
    if row[name+'_revision']!=selected['revision'] or row[name+'_sha256']!=pins[row[name]]:c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return selected

def assess_submission(row,selected,order):
    fields={v['id']:v for v in selected['fields']};values=row['values'];decisions={}
    def matches(conditions):return all(decisions[v['field']]['visible'] and decisions[v['field']]['state']=='valid' and type(values.get(v['field'])) is type(v['equals']) and values.get(v['field'])==v['equals'] for v in conditions)
    for key in order:
        item=fields[key];visible=matches(item['visible_when']);required=visible and (item['required'] or bool(item['required_when']) and matches(item['required_when']))
        if not visible:state='hidden_value_refused' if key in values else 'hidden_absent'
        elif key not in values:state='missing_required' if required else 'optional_absent'
        else:state=value_state(values[key],item)
        decisions[key]=dict(id=key,visible=visible,required=required,state=state)
    unknown=len(set(values)-set(fields));valid=unknown==0 and all(v['state'] in ('valid','hidden_absent','optional_absent') for v in decisions.values())
    return dict(id=row['id'],valid=valid,fields=[decisions[key] for key in sorted(decisions)],unknown_field_count=unknown,expectation_met=None if row['expected_valid'] is None else row['expected_valid']==valid)

def context(value,prefix,counts,issues,with_histories=False,required=True):
    def name(key):return prefix+'_'+key if prefix else key
    forms=collect(value[name('forms')],form,name('forms'),counts,issues,True,64);form_pins={key:c.pin(row) for key,(_,row) in forms.items()};orders={key:field_order(row['fields']) for key,(_,row) in forms.items()}
    submissions=collect(value[name('submissions')],submission,name('submissions'),counts,issues,required and not with_histories);budget=0
    for position,row in submissions.values():
        selected=reference(row,'form',forms,form_pins,name('submissions'),position,issues)
        if selected is not None:budget+=len(selected['fields'])
    t.require(budget<=8192,'FIELD_ASSESSMENT_LIMIT');out=dict(forms=forms,submissions=submissions,budget=budget,orders=orders)
    if with_histories:
        flows=collect(value[name('flows')],flow,name('flows'),counts,issues,True,64);flow_pins={key:c.pin(row) for key,(_,row) in flows.items()};submission_pins={key:c.pin(row) for key,(_,row) in submissions.items()}
        for position,row in flows.values():reference(row,'form',forms,form_pins,name('flows'),position,issues)
        histories=collect(value[name('histories')],history,name('histories'),counts,issues,required,256);t.require(sum(len(row['events']) for _,row in histories.values())<=4096,'EVENT_ASSESSMENT_LIMIT')
        for position,row in histories.values():
            selected=reference(row,'flow',flows,flow_pins,name('histories'),position,issues)
            for item in row['events']:
                if item['submission'] is not None:
                    observed=reference(item,'submission',submissions,submission_pins,name('histories'),position,issues)
                    if observed is not None and selected is not None and any(observed[key]!=selected[key] for key in ('form','form_revision','form_sha256')):c.issue(issues,name('histories'),position,'SUBMISSION_FORM_MISMATCH')
        out.update(flows=flows,histories=histories)
    return out

def assess_history(row,selected,submissions):
    current=selected['initial_state'];intact=True;steps=[];slots={(v['from'],v['action']):v for v in selected['transitions']}
    for index,item in enumerate(row['events'],1):
        codes=[]
        if not intact:codes.append('UNASSESSED_AFTER_INVALID_STEP')
        else:
            if item['sequence']!=index:codes.append('SEQUENCE_INVALID')
            if item['from']!=current:codes.append('SOURCE_STATE_MISMATCH')
            choice=slots.get((current,item['action']))
            if choice is None:codes.append('TRANSITION_UNDECLARED')
            else:
                if item['to']!=choice['to']:codes.append('TARGET_STATE_MISMATCH')
                needed=choice['submission_requirement']
                if needed=='none' and item['submission'] is not None:codes.append('SUBMISSION_NOT_ALLOWED')
                elif needed!='none':
                    if item['submission'] is None:codes.append('SUBMISSION_REQUIRED')
                    elif submissions[item['submission']]['valid']!=(needed=='valid'):codes.append('SUBMISSION_VALIDITY_MISMATCH')
            if not codes:current=choice['to']
        if codes:intact=False
        steps.append(dict(sequence=index,valid=not codes,failed_criteria=codes))
    reached=intact and current in selected['terminal_states'];valid=intact and reached
    return dict(id=row['id'],valid=valid,last_confirmed_state=current,terminal_reached=reached,steps=steps,expectation_met=None if row['expected_valid'] is None else row['expected_valid']==valid)

def outcomes(scope):
    submissions={key:assess_submission(row,scope['forms'][row['form']][1],scope['orders'][row['form']]) for key,(_,row) in sorted(scope['submissions'].items())}
    histories={key:assess_history(row,scope['flows'][row['flow']][1],submissions) for key,(_,row) in sorted(scope.get('histories',{}).items())};return submissions,histories

def check_expectations(records,results,side,issues,require_valid=False):
    for key,(position,_) in records.items():
        if require_valid and not results[key]['valid']:c.issue(issues,side,position,'CONTRACT_VIOLATION')
        if results[key]['expectation_met'] is False:c.issue(issues,side,position,'EXPECTED_VALIDITY_MISMATCH')

def output(raw,fmt,counts,issues,qualified,assessment,pins):
    result=c.base(raw,fmt,counts,issues);result.update(assessment=assessment,qualified_scope_sha256=c.pin(pins) if qualified and not issues else None)
    result.update({key:value if qualified else None for key,value in pins.items()})
    for key in ('browser_started','dom_inspected','scripts_executed','network_requests_performed','authentication_performed','records_changed','raw_values_emitted','accessibility_verified','whole_ui_compatibility_verified'):result[key]=False
    return result

def submission_case(row):return {key:value for key,value in row.items() if key not in ('form_revision','form_sha256')}

def history_case(row):
    out={key:value for key,value in row.items() if key not in ('flow_revision','flow_sha256','events')};out['events']=[{key:value for key,value in v.items() if key!='submission_sha256'} for v in row['events']];return out

def compare(raw,value):
    counts={};issues=[];left=context(value,'baseline',counts,issues,True);right=context(value,'candidate',counts,issues,True,False);t.require(left['budget']+right['budget']<=8192,'COMPARISON_FIELD_LIMIT')
    for kind in ('forms','flows'):
        for key in set(left[kind])&set(right[kind]):
            a,b=left[kind][key][1],right[kind][key][1]
            if a['revision']==b['revision'] and a!=b:c.issue(issues,kind,0,'DEFINITION_IDENTITY_CONFLICT')
    qualified=not issues;assessment=None
    if qualified:
        ls,lh=outcomes(left);rs,rh=outcomes(right)
        for prefix,scope,subs,hists in [('baseline',left,ls,lh),('candidate',right,rs,rh)]:
            check_expectations(scope['submissions'],subs,prefix+'_submissions',issues);check_expectations(scope['histories'],hists,prefix+'_histories',issues)
        left_cases={key:t.encode(submission_case(row)) for key,(_,row) in left['submissions'].items()};right_cases={key:t.encode(submission_case(row)) for key,(_,row) in right['submissions'].items()};same_submissions=left_cases==right_cases;submission_rows=[]
        for key in sorted(set(ls)|set(rs)):
            a,b=ls.get(key),rs.get(key)
            comparable=key in left_cases and key in right_cases and left_cases[key]==right_cases[key];state=('unchanged' if a==b else 'observed_outcomes_changed') if comparable else 'submission_scope_changed'
            if state!='unchanged':c.issue(issues,'submissions',0,state.upper())
            submission_rows.append(dict(id=key,state=state,baseline=a if comparable else None,candidate=b if comparable else None))
        history_rows=[]
        for key in sorted(set(lh)|set(rh)):
            a=b=None
            if key not in lh:state='candidate_only'
            elif key not in rh:state='candidate_missing'
            elif not same_submissions:state='submission_scope_changed'
            elif history_case(left['histories'][key][1])!=history_case(right['histories'][key][1]):state='interaction_scope_changed'
            else:
                a,b=lh[key],rh[key];used={v['submission'] for v in left['histories'][key][1]['events'] if v['submission'] is not None};state='unchanged' if a==b and all(ls[item]==rs[item] for item in used) else 'observed_outcomes_changed'
            if state!='unchanged':c.issue(issues,'histories',0,state.upper())
            history_rows.append(dict(id=key,state=state,baseline=a,candidate=b))
        assessment=dict(submissions=submission_rows,histories=history_rows,all_declared_outcomes_equal=not issues)
    pins={prefix+'_'+kind+'_sha256':c.cohort_pin(scope[kind]) for prefix,scope in [('baseline',left),('candidate',right)] for kind in ('forms','flows','submissions','histories')}
    return output(raw,'outlands-ui-interaction-scenarios-report-v1',counts,issues,qualified,assessment,pins)

def check(raw,mode):
    value=t.decode(raw)
    formats={'forms':'outlands-form-definitions','submissions':'outlands-form-submissions','histories':'outlands-ui-histories','scenarios':'outlands-ui-interaction-scenarios'}
    keys={'format','forms'} if mode=='forms' else {'format','forms','submissions'} if mode=='submissions' else {'format','forms','flows','submissions','histories'} if mode=='histories' else {'format'}|{prefix+'_'+kind for prefix in ('baseline','candidate') for kind in ('forms','flows','submissions','histories')}
    t.fields(value,keys);t.require(value['format']==formats[mode]+'-v1','FORMAT_INVALID')
    if mode=='scenarios':return compare(raw,value)
    counts={};issues=[];assessment=None
    if mode=='forms':
        records=collect(value['forms'],form,'forms',counts,issues,True,64);qualified=not issues;pins=dict(forms_sha256=c.cohort_pin(records))
        if qualified:assessment=dict(forms=[dict(id=key,field_count=len(row['fields']),evaluation_order=field_order(row['fields'])) for key,(_,row) in sorted(records.items())])
    else:
        scope=context(value,'',counts,issues,mode=='histories');qualified=not issues;pins={kind+'_sha256':c.cohort_pin(scope[kind]) for kind in ('forms','submissions')+(('flows','histories') if mode=='histories' else ())}
        if qualified:
            submissions,histories=outcomes(scope);check_expectations(scope['submissions'],submissions,'submissions',issues,mode=='submissions');assessment=dict(submissions=list(submissions.values()))
            if mode=='histories':check_expectations(scope['histories'],histories,'histories',issues,True);assessment['histories']=list(histories.values())
    return output(raw,formats[mode]+'-report-v1',counts,issues,qualified,assessment,pins)
