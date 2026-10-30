"""Explicit model/request bindings and conservative nonexecuting fallback planning."""
import toolkit as t
import decision_core as c

FAILURES=('timeout','unavailable','rate-limited','invalid-output')

def model(row):
    key,out=c.record(row,{'id','revision','tasks','input_types','output_types','max_input_units','max_output_units','context_units'},('id',),('revision',))
    for field in ('tasks','input_types','output_types'):out[field]=c.tags(row[field],1)
    for field in ('max_input_units','max_output_units','context_units'):t.integer(row[field],10**9,1)
    return key,out

def model_failures(row):
    return [code for field,code in [('max_input_units','MODEL_INPUT_EXCEEDS_CONTEXT'),('max_output_units','MODEL_OUTPUT_EXCEEDS_CONTEXT')] if row[field]>row['context_units']]

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def models(value,counts,issues):
    selected=collect(value,model,'models',counts,issues)
    for position,row in selected.values():
        for code in model_failures(row):c.issue(issues,'models',position,code)
    return selected

def request(row):
    key,out=c.record(row,{'id','revision','task','input_type','output_type','input_sha256','prompt_sha256','input_units','output_budget'},
                     ('id','task','input_type','output_type'),('revision',))
    t.sha(row['input_sha256']);t.sha(row['prompt_sha256']);t.integer(row['input_units'],10**9);t.integer(row['output_budget'],10**9,1)
    return key,out

def policy(row):
    _,out=c.record(row,{'id','revision','allowed_models','allowed_tasks','allowed_input_types','allowed_output_types','max_input_units','max_output_units','max_total_units'},('id',),('revision',))
    for field in ('allowed_models','allowed_tasks','allowed_input_types','allowed_output_types'):out[field]=c.tags(row[field],1)
    for field in ('max_input_units','max_output_units','max_total_units'):t.integer(row[field],10**9,1)
    return out

def policy_scope(rule,catalog,issues):
    if not set(rule['allowed_models'])<=set(catalog):c.issue(issues,'policy',0,'POLICY_MODEL_UNKNOWN')

def eligible(req,selected,rule):
    checks=[(selected['id'] in rule['allowed_models'],'MODEL_NOT_ALLOWED'),
        (req['task'] in selected['tasks'],'MODEL_TASK_UNSUPPORTED'),(req['input_type'] in selected['input_types'],'MODEL_INPUT_TYPE_UNSUPPORTED'),
        (req['output_type'] in selected['output_types'],'MODEL_OUTPUT_TYPE_UNSUPPORTED'),
        (req['task'] in rule['allowed_tasks'],'TASK_NOT_ALLOWED'),(req['input_type'] in rule['allowed_input_types'],'INPUT_TYPE_NOT_ALLOWED'),
        (req['output_type'] in rule['allowed_output_types'],'OUTPUT_TYPE_NOT_ALLOWED'),
        (req['input_units']<=selected['max_input_units'],'MODEL_INPUT_BUDGET_EXCEEDED'),
        (req['output_budget']<=selected['max_output_units'],'MODEL_OUTPUT_BUDGET_EXCEEDED'),
        (req['input_units']+req['output_budget']<=selected['context_units'],'MODEL_CONTEXT_BUDGET_EXCEEDED'),
        (req['input_units']<=rule['max_input_units'],'POLICY_INPUT_BUDGET_EXCEEDED'),
        (req['output_budget']<=rule['max_output_units'],'POLICY_OUTPUT_BUDGET_EXCEEDED'),
        (req['input_units']+req['output_budget']<=rule['max_total_units'],'POLICY_TOTAL_BUDGET_EXCEEDED')]
    return [code for passes,code in checks if not passes]

def model_reference(row,catalog,side,position,issues):
    selected=catalog.get(row['model'])
    if selected is None:c.issue(issues,side,position,'MODEL_UNKNOWN');return
    if row['model_revision']!=selected[1]['revision'] or row['model_sha256']!=c.pin(selected[1]):c.issue(issues,side,position,'MODEL_SNAPSHOT_MISMATCH')

def unique_slots(selected,field,side,issues):
    slots={}
    for position,row in selected.values():
        if row[field] in slots:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        slots[row[field]]=row
    return slots

def output(raw,fmt,counts,issues,**values):
    report=c.base(raw,fmt,counts,issues)
    report.update(capabilities_independently_verified=False,artifact_bytes_verified=False,input_units_measured=False,output_units_measured=False,
        inference_performed=False,inference_occurrence_verified=False,provider_contacted=False,
        output_content_verified=False,dispatch_authorized=False,**values)
    return report

def step(row):
    key,out=c.record(row,{'id','model','model_revision','model_sha256','next_step','on_failures'},('id','model'),('model_revision',))
    t.sha(row['model_sha256'])
    if row['next_step'] is not None:t.identifier(row['next_step'])
    out['on_failures']=c.tags(row['on_failures'])
    t.require(set(out['on_failures'])<=set(FAILURES),'FAILURE_CLASS_UNKNOWN')
    t.require(bool(out['on_failures'])==(row['next_step'] is not None),'TRANSITION_CONDITIONS_INVALID');return key,out

def chain_scope(value,counts,issues):
    catalog=models(value['models'],counts,issues);_,req=request(value['request']);rule=policy(value['policy']);policy_scope(rule,catalog,issues)
    chain=value['chain'];_,normalized=c.record(chain,{'id','revision','request_sha256','policy_sha256','start','maximum_attempts','steps'},('id','start'),('revision',))
    t.sha(chain['request_sha256']);t.sha(chain['policy_sha256']);t.integer(chain['maximum_attempts'],32,1)
    t.require(type(chain['steps']) is list and len(chain['steps'])<=32,'STEP_LIMIT')
    steps=collect(chain['steps'],step,'steps',counts,issues)
    if chain['request_sha256']!=c.pin(req):c.issue(issues,'chain',0,'REQUEST_PIN_MISMATCH')
    if chain['policy_sha256']!=c.pin(rule):c.issue(issues,'chain',0,'POLICY_PIN_MISMATCH')
    if chain['start'] not in steps:c.issue(issues,'chain',0,'START_UNKNOWN')
    for position,row in steps.values():
        model_reference(row,catalog,'steps',position,issues)
        if row['next_step'] is not None and row['next_step'] not in steps:c.issue(issues,'steps',position,'NEXT_STEP_UNKNOWN')
    order=[]
    if not issues:
        current=chain['start'];seen=set()
        while current is not None:
            if current in seen:c.issue(issues,'chain',0,'CHAIN_CYCLE');break
            seen.add(current);order.append(steps[current][1]);current=steps[current][1]['next_step']
        if set(steps)!=seen:c.issue(issues,'chain',0,'STEPS_UNREACHABLE')
    qualified=not issues;assessment=None;plan_pin=None
    normalized['steps']=[steps[k][1] for k in sorted(steps)]
    pins=dict(models_sha256=c.cohort_pin(catalog),request_sha256=c.pin(req),policy_sha256=c.pin(rule),chain_sha256=c.pin(normalized))
    if qualified:
        outcomes=[];failures=[]
        for row in order:
            failed=eligible(req,catalog[row['model']][1],rule)
            for code in failed:c.issue(issues,'steps',steps[row['id']][0],code)
            outcomes.append(dict(step=row['id'],model=row['model'],eligible=not failed,failed_criteria=failed,next_step=row['next_step'],on_failures=row['on_failures']))
            failures.extend(failed)
        if len(order)>chain['maximum_attempts']:failures.append('CHAIN_EXCEEDS_ATTEMPT_CAP');c.issue(issues,'chain',0,'CHAIN_EXCEEDS_ATTEMPT_CAP')
        if len({r['model'] for r in order})!=len(order):failures.append('MODEL_REPEATED_IN_CHAIN');c.issue(issues,'chain',0,'MODEL_REPEATED_IN_CHAIN')
        assessment=dict(ordered_steps=outcomes,declared_steps=len(order),maximum_attempts=chain['maximum_attempts'],
            failed_criteria=sorted(set(failures)),eligible_for_manual_routing_review=not failures)
        if not failures:plan_pin=c.pin(pins)
    exposed={key:pin if qualified else None for key,pin in pins.items()}
    return dict(assessment=assessment,plan_sha256=plan_pin,**exposed),dict(models=catalog,request=req,policy=rule,chain=normalized,order=order)
