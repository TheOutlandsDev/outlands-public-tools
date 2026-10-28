"""UTC event identities and snapshot reconciliation over an explicit saved set."""
from ..contracts import fields,text,token,integer,instant,utc
from ..runtime import WorkbenchError


def event(value):
    fields(value,('source','event_id','family','units','occurred_at'))
    return dict(source=token(value['source']),event_id=token(value['event_id']),family=token(value['family']),units=integer(value['units'],1),occurred_at=utc(value['occurred_at']))


def calculate(value):
    start=instant(value['window']['start']);end=instant(value['window']['end']);snapshot=instant(value['snapshot_utc'])
    counts=dict(queued=0,buffer=0,hold=0);units=dict.fromkeys(counts,0);holds=[]
    for row in value['active_lots']:
        fields(row,('id','family','stage','units','entered_at'),('held_since','hold_reason'))
        identifier=token(row['id']);token(row['family']);stage=row['stage'];quantity=integer(row['units'],1);entered=instant(row['entered_at'])
        if type(stage) is not str or stage not in counts or entered>snapshot:raise WorkbenchError('LOT_STATE_INVALID')
        counts[stage]+=1;units[stage]+=quantity
        if stage=='hold':
            held=instant(row.get('held_since'));reason=text(row.get('hold_reason'),240)
            if not entered<=held<=snapshot:raise WorkbenchError('HOLD_TIME_INVALID')
            holds.append(dict(id=identifier,hold_age_hours=(snapshot-held).total_seconds()/3600,reason=reason))
        elif 'held_since' in row or 'hold_reason' in row:raise WorkbenchError('HOLD_FIELDS_INVALID')
    included=[r for r in value['completions'] if start<=instant(r['occurred_at'])<end]
    if any(instant(r['occurred_at'])>snapshot for r in value['completions']):raise WorkbenchError('EVENT_AFTER_SNAPSHOT')
    family={}
    for row in included:family[row['family']]=family.get(row['family'],0)+row['units']
    total=sum(r['units'] for r in included)
    if sum(family.values())!=total:raise WorkbenchError('RECONCILIATION_FAILED')
    return dict(stage_lot_counts=counts,stage_unit_counts=units,active_lots=sum(counts.values()),active_units=sum(units.values()),holds=sorted(holds,key=lambda r:(-r['hold_age_hours'],r['id'])),completed_units=total,completion_events=len(included),family_units=dict(sorted(family.items())),completed_units_per_calendar_hour=total/((end-start).total_seconds()/3600),reconciled=True,window_start_inclusive=value['window']['start'],window_end_exclusive=value['window']['end'])
