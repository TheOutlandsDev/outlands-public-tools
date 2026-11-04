"""Bounded offline unit catalogs, exact linear paths and rounded quantity checks."""
from collections import defaultdict, deque
from fractions import Fraction
import re
import toolkit as t
import decision_core as c

def number(value):
    t.require(type(value) is str and re.fullmatch(r'-?(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,6})?',value),'DECIMAL_INVALID')
    result=Fraction(value)
    t.require(abs(result)<=10**12,'DECIMAL_MAGNITUDE_INVALID')
    return result

def render(value):
    t.require(value.denominator==1,'NONTERMINATING_OUTPUT')
    sign='-' if value<0 else ''
    whole,part=divmod(abs(value.numerator),10**6)
    return sign+str(whole)+('.'+str(part).zfill(6).rstrip('0') if part else '')

def exact_decimal(value):
    scaled=value*10**6
    t.require(scaled.denominator==1,'DECIMAL_PRECISION_INVALID')
    return render(scaled)

def unique(value,parser,minimum,maximum):
    t.require(type(value) is list and minimum<=len(value)<=maximum,'NESTED_LIMIT')
    out={}
    for row in value:
        key,item=parser(row);t.require(key not in out,'NESTED_ID_DUPLICATE');out[key]=item
    return [out[k] for k in sorted(out)]

def dimension(row):
    key,out=c.record(row,{'id','base_unit'},('id','base_unit'))
    return key,out

def unit(row):
    return c.record(row,{'id','dimension'},('id','dimension'))

def edge(row):
    key,out=c.record(row,{'id','source','target','numerator','denominator'},('id','source','target'))
    t.integer(row['numerator'],10**6,1);t.integer(row['denominator'],10**6,1)
    t.require(row['source']!=row['target'],'SELF_EDGE_INVALID')
    fraction=Fraction(row['numerator'],row['denominator'])
    out['numerator']=fraction.numerator;out['denominator']=fraction.denominator
    return key,out

def catalog(row):
    key,out=c.record(row,{'id','revision','dimensions','units','edges'},('id',),('revision',))
    out['dimensions']=unique(row['dimensions'],dimension,1,8)
    out['units']=unique(row['units'],unit,1,32)
    out['edges']=unique(row['edges'],edge,0,64)
    dims={v['id']:v for v in out['dimensions']};units={v['id']:v for v in out['units']}
    for value in units.values():t.require(value['dimension'] in dims,'DIMENSION_UNKNOWN')
    for value in dims.values():
        base=units.get(value['base_unit'])
        t.require(base is not None and base['dimension']==value['id'],'BASE_UNIT_INVALID')
    for value in out['edges']:
        source=units.get(value['source']);target=units.get(value['target'])
        t.require(source is not None and target is not None,'UNIT_UNKNOWN')
        t.require(source['dimension']==target['dimension'],'CROSS_DIMENSION_EDGE')
    return key,out

def quantity(row):
    key,out=c.record(row,{'id','revision','catalog','catalog_revision','catalog_sha256','source','target','input','output','places','rounding'},('id','catalog','source','target'),('revision','catalog_revision'))
    t.sha(row['catalog_sha256']);number(row['input']);number(row['output'])
    t.integer(row['places'],6);t.require(row['rounding'] in ('half_even','half_away'),'ROUNDING_INVALID')
    return key,out

def scenario(row):
    key,out=c.record(row,{'id','revision','baseline','baseline_revision','baseline_sha256','candidate','candidate_revision','candidate_sha256','source','target','input','places','rounding'},('id','baseline','candidate','source','target'),('revision','baseline_revision','candidate_revision'))
    t.sha(row['baseline_sha256']);t.sha(row['candidate_sha256']);number(row['input'])
    t.integer(row['places'],6);t.require(row['rounding'] in ('half_even','half_away'),'ROUNDING_INVALID')
    return key,out

def collect(value,parser,name,counts,issues,maximum=32):
    t.require(type(value) is list and 1<=len(value)<=maximum,'COHORT_LIMIT')
    records,counts[name],found=c.rows(value,parser,name);issues.extend(found)
    if not records:c.issue(issues,name,0,'COHORT_EMPTY')
    return records

def reference(row,name,records,side,position,issues):
    found=records.get(row[name])
    if found is None:c.issue(issues,side,position,'REFERENCE_UNKNOWN');return None
    selected=found[1]
    if row[name+'_revision']!=selected['revision'] or row[name+'_sha256']!=c.pin(selected):c.issue(issues,side,position,'SNAPSHOT_MISMATCH')
    return selected

def resolve(catalog):
    units={v['id']:v for v in catalog['units']};graph=defaultdict(list)
    for edge in catalog['edges']:
        factor=Fraction(edge['numerator'],edge['denominator'])
        graph[edge['source']].append((edge['target'],1/factor))
        graph[edge['target']].append((edge['source'],factor))
    factors={};issues=set()
    for dim in catalog['dimensions']:
        base=dim['base_unit'];factors[base]=Fraction(1);todo=deque([base])
        while todo:
            current=todo.popleft()
            for target,ratio in graph[current]:
                proposed=factors[current]*ratio
                if target not in factors:factors[target]=proposed;todo.append(target)
                elif factors[target]!=proposed:issues.add('PATH_CONFLICT')
        if any(v['dimension']==dim['id'] and v['id'] not in factors for v in units.values()):issues.add('UNIT_UNREACHABLE')
    return factors,sorted(issues)

def rounded(value,places,mode):
    scaled=abs(value)*10**places
    quotient,remainder=divmod(scaled.numerator,scaled.denominator)
    twice=2*remainder
    if twice>scaled.denominator or (twice==scaled.denominator and (mode=='half_away' or quotient%2)):
        quotient+=1
    answer=Fraction(quotient,10**places)
    if value<0:answer=-answer
    t.require(abs(answer)<=10**12,'CONVERSION_MAGNITUDE_INVALID')
    return exact_decimal(answer)

def convert(catalog,factors,source,target,input_value,places,mode):
    units={v['id']:v for v in catalog['units']}
    if source not in units or target not in units:return None,'UNIT_UNKNOWN'
    if units[source]['dimension']!=units[target]['dimension']:return None,'DIMENSION_MISMATCH'
    if source not in factors or target not in factors:return None,'PATH_UNAVAILABLE'
    factor=factors[source]/factors[target]
    try:return {'factor':str(factor.numerator)+'/'+str(factor.denominator),'value':rounded(number(input_value)*factor,places,mode)},None
    except t.Rejected as error:return None,str(error)

def check(raw,mode):
    value=t.decode(raw)
    fields={'catalogs':{'catalogs'},'paths':{'catalogs'},'claims':{'catalogs','claims'},'scenarios':{'baseline_catalogs','candidate_catalogs','scenarios'}}[mode]
    t.fields(value,fields|{'format'});t.require(value['format']=='outlands-unit-'+mode+'-v1','FORMAT_INVALID')
    counts={};issues=[];assessment=None
    if mode=='scenarios':
        left=collect(value['baseline_catalogs'],catalog,'baseline_catalogs',counts,issues)
        right=collect(value['candidate_catalogs'],catalog,'candidate_catalogs',counts,issues)
        cases=collect(value['scenarios'],scenario,'scenarios',counts,issues,128)
        cohorts={'baseline_catalogs':left,'candidate_catalogs':right,'scenarios':cases}
        for key in left.keys()&right.keys():
            a=left[key][1];b=right[key][1]
            if a['revision']==b['revision'] and c.pin(a)!=c.pin(b):c.issue(issues,'candidate_catalogs',right[key][0],'SAME_REVISION_CATALOG_CONFLICT')
        for _,(position,item) in sorted(cases.items()):
            reference(item,'baseline',left,'scenarios',position,issues)
            reference(item,'candidate',right,'scenarios',position,issues)
        if not issues:
            assessment=[]
            for key,(position,item) in sorted(cases.items()):
                a=left[item['baseline']][1];b=right[item['candidate']][1]
                af,ai=resolve(a);bf,bi=resolve(b)
                if ai or bi:c.issue(issues,'scenarios',position,'CATALOG_PATH_INVALID');assessment.append({'id':key,'baseline':None,'candidate':None,'equal':None});continue
                av,ae=convert(a,af,item['source'],item['target'],item['input'],item['places'],item['rounding'])
                bv,be=convert(b,bf,item['source'],item['target'],item['input'],item['places'],item['rounding'])
                if ae or be:c.issue(issues,'scenarios',position,ae or be)
                equal=av==bv if av is not None and bv is not None else None
                if equal is False:c.issue(issues,'scenarios',position,'CONVERSION_CHANGED')
                assessment.append({'id':key,'baseline':av,'candidate':bv,'equal':equal})
    else:
        catalogs=collect(value['catalogs'],catalog,'catalogs',counts,issues)
        cohorts={'catalogs':catalogs}
        if mode=='catalogs':
            if not issues:assessment=[{'id':key,'revision':row['revision'],'sha256':c.pin(row),'dimension_count':len(row['dimensions']),'unit_count':len(row['units']),'edge_count':len(row['edges'])} for key,(_,row) in sorted(catalogs.items())]
        elif mode=='paths':
            if not issues:
                assessment=[]
                for key,(position,row) in sorted(catalogs.items()):
                    factors,found=resolve(row)
                    for code in found:c.issue(issues,'catalogs',position,code)
                    assessment.append({'id':key,'factors_to_base':{k:str(v.numerator)+'/'+str(v.denominator) for k,v in sorted(factors.items())} if not found else None,'findings':found})
        else:
            claims=collect(value['claims'],quantity,'claims',counts,issues,128);cohorts['claims']=claims
            for _,(position,item) in sorted(claims.items()):reference(item,'catalog',catalogs,'claims',position,issues)
            if not issues:
                assessment=[]
                for key,(position,item) in sorted(claims.items()):
                    selected_catalog=catalogs[item['catalog']][1];factors,found=resolve(selected_catalog)
                    if found:c.issue(issues,'claims',position,'CATALOG_PATH_INVALID');assessment.append({'id':key,'expected':None,'matches':None});continue
                    expected,error=convert(selected_catalog,factors,item['source'],item['target'],item['input'],item['places'],item['rounding'])
                    if error:c.issue(issues,'claims',position,error)
                    matches=expected['value']==exact_decimal(number(item['output'])) if expected is not None else None
                    if matches is False:c.issue(issues,'claims',position,'CONVERSION_MISMATCH')
                    assessment.append({'id':key,'expected':expected,'matches':matches})
    out=c.base(raw,'outlands-unit-'+mode+'-report-v1',counts,issues)
    pins={name:c.cohort_pin(rows) for name,rows in cohorts.items()}
    out.update(assessment=assessment,cohort_sha256=pins if assessment is not None else None,qualified_scope_sha256=c.pin(pins) if assessment is not None and not issues else None,linear_conversions_only=True,source_data_verified=False,instruments_contacted=False,network_requests_performed=False,target_changes_performed=False)
    return out
