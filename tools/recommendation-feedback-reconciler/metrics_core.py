"""Exact bounded decimals, complete duplicate/conflict accounting and explicit joins."""
from collections import defaultdict
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import re
import toolkit as t


def number(value):
    t.require(type(value) is str and re.fullmatch(r'-?(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,6})?',value), 'DECIMAL_INVALID')
    result=Fraction(Decimal(value))
    t.require(abs(result)<=10**12,'DECIMAL_LIMIT')
    return result


def canonical(value):
    parsed=number(value)
    result=format(Decimal(value),'f')
    if '.' in result: result=result.rstrip('0').rstrip('.')
    return '0' if parsed==0 else result


def ratio(value):
    value=Fraction(value)
    return dict(numerator=str(value.numerator),denominator=str(value.denominator))


def root_mean_square(square_mean):
    with localcontext() as context:
        context.prec=60
        value=(Decimal(square_mean.numerator)/Decimal(square_mean.denominator)).sqrt()
        return format(value.quantize(Decimal('0.000000000001'),rounding=ROUND_HALF_EVEN),'f')


def rows(value,parser,side):
    t.require(type(value) is list and len(value)<=1000,'ROW_LIMIT')
    groups=defaultdict(list); issues=[]; rejected=0
    for index,row in enumerate(value,1):
        try:
            key,normalized=parser(row)
            groups[key].append((index,normalized))
        except t.Rejected as error:
            rejected+=1; issues.append(dict(side=side,row=index,code=str(error)))
    accepted={}; duplicate=conflict=0
    for key,entries in groups.items():
        if len({t.encode(record) for _,record in entries})!=1:
            conflict+=len(entries)
            issues.extend(dict(side=side,row=index,code='IDENTITY_CONFLICT') for index,_ in entries)
        else:
            accepted[key]=entries[0]; duplicate+=len(entries)-1
    counts=dict(input_rows=len(value),accepted_records=len(accepted),duplicate_rows=duplicate,
                conflict_rows=conflict,rejected_rows=rejected)
    t.require(len(value)==len(accepted)+duplicate+conflict+rejected,'ACCOUNTING_FAILED')
    return accepted,counts,issues


def forecast_fields(row,fields):
    t.fields(row,{'id','revision','series','origin','target'}|set(fields))
    t.identifier(row['id']); t.identifier(row['series'])
    t.integer(row['revision'],1000000,1)
    t.integer(row['origin'],10**9); t.integer(row['target'],10**9)
    t.require(1<=row['target']-row['origin']<=365,'HORIZON_INVALID')
    result={k:row[k] for k in ('id','revision','series','origin','target')}
    for field in fields:
        number(row[field]); result[field]=canonical(row[field])
    return result


def outcome(row):
    t.fields(row,{'series','period','value'})
    t.identifier(row['series']); t.integer(row['period'],10**9)
    value=row['value']
    if value is not None: number(value); value=canonical(value)
    return (row['series'],row['period']),dict(series=row['series'],period=row['period'],value=value)


def pairs(forecasts,outcomes,parser):
    t.require(type(forecasts) is list and 1<=len(forecasts)<=1000,'FORECAST_ROWS_REQUIRED')
    predictions,pc,issues=rows(forecasts,parser,'forecasts')
    observed,oc,other=rows(outcomes,outcome,'outcomes'); issues+=other
    matched=[]; used=set(); missing=pending=0
    for index,prediction in predictions.values():
        key=(prediction['series'],prediction['target'])
        if key not in observed:
            missing+=1; issues.append(dict(side='forecasts',row=index,code='MISSING_OUTCOME')); continue
        used.add(key); actual=observed[key][1]
        if actual['value'] is None:
            pending+=1; issues.append(dict(side='forecasts',row=index,code='PENDING_OUTCOME')); continue
        matched.append((prediction,number(actual['value'])))
    unused=set(observed)-used
    for key in sorted(unused): issues.append(dict(side='outcomes',row=observed[key][0],code='UNUSED_OUTCOME'))
    counts=dict(forecasts=pc,outcomes=oc,resolved_pairs=len(matched),missing_forecasts=missing,
                pending_forecasts=pending,unused_outcomes=len(unused))
    return matched,counts,sorted(issues,key=lambda row:(row['side'],row['row'],row['code']))


def cli(description,operation,argv=None):
    parser=t.Parser(description=description)
    parser.add_argument('--input',required=True); parser.add_argument('--out')
    return t.run(parser,lambda a:operation(t.read(a.input)),argv)
