"""Single-cohort stock-position proposals; inbound availability is an assertion."""
from decimal import ROUND_CEILING
from ..contracts import fields,token,integer,number,instant,finite
from ..runtime import WorkbenchError


def calculate(row,snapshot):
    fields(row,('id','on_hand','allocated','confirmed_inbound','lead_days','review_days','safety_units','order_multiple','assumed_daily_usage_units','received_at'))
    identifier=token(row['id']);stock=integer(row['on_hand']);allocated=integer(row['allocated']);inbound=integer(row['confirmed_inbound']);lead=integer(row['lead_days'],maximum=3650);review=integer(row['review_days'],maximum=3650);safety=integer(row['safety_units']);multiple=integer(row['order_multiple'],1,1000000);usage=number(row['assumed_daily_usage_units'],maximum=1000000)
    received=instant(row['received_at']);stamp=instant(snapshot)
    if allocated>stock or received>stamp:raise WorkbenchError('STOCK_OBSERVATION_INVALID')
    available=stock-allocated;position=available+inbound
    point=int((usage*lead+safety).to_integral_value(rounding=ROUND_CEILING));target=int((usage*(lead+review)+safety).to_integral_value(rounding=ROUND_CEILING))
    shortage=max(0,target-position) if position<=point else 0
    proposal=((shortage+multiple-1)//multiple)*multiple
    return finite(dict(id=identifier,available_units=available,inventory_position_units=position,reorder_point_units=point,target_units=target,reorder_triggered=position<=point,proposed_order_units=proposal,stock_age_calendar_days=(stamp-received).total_seconds()/86400,inbound_assumed_available=True,purchase_authorized=False))
