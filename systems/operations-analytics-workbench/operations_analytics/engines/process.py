"""Declared OEE decomposition and explicit linear-interpolated cycle percentiles."""
from decimal import Decimal,ROUND_FLOOR
from ..contracts import fields,token,number,integer,rows,finite
from ..runtime import WorkbenchError


def calculate(row):
    fields(row,('id','planned_minutes','running_minutes','downtime_minutes','ideal_minutes_per_unit','total_units','good_units','cycle_samples_minutes'))
    identifier=token(row['id']);planned=number(row['planned_minutes'],maximum=527040);running=number(row['running_minutes'],maximum=527040);down=number(row['downtime_minutes'],maximum=527040)
    ideal=number(row['ideal_minutes_per_unit'],0.000001,1000000);total=integer(row['total_units']);good=integer(row['good_units'])
    if running+down!=planned:raise WorkbenchError('PROCESS_TIME_PARTITION_INVALID')
    if good>total or running==0 and total>0 or ideal*total>running:raise WorkbenchError('PROCESS_QUANTITY_INVALID')
    samples=sorted(number(v,0.000001,1000000) for v in rows(row['cycle_samples_minutes'],2000))
    median=p90=None
    if samples:
        middle=len(samples)//2;median=samples[middle] if len(samples)%2 else (samples[middle-1]+samples[middle])/2
        position=Decimal(len(samples)-1)*Decimal('0.9');low=int(position.to_integral_value(rounding=ROUND_FLOOR));high=min(low+1,len(samples)-1)
        p90=samples[low]+(samples[high]-samples[low])*(position-low)
    return finite(dict(id=identifier,availability_fraction=running/planned if planned else None,performance_fraction=ideal*total/running if running else None,quality_fraction=Decimal(good)/total if total else None,oee_fraction=ideal*good/planned if planned else None,observed_minutes_per_unit=running/total if total else None,cycle_sample_count=len(samples),median_minutes=median,p90_minutes_linear_interpolation=p90,total_units=total,good_units=good,declared_inputs_unverified=True))
