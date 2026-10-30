"""Bounded versioned working windows, task DAGs and pinned declared placements."""
from collections import defaultdict,deque
import toolkit as t
import decision_core as c

def collect(value,parser,side,counts,issues,required=True):
    selected,counts[side],found=c.rows(value,parser,side);issues.extend(found)
    if required and not selected:c.issue(issues,side,0,'COHORT_EMPTY')
    return selected

def span(value):
    t.fields(value,{'start','end'});t.integer(value['start'],10**9);t.integer(value['end'],10**9);t.require(value['start']<value['end'],'SPAN_INVALID');return dict(value)

def calendar(row):
    key,out=c.record(row,{'id','revision','windows'},('id',),('revision',))
    t.require(type(row['windows']) is list and len(row['windows'])<=32,'WINDOW_LIMIT')
    windows=sorted((span(v) for v in row['windows']),key=lambda v:(v['start'],v['end']));merged=[]
    for window in windows:
        if merged:
            t.require(window['start']>=merged[-1]['end'],'WINDOW_OVERLAP')
            if window['start']==merged[-1]['end']:merged[-1]['end']=window['end'];continue
        merged.append(dict(window))
    out['windows']=merged;return key,out

def calendar_scope(rows):t.require(sum(len(row['windows']) for _,row in rows.values())<=4096,'CALENDAR_SCOPE_LIMIT')

def task(row):
    key,out=c.record(row,{'id','revision','duration','release','due'},('id',),('revision',))
    t.integer(row['duration'],10**6,1);t.integer(row['release'],10**9);t.integer(row['due'],10**9);t.require(row['release']<=row['due'],'TASK_WINDOW_INVALID');return key,out

def dependency(row):
    key,out=c.record(row,{'id','predecessor','predecessor_revision','predecessor_sha256','successor','successor_revision','successor_sha256','minimum_lag'},('id','predecessor','successor'),('predecessor_revision','successor_revision'))
    t.sha(row['predecessor_sha256']);t.sha(row['successor_sha256']);t.integer(row['minimum_lag'],10**6);return key,out

def reference(row,field,records,side,position,issues):
    target=records.get(row[field])
    if target is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    target=target[1]
    if row[field+'_revision']!=target['revision'] or row[field+'_sha256']!=c.pin(target):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return target

def slots(records,slot,side,issues):
    seen=set()
    for position,row in records.values():
        key=slot(row)
        if key in seen:c.issue(issues,side,position,'SLOT_AMBIGUOUS')
        seen.add(key)

def graph(tasks,dependencies,side,issues):
    slots(dependencies,lambda row:(row['predecessor'],row['successor']),side,issues)
    outgoing=defaultdict(dict);incoming=defaultdict(list);indegree={key:0 for key in tasks}
    for position,row in dependencies.values():
        before=reference(row,'predecessor',tasks,side,position,issues);after=reference(row,'successor',tasks,side,position,issues)
        if before and after and row['successor'] not in outgoing[row['predecessor']]:
            outgoing[row['predecessor']][row['successor']]=row;incoming[row['successor']].append(row);indegree[row['successor']]+=1
    queue=deque(sorted(key for key,value in indegree.items() if value==0));order=[]
    while queue:
        key=queue.popleft();order.append(key)
        for child in sorted(outgoing[key]):
            indegree[child]-=1
            if indegree[child]==0:queue.append(child)
    if len(order)!=len(tasks):c.issue(issues,side,0,'DEPENDENCY_CYCLE')
    return order,incoming

def plan(value):
    _,out=c.record(value,{'id','revision','tasks_sha256','dependencies_sha256','calendars_sha256'},('id',),('revision',))
    for field in ('tasks_sha256','dependencies_sha256','calendars_sha256'):t.sha(value[field])
    return out

def placement(row):
    key,out=c.record(row,{'id','plan','plan_revision','plan_sha256','task','task_revision','task_sha256','calendar','calendar_revision','calendar_sha256','start'},('id','plan','task','calendar'),('plan_revision','task_revision','calendar_revision'))
    for field in ('plan_sha256','task_sha256','calendar_sha256'):t.sha(row[field])
    t.integer(row['start'],10**9);return key,out

def bundle(value,counts,issues,prefix=''):
    t.fields(value,{'tasks','dependencies','calendars','plan','placements'})
    tasks=collect(value['tasks'],task,prefix+'tasks',counts,issues);dependencies=collect(value['dependencies'],dependency,prefix+'dependencies',counts,issues,False)
    calendars=collect(value['calendars'],calendar,prefix+'calendars',counts,issues);calendar_scope(calendars)
    header=plan(value['plan']);placements=collect(value['placements'],placement,prefix+'placements',counts,issues,False)
    for field,rows in [('tasks',tasks),('dependencies',dependencies),('calendars',calendars)]:
        if header[field+'_sha256']!=c.cohort_pin(rows):c.issue(issues,prefix+'plan',0,'PLAN_COHORT_MISMATCH')
    slots(placements,lambda row:row['task'],prefix+'placements',issues)
    for position,row in placements.values():
        reference(row,'task',tasks,prefix+'placements',position,issues);reference(row,'calendar',calendars,prefix+'placements',position,issues)
        if row['plan']!=header['id'] or row['plan_revision']!=header['revision'] or row['plan_sha256']!=c.pin(header):c.issue(issues,prefix+'placements',position,'PLAN_SNAPSHOT_MISMATCH')
    order,incoming=graph(tasks,dependencies,prefix+'dependencies',issues)
    return dict(tasks=tasks,dependencies=dependencies,calendars=calendars,plan=header,placements=placements,incoming=incoming)

def evaluate(b):
    placed={row['task']:row for _,row in b['placements'].values()};out=[]
    for key,(_,task) in sorted(b['tasks'].items()):
        row=placed.get(key);codes=[];start=finish=lateness=calendar_id=None
        if row is None:codes.append('PLACEMENT_MISSING')
        else:
            start=row['start'];finish=start+task['duration'];lateness=max(0,finish-task['due']);calendar_id=row['calendar']
            if start<task['release']:codes.append('START_BEFORE_RELEASE')
            if lateness:codes.append('FINISH_AFTER_DUE')
            windows=b['calendars'][calendar_id][1]['windows']
            if not any(w['start']<=start and finish<=w['end'] for w in windows):codes.append('OUTSIDE_WORKING_WINDOW')
            for edge in b['incoming'][key]:
                predecessor=placed.get(edge['predecessor'])
                if predecessor is None:codes.append('PREDECESSOR_PLACEMENT_MISSING')
                elif start<predecessor['start']+b['tasks'][edge['predecessor']][1]['duration']+edge['minimum_lag']:codes.append('PRECEDENCE_LAG_VIOLATION')
        out.append(dict(id=key,task_sha256=c.pin(task),placement_id=row['id'] if row else None,calendar=calendar_id,
            start=start,finish=finish,lateness=lateness,declared_timing_feasible=not codes,failed_criteria=sorted(set(codes))))
    return out

def bundle_pins(b):return dict(tasks_sha256=c.cohort_pin(b['tasks']),dependencies_sha256=c.cohort_pin(b['dependencies']),calendars_sha256=c.cohort_pin(b['calendars']),placements_sha256=c.cohort_pin(b['placements']),plan_sha256=c.pin(b['plan']))

def output(raw,fmt,counts,issues,qualified,assessment,pins):
    report=c.base(raw,fmt,counts,issues)
    report.update(assessment=assessment,qualified_scope_sha256=c.pin(dict(format=fmt,**pins)) if qualified and not issues else None,
        actual_availability_verified=False,actual_task_durations_verified=False,capacity_checked=False,optimality_proven=False,
        calendar_updated=False,schedule_executed=False,dispatch_authorized=False,records_changed=False)
    report.update({key:value if qualified else None for key,value in pins.items()});return report
