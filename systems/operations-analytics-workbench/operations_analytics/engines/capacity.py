"""Declared capacity arithmetic, using Decimal floor/ceiling with explicit units."""
from decimal import ROUND_CEILING,ROUND_FLOOR
from ..contracts import fields,token,integer,number,finite
from ..runtime import WorkbenchError


def calculate(row):
    fields(row,('id','demand_units','people','minutes_per_unit','shift_minutes','break_minutes','unavailable_minutes_per_person','productive_fraction'))
    identifier=token(row['id']);demand=integer(row['demand_units']);people=integer(row['people'],maximum=100000)
    cycle=number(row['minutes_per_unit'],0.000001,1000000)
    shift=number(row['shift_minutes'],maximum=527040);breaks=number(row['break_minutes'],maximum=527040);unavailable=number(row['unavailable_minutes_per_person'],maximum=527040)
    factor=number(row['productive_fraction'],maximum=1)
    if breaks+unavailable>shift:raise WorkbenchError('SHIFT_PARTITION_INVALID')
    productive=(shift-breaks-unavailable)*factor
    capacity=int((people*productive/cycle).to_integral_value(rounding=ROUND_FLOOR))
    minimum=0 if demand==0 else None if productive==0 else int((demand*cycle/productive).to_integral_value(rounding=ROUND_CEILING))
    if capacity>1000000000 or minimum is not None and minimum>1000000000:raise WorkbenchError('RESULT_LIMIT')
    return finite(dict(id=identifier,demand_units=demand,people=people,productive_minutes_per_person=productive,whole_unit_capacity=capacity,shortfall_units=max(0,demand-capacity),surplus_units=max(0,capacity-demand),minimum_people_under_assumptions=minimum,assumption_only=True))
